"""Extract the knowledge in one ingested original into facts (Phase 3). Code orchestrates; the LLM only fills partial objects per batch.

Per entity tagged in the file (the chunks are re-derived from the original). A chunk informs the facts that recognition gave it as topics
(`RecognitionStore`), plus, for the identifier facts (FunctionalRequirements, NonFunctionalRequirements), the facts the keyword rules tagged
it with; a file not recognized yet uses the keyword tags alone. A fact's entity-backed list fields (components, environments, alerts, ...)
are not asked for here: entity-centric extraction fills one item per recognized entity (`entity_item_pipeline`).
1. fact key from the file's scope (`fact_keys`); none = SKIPPED_SCOPE;
2. the entity's chunks unchanged since this file's stored contribution = SKIPPED_UNCHANGED_CHUNKS, no LLM call;
3. the chunks in batches, one fresh single-tool call per batch (`EntityExtractor`), the batch answers merged in chunk order; a failed
   batch of several chunks is split in half and retried (an answer too long for one reply is the usual cause);
4. the result stored as this file's contribution (a contribution concept beside its Source), replacing its earlier one;
5. all contributions of the fact merged (newest ingested file first, '(existing)' last) and saved through BundleStore,
   which writes the fact's OKF concept file (frontmatter, JSON value, open questions) and the bundle's log and index.
Before merging, an empty requirement priority is filled from the requirement's own keyword (SHALL -> MUST, ...; `priority_keywords`).
An entity no longer tagged in the file loses this file's contribution and its fact is re-merged (REMOVED). A batch that fails is
reported; when any batch failed the contribution keeps no chunks hash, so the next run tries again.
"""
import json
import re

from docfactory import clock
from docfactory.agents.entity_extractor import EntityExtractor
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.contribution_store import ContributionStore
from docfactory.bundle.fact_registry import FACT_SPECS
from docfactory.bundle.entity_store import EntityStore
from docfactory.bundle.paths import ENTITY_RESOURCE_PREFIX, EXISTING_RESOURCE, is_entity_resource
from docfactory.bundle.recognition_store import RecognitionStore
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.batching import batch_chunks, batch_text, chunks_hash, split_chunk
from docfactory.extract.evidence import attach_evidence
from docfactory.extract.fact_keys import fact_key
from docfactory.extract.grounding import ungrounded_values
from docfactory.extract.merge import merge_partials
from docfactory.extract.missing_questions import missing_questions
from docfactory.extract.priority_keywords import fill_priorities
from docfactory.ingest.source_reads import read_chunks
from docfactory.extract.model_shapes import item_model
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.entity_extraction_report import EntityExtractionReport
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_source import FactSource
from docfactory.models.save_action import SaveAction
from docfactory.okf_frontmatter import type_name
from docfactory.recognize.type_vocabulary import entity_fields, identifier_facts

UNSPECIFIED_ACTOR = "docfactory/unspecified"


def _chunk_facts(path: str, record) -> list[tuple[int, str]]:
    """(chunk number, fact) pairs of the stored original `path`: recognition topics plus the keyword tags of identifier facts, or the keyword
    tags alone when the file has no recognition yet."""
    recognition = RecognitionStore().get(path)
    if recognition is None:
        return [(tag.chunk_no, tag.entity) for tag in record.tags]
    pairs = [(topic.chunk_no, fact) for window in recognition.windows for topic in window.topics for fact in topic.facts]
    pairs += [(tag.chunk_no, tag.entity) for tag in record.tags if tag.entity in identifier_facts()]
    return list(dict.fromkeys(pairs))


def _chunks_by_entity(path: str) -> dict[str, list[DocChunk]]:
    """The chunks of the stored original `path` (re-derived from the file) grouped by the fact they inform (`_chunk_facts`), facts by name."""
    record, chunks = read_chunks(path)
    by_number = {chunk.chunk_no: chunk for chunk in chunks}
    by_entity: dict[str, list[DocChunk]] = {}
    for chunk_no, fact in sorted(_chunk_facts(path, record)):
        if chunk_no in by_number and fact in FACT_SPECS:
            by_entity.setdefault(fact, []).append(by_number[chunk_no])
    return dict(sorted(by_entity.items()))


def _kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def keep_existing(key: str) -> None:
    """A fact stored before any extraction (e.g. seed data) becomes the lowest-precedence contribution, so merging never drops it."""
    fact = BundleStore().read_fact(key)
    store = ContributionStore()
    if fact is None or store.list(key):
        return
    store.save(key, EXISTING_RESOURCE, json.loads(fact.value), None, None, fact.generated_by or UNSPECIFIED_ACTOR, fact.generated_at or clock.now_iso())


