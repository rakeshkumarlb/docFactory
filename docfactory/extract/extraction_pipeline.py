"""Extract the knowledge in one DocStore file into facts (Phase 3). Code orchestrates; the LLM only fills partial objects per batch.

Per entity tagged in the file (`DocChunkTags`):
1. fact key from the file's scope (`fact_keys`); none = SKIPPED_SCOPE;
2. the entity's chunks unchanged since this file's stored contribution = SKIPPED_UNCHANGED_CHUNKS, no LLM call;
3. the chunks in batches, one fresh single-tool call per batch (`EntityExtractor`), the batch answers merged in chunk order;
4. the result stored as this file's contribution (`FactContributions`), replacing its earlier one;
5. all contributions of the fact merged (newest DocStore file first, '(existing)' last) and saved through the entity saver,
   which writes KnowledgeFacts, its history and the bundle file.
An entity no longer tagged in the file loses this file's contribution and its fact is re-merged (REMOVED). A batch that fails is
reported; when any batch failed the contribution keeps no chunks hash, so the next run tries again.
"""
import json
import re

from docfactory import clock, contributions, db, facts
from docfactory.agents.entity_extractor import EntityExtractor
from docfactory.base_saver import BaseSaver
from docfactory.extract.batching import batch_chunks, batch_text, chunks_hash
from docfactory.extract.fact_keys import fact_key
from docfactory.extract.grounding import ungrounded_values
from docfactory.extract.merge import merge_partials
from docfactory.extract.missing_questions import missing_questions
from docfactory.extract.model_shapes import item_model
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.entity_extraction_report import EntityExtractionReport
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_source import FactSource
from docfactory.models.save_action import SaveAction
from docfactory.okf_frontmatter import type_name
from docfactory.saver_resolution import entity_saver_for

UNSPECIFIED_ACTOR = "docfactory/unspecified"


def _chunks_by_entity(path: str) -> dict[str, list[DocChunk]]:
    rows = {row["ChunkNo"]: row for row in db.list_doc_chunks(path)}
    by_entity: dict[str, list[DocChunk]] = {}
    for tag in db.list_doc_chunk_tags(path):
        row = rows[tag["ChunkNo"]]
        by_entity.setdefault(tag["Entity"], []).append(DocChunk(chunk_no=row["ChunkNo"], heading=row["Heading"], page_from=row["PageFrom"],
                                                                page_to=row["PageTo"], text=row["Text"], text_hash=row["TextHash"]))
    return dict(sorted(by_entity.items()))


def _kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _keep_existing(key: str) -> None:
    """A fact stored before any extraction (e.g. seed data) becomes the lowest-precedence contribution, so merging never drops it."""
    fact = facts.get_fact(key)
    if fact is None or contributions.list_contributions(key):
        return
    contributions.save_contribution(key, contributions.EXISTING, json.loads(fact.value), None, None,
                                    fact.generated_by or UNSPECIFIED_ACTOR, fact.generated_at or clock.now_iso())


def _ordered(key: str) -> list[tuple[str, dict, str | None, str | None]]:
    """(resource, value, description, DocStore timestamp) of every contribution of `key`, newest DocStore file first, '(existing)' last."""
    rows = []
    for contribution in contributions.list_contributions(key):
        stored = None if contribution.resource == contributions.EXISTING else db.get_docstore_row(contribution.resource)
        rows.append((contribution.resource, json.loads(contribution.value_json), contribution.description,
                     stored["Timestamp"] if stored else None, contribution.timestamp))
    rows.sort(key=lambda r: r[0])  # stable sorts: the last one is the primary order
    rows.sort(key=lambda r: r[3] or r[4], reverse=True)  # newest DocStore file first (contribution time when the file is gone)
    rows.sort(key=lambda r: r[0] == contributions.EXISTING)
    return [(resource, value, description, stamp) for resource, value, description, stamp, _ in rows]


def _merge_and_save(key: str, saver_class: type[BaseSaver], actor: str, report: dict) -> None:
    """Merge every contribution of `key`, save the result and record what happened in `report` (fields of the report)."""
    ordered = _ordered(key)
    report["contributions"] = len(ordered)
    if not ordered:
        report["reason"] = "no file contributes to this fact any more; the stored fact is left as it was"
        return
    model = saver_class.model
    merged, conflicts = merge_partials(model, [(resource, value) for resource, value, _, _ in ordered])
    scope = key.split(".")[0]
    meta = FactMeta(
        generated_by=actor,
        title=f"{scope} {type_name(model.__name__).lower()}",
        description=next((d for _, _, d, _ in ordered if d), None),
        tags=[_kebab(model.__name__), "extracted"],
        sources=[FactSource(resource=resource, last_modified=stamp) for resource, _, _, stamp in ordered if stamp],
    )
    result = saver_class().save(key, merged, meta=meta)
    report["conflicts"] += conflicts
    report["missing_questions"] = missing_questions(model, merged)
    report["items"] = sum(len(v) for n, v in merged.items() if isinstance(v, list) and item_model(model.model_fields[n].annotation))
    report["action"], report["version"], report["completeness"] = result.action, result.version, result.completeness
    report["save_errors"] = result.errors
    if result.action == SaveAction.REJECTED:
        report["outcome"] = ExtractionOutcome.REJECTED
        report["reason"] = "the merged fact is not valid yet (see save errors); this file's contribution is kept for a later merge"