def _ordered(key: str) -> list[tuple[str, dict, str | None, str | None, str | None]]:
    """(resource, value, description, Source timestamp, Source author) of every contribution of `key`, newest ingested file first, '(existing)' last."""
    rows = []
    sources = SourceStore()
    for contribution in ContributionStore().list(key):
        no_source = contribution.resource == EXISTING_RESOURCE or is_entity_resource(contribution.resource)
        stored = None if no_source else sources.read(contribution.resource)
        rows.append((contribution.resource, json.loads(contribution.value_json), contribution.description,
                     stored.timestamp if stored else None, contribution.timestamp, stored.author if stored else None))
    rows.sort(key=lambda r: r[0])  # stable sorts: the last one is the primary order
    rows.sort(key=lambda r: r[3] or r[4], reverse=True)  # newest ingested file first (contribution time when the Source is gone)
    rows.sort(key=lambda r: r[0] == EXISTING_RESOURCE)
    return [(resource, value, description, stamp, author) for resource, value, description, stamp, _, author in rows]


def _entity_sources(scope: str, ordered: list) -> list[FactSource]:
    """The originals behind the entity items of a fact (the evidence of their entities), each once, with their Source time and author."""
    graph = {e.entity_id: e for e in EntityStore().list(scope)}
    sources, found = SourceStore(), []
    for resource, _, _, _, _ in ordered:
        if is_entity_resource(resource) and resource.removeprefix(ENTITY_RESOURCE_PREFIX) in graph:
            found += [e.resource for e in graph[resource.removeprefix(ENTITY_RESOURCE_PREFIX)].evidence]
    records = [sources.read(r) for r in dict.fromkeys(found)]
    return [FactSource(resource=r.path, last_modified=r.timestamp, author=r.author) for r in records if r is not None]


def _without_entity_fields(model: type, ordered: list) -> list[tuple[str, dict]]:
    """The contributions to merge. Once a fact has entity items, its entity-backed list fields come from them alone: what batch extraction once
    put there (items named after any mention) is ignored. A fact without entity items merges as before."""
    fields = entity_fields(model.__name__)
    if not fields or not any(is_entity_resource(resource) for resource, _, _, _, _ in ordered):
        return [(resource, value) for resource, value, _, _, _ in ordered]
    return [(resource, value if is_entity_resource(resource) else {k: v for k, v in value.items() if k not in fields})
            for resource, value, _, _, _ in ordered]


def merge_and_save(key: str, model: type, actor: str, report: dict) -> None:
    """Merge every contribution of `key`, save the result and record what happened in `report` (fields of the report)."""
    ordered = _ordered(key)
    report["contributions"] = len(ordered)
    if not ordered:
        report["reason"] = "no file contributes to this fact any more; the stored fact is left as it was"
        return
    merged, conflicts = merge_partials(model, _without_entity_fields(model, ordered))
    scope = key.split(".")[0]
    file_sources = [FactSource(resource=resource, last_modified=stamp, author=author) for resource, _, _, stamp, author in ordered if stamp]
    known = {s.resource for s in file_sources}
    meta = FactMeta(
        generated_by=actor,
        title=f"{scope} {type_name(model.__name__).lower()}",
        description=next((d for _, _, d, _, _ in ordered if d), None),
        tags=[_kebab(model.__name__), "extracted"],
        sources=file_sources + [s for s in _entity_sources(scope, ordered) if s.resource not in known],
    )
    result = BundleStore().write_fact(key, merged, meta)
    report["conflicts"] += conflicts
    report["missing_questions"] = missing_questions(model, merged)
    report["items"] = sum(len(v) for n, v in merged.items() if isinstance(v, list) and item_model(model.model_fields[n].annotation))
    report["action"], report["version"], report["completeness"] = result.action, result.version, result.completeness
    report["save_errors"] = result.errors
    if result.action == SaveAction.REJECTED:
        report["outcome"] = ExtractionOutcome.REJECTED
        report["reason"] = "the merged fact is not valid yet (see save errors); this file's contribution is kept for a later merge"


def _extract_entity(path: str, entity: str, chunks: list[DocChunk], extractor: EntityExtractor, force: bool) -> EntityExtractionReport:
    report = {"entity": entity, "chunks_used": len(chunks), "conflicts": [], "ungrounded_values": [], "batch_notes": [], "priorities_from_keywords": 0}
    key, why = fact_key(path, entity)
    if key is None:
        return EntityExtractionReport(outcome=ExtractionOutcome.SKIPPED_SCOPE, reason=why, **report)
    report["key"] = key
    model = FACT_SPECS[entity]["model"]
    current_hash = chunks_hash(chunks)
    stored = ContributionStore().get(key, path)
    if stored is not None and stored.chunks_hash == current_hash and not force:
        return EntityExtractionReport(outcome=ExtractionOutcome.SKIPPED_UNCHANGED_CHUNKS, contributions=len(ContributionStore().list(key)),
                                      reason="the entity's chunks are unchanged since the last extraction", **report)
    pending = batch_chunks(chunks)
    answers, summaries, calls, failed = [], [], 0, 0
    while pending:
        batch = pending.pop(0)
        stated, summary, note = extractor.extract_batch(model, path, batch, entity_fields(entity))
        calls += 1
        label = f"chunks {batch[0].chunk_no}-{batch[-1].chunk_no}"
        if stated is None:
            if len(batch) > 1:  # often an answer too long for one reply: retry the halves, in order
                half = len(batch) // 2
                pending[:0] = [batch[:half], batch[half:]]
                report["batch_notes"].append(f"{label}: {note}; split and retried in two halves")
            elif len(split_chunk(batch[0])) > 1:  # a single long chunk (a big table): cut it in two and try the halves
                pending[:0] = [[half] for half in split_chunk(batch[0])]
                report["batch_notes"].append(f"{label}: {note}; the chunk was cut in two and retried")
            else:
                failed += 1
                report["batch_notes"].append(f"{label}: {note}")
            continue
        stated, filled = fill_priorities(model, stated)
        stated = attach_evidence(model, stated, batch)  # where the document names each item, set by code
        report["priorities_from_keywords"] += filled
        answers.append((label, stated))
        summaries.append(summary)
        report["ungrounded_values"] += ungrounded_values(model, stated, batch_text(batch))
    report["batches"], report["failed_batches"] = calls, failed
    if not answers:
        return EntityExtractionReport(outcome=ExtractionOutcome.FAILED, reason="no batch gave an accepted answer; nothing was stored", **report)
    file_value, batch_conflicts = merge_partials(model, answers)
    report["conflicts"] += batch_conflicts
    keep_existing(key)
    complete = not report["failed_batches"]  # a partial result is stored but retried next run
    ContributionStore().save(key, path, file_value, current_hash if complete else None, next((s for s in summaries if s), None),
                             extractor.actor, clock.now_iso())
    report["outcome"] = ExtractionOutcome.SAVED
    merge_and_save(key, model, extractor.actor, report)
    if report["outcome"] == ExtractionOutcome.SAVED and report.get("action") == SaveAction.UNCHANGED:
        report["outcome"] = ExtractionOutcome.UNCHANGED
    return EntityExtractionReport(**report)


def remove_entity(path: str, key: str, actor: str) -> EntityExtractionReport:
    entity = key.rsplit(".", 1)[-1]
    ContributionStore().remove(key, path)
    report = {"entity": entity, "key": key, "outcome": ExtractionOutcome.REMOVED, "conflicts": [],
              "reason": "the entity is no longer tagged in this file; its contribution was removed and the fact re-merged"}
    merge_and_save(key, FACT_SPECS[entity]["model"], actor, report)
    return EntityExtractionReport(**report)


def extract_file(path: str, extractor: EntityExtractor, entities: list[str] | None = None, force: bool = False) -> list[EntityExtractionReport]:
    """Extract the entities tagged in the ingested original `path` (its bundle path) (all, or only `entities`) and return one report per entity.

    `force` re-extracts entities whose chunks are unchanged. Raises FileNotFoundError for an original with no Source, ValueError for an
    unknown entity name.
    """
    path = path.replace("\\", "/").strip("/")
    if SourceStore().read(path) is None:
        raise FileNotFoundError(f"no such file in the bundle: {path}")
    for name in entities or []:
        if name not in FACT_SPECS:
            raise ValueError(f"unknown entity {name!r}")
    tagged = _chunks_by_entity(path)
    wanted = set(entities) if entities else None
    reports = [_extract_entity(path, entity, chunks, extractor, force) for entity, chunks in tagged.items() if wanted is None or entity in wanted]
    for contribution in ContributionStore().list(resource=path):
        entity = contribution.fact_key.rsplit(".", 1)[-1]
        if entity not in tagged and (wanted is None or entity in wanted):
            reports.append(remove_entity(path, contribution.fact_key, extractor.actor))
    return reports


def format_reports(path: str, reports: list[EntityExtractionReport]) -> str:
    """The plain-text run report: one block per entity."""
    if not reports:
        return f"{path}: no tagged entities to extract"
    lines = [path]
    for r in reports:
        saved = f" v{r.version}, {r.completeness:.0f}% complete" if r.version is not None and r.completeness is not None else ""
        lines.append(f"  {r.entity}: {r.outcome.value}" + (f" -> {r.key}" if r.key else "") + saved)
        if r.reason:
            lines.append(f"    reason: {r.reason}")
        if r.batches:
            lines.append(f"    chunks {r.chunks_used}, batches {r.batches} ({r.failed_batches} failed), items {r.items}, contributing files {r.contributions}"
                         + (f", priorities from keywords {r.priorities_from_keywords}" if r.priorities_from_keywords else ""))
        for title, values in (("batch problems", r.batch_notes), ("conflicts", r.conflicts), ("not found in the text", r.ungrounded_values),
                              ("still missing", r.missing_questions)):
            if values:
                lines.append(f"    {title} ({len(values)}):")
                lines += [f"      - {value}" for value in values]
        lines += [f"    save error: {e.path}: {e.message}" + (f" ({e.question})" if e.question else "") for e in r.save_errors]
    return "\n".join(lines)