def _extract_entity(path: str, entity: str, chunks: list[DocChunk], extractor: EntityExtractor, force: bool) -> EntityExtractionReport:
    report = {"entity": entity, "chunks_used": len(chunks), "conflicts": [], "ungrounded_values": [], "batch_notes": []}
    key, why = fact_key(path, entity)
    if key is None:
        return EntityExtractionReport(outcome=ExtractionOutcome.SKIPPED_SCOPE, reason=why, **report)
    report["key"] = key
    saver_class = entity_saver_for(entity)
    model = saver_class.model
    current_hash = chunks_hash(chunks)
    stored = contributions.get_contribution(key, path)
    if stored is not None and stored.chunks_hash == current_hash and not force:
        return EntityExtractionReport(outcome=ExtractionOutcome.SKIPPED_UNCHANGED_CHUNKS, contributions=len(contributions.list_contributions(key)),
                                      reason="the entity's chunks are unchanged since the last extraction", **report)
    batches = batch_chunks(chunks)
    answers, summaries = [], []
    for number, batch in enumerate(batches, start=1):
        stated, summary, note = extractor.extract_batch(model, path, batch)
        label = f"chunks {batch[0].chunk_no}-{batch[-1].chunk_no}"
        if stated is None:
            report["batch_notes"].append(f"batch {number} ({label}): {note}")
            continue
        answers.append((label, stated))
        summaries.append(summary)
        report["ungrounded_values"] += ungrounded_values(model, stated, batch_text(batch))
    report["batches"], report["failed_batches"] = len(batches), len(batches) - len(answers)
    if not answers:
        return EntityExtractionReport(outcome=ExtractionOutcome.FAILED, reason="no batch gave an accepted answer; nothing was stored", **report)
    file_value, batch_conflicts = merge_partials(model, answers)
    report["conflicts"] += batch_conflicts
    _keep_existing(key)
    complete = not report["failed_batches"]  # a partial result is stored but retried next run
    contributions.save_contribution(key, path, file_value, current_hash if complete else None, next((s for s in summaries if s), None),
                                    extractor.actor, clock.now_iso())
    report["outcome"] = ExtractionOutcome.SAVED
    _merge_and_save(key, saver_class, extractor.actor, report)
    if report["outcome"] == ExtractionOutcome.SAVED and report.get("action") == SaveAction.UNCHANGED:
        report["outcome"] = ExtractionOutcome.UNCHANGED
    return EntityExtractionReport(**report)


def _remove_entity(path: str, key: str, actor: str) -> EntityExtractionReport:
    entity = key.rsplit(".", 1)[-1]
    contributions.remove_contribution(key, path)
    report = {"entity": entity, "key": key, "outcome": ExtractionOutcome.REMOVED, "conflicts": [],
              "reason": "the entity is no longer tagged in this file; its contribution was removed and the fact re-merged"}
    _merge_and_save(key, entity_saver_for(entity), actor, report)
    return EntityExtractionReport(**report)


def extract_file(path: str, extractor: EntityExtractor, entities: list[str] | None = None, force: bool = False) -> list[EntityExtractionReport]:
    """Extract the entities tagged in the DocStore file `path` (all, or only `entities`) and return one report per entity.

    `force` re-extracts entities whose chunks are unchanged. Raises FileNotFoundError for a file not in DocStore, ValueError for an
    unknown entity name.
    """
    path = path.replace("\\", "/").strip("/")
    if db.get_docstore_row(path) is None:
        raise FileNotFoundError(f"no such file in DocStore: {path}")
    for name in entities or []:
        if entity_saver_for(name) is None:
            raise ValueError(f"unknown entity {name!r}")
    tagged = _chunks_by_entity(path)
    wanted = set(entities) if entities else None
    reports = [_extract_entity(path, entity, chunks, extractor, force) for entity, chunks in tagged.items() if wanted is None or entity in wanted]
    for contribution in contributions.list_contributions(resource=path):
        entity = contribution.fact_key.rsplit(".", 1)[-1]
        if entity not in tagged and (wanted is None or entity in wanted):
            reports.append(_remove_entity(path, contribution.fact_key, extractor.actor))
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
            lines.append(f"    chunks {r.chunks_used}, batches {r.batches} ({r.failed_batches} failed), items {r.items}, contributing files {r.contributions}")
        for title, values in (("batch problems", r.batch_notes), ("conflicts", r.conflicts), ("not found in the text", r.ungrounded_values),
                              ("still missing", r.missing_questions)):
            if values:
                lines.append(f"    {title} ({len(values)}):")
                lines += [f"      - {value}" for value in values]
        lines += [f"    save error: {e.path}: {e.message}" + (f" ({e.question})" if e.question else "") for e in r.save_errors]
    return "\n".join(lines)
