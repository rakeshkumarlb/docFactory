"""Entity-centric extraction: one item per recognized entity, filled from everything that discusses it. Code orchestrates; the LLM only
fills one item per call.

For each entity of the scope's graph whose type is an item type (Component -> Architecture.components, Alert -> Monitoring.alerts, ...):
1. its fact key: '<scope>.<Fact>' (a shared fact such as Slo only in the Shared scope, an application fact never there);
2. its evidence: its own chunks in every original, then its neighbours' chunks, within the word budget (`entity_evidence`);
3. unchanged entity and evidence since its stored item = no call (unless `force`); else one fresh single-tool call (`EntityItemExtractor`)
   that sees the item model without the fields code sets;
4. code sets the identity (the entity's canonical name), `evidence` (where it is discussed), `relations` (its links in the graph, as
   Relation items) and adds the targets of its 'depends on' links to `dependencies`;
5. the item is stored as the contribution '(entity) <entity id>' to the fact; items of entities no longer in the graph are removed;
6. every touched fact is re-merged and saved (`extraction_pipeline.merge_and_save`): its entity-backed list fields now come from these items.
"""
import json

from pydantic import ValidationError

from docfactory import clock
from docfactory.agents.entity_item_extractor import EntityItemExtractor
from docfactory.bundle.contribution_store import ContributionStore
from docfactory.bundle.entity_store import EntityStore
from docfactory.bundle.fact_registry import FACT_SPECS
from docfactory.bundle.paths import ENTITY_RESOURCE_PREFIX, SHARED_FOLDER, entity_resource, is_entity_resource
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.entitymodels.items.relation_kind import RelationKind
from docfactory.extract.entity_evidence import evidence_lines, evidence_text, gather
from docfactory.extract.extraction_pipeline import merge_and_save
from docfactory.extract.grounding import ungrounded_values
from docfactory.extract.model_shapes import identity_field
from docfactory.ingest.chunks_out_of_date_error import ChunksOutOfDateError
from docfactory.ingest.source_reads import read_chunks
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.entity_extraction_report import EntityExtractionReport
from docfactory.models.entity_record import EntityRecord
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.save_action import SaveAction
from docfactory.recognize.type_vocabulary import identifier_types, item_types

CODE_FIELDS = ("evidence", "relations")  # set by code from the graph, never asked for
KINDS = {kind.value for kind in RelationKind}


def _key(scope: str, fact: str) -> str | None:
    shared = FACT_SPECS[fact]["shared"]
    if shared != (scope == SHARED_FOLDER):
        return None
    return f"{scope}.{fact}"


def _chunk_reader():
    cache: dict[str, dict[int, DocChunk]] = {}

    def chunks_of(resource: str) -> dict[int, DocChunk]:
        if resource not in cache:
            try:
                cache[resource] = {c.chunk_no: c for c in read_chunks(resource)[1]}
            except (FileNotFoundError, ValueError, ChunksOutOfDateError):
                cache[resource] = {}  # the original is gone or changed: its evidence is skipped until recognition runs again
        return cache[resource]

    return chunks_of


def _code_fields(model, entity: EntityRecord, graph: dict[str, EntityRecord], lines: list[str]) -> dict:
    """The item fields code sets: identity, evidence, relations (one per target, from the links) and the 'depends on' targets."""
    fields = {identity_field(model): entity.name}
    if "evidence" in model.model_fields:
        fields["evidence"] = lines
    targets = [(graph[link.target].name if link.target in graph else link.target, link) for link in entity.links]
    if "relations" in model.model_fields:
        seen: set[str] = set()
        fields["relations"] = [{"target": name, "kind": link.kind if link.kind in KINDS else "relates_to", "evidence": link.relation}
                               for name, link in targets if name not in seen and not seen.add(name)]
    if "dependencies" in model.model_fields:
        fields["dependencies"] = [name for name, link in targets if link.kind == "depends_on" or "depend" in link.relation.lower()]
    return fields


def _merge_dependencies(stated: list, derived: list) -> list:
    seen = {str(v).casefold() for v in stated}
    return list(stated) + [v for v in derived if v.casefold() not in seen]


def extract_entity_items(scope: str, extractor: EntityItemExtractor, force: bool = False) -> list[EntityExtractionReport]:
    """Fill or refresh the item of every item-typed entity of `scope`, re-merge the touched facts and return one report per fact."""
    graph_list = EntityStore().list(scope)
    graph = {e.entity_id: e for e in graph_list}
    mapping = {name: spec for name, spec in item_types().items() if name not in identifier_types()}
    chunks_of = _chunk_reader()
    store = ContributionStore()
    reports: dict[str, dict] = {}
    for entity in graph_list:
        if entity.type not in mapping:
            continue
        fact, field, model = mapping[entity.type]
        key = _key(scope, fact)
        if key is None:
            continue
        report = reports.setdefault(key, {"entity": fact, "key": key, "conflicts": [], "ungrounded_values": [], "batch_notes": [],
                                          "chunks_used": 0, "batches": 0, "failed_batches": 0, "touched": False})
        picked = gather(entity, graph_list, chunks_of)
        if not picked:
            report["batch_notes"].append(f"{entity.name}: no evidence text could be read; item left as it was")
            continue
        text = evidence_text(picked)
        input_hash = sha256_hex(canonical_json([entity.model_dump(mode="json"), text]))
        resource = entity_resource(entity.entity_id)
        report["chunks_used"] += len(picked)
        stored = store.get(key, resource)
        if stored is not None and stored.chunks_hash == input_hash and not force:
            continue
        exclude = frozenset([identity_field(model), *(f for f in CODE_FIELDS if f in model.model_fields)])
        stated, summary, note = extractor.extract_item(model, entity, text, exclude)
        report["batches"] += 1
        if stated is None:
            report["failed_batches"] += 1
            report["batch_notes"].append(f"{entity.name}: {note}")
            continue
        report["ungrounded_values"] += [f"{entity.name}: {v}" for v in ungrounded_values(model, stated, text)]
        code = _code_fields(model, entity, graph, evidence_lines(picked, entity))
        if "dependencies" in code:
            code["dependencies"] = _merge_dependencies(stated.get("dependencies", []), code["dependencies"])
        item = {**stated, **{k: v for k, v in code.items() if v not in ([], "")}}
        try:
            model.model_validate(item)
        except ValidationError as error:  # e.g. a Kpi whose definition no document states: not an item yet
            missing = ", ".join(".".join(map(str, e["loc"])) for e in error.errors())
            report["batch_notes"].append(f"{entity.name}: not a valid {model.__name__} yet ({missing}); not stored")
            continue
        store.save(key, resource, {field: [item]}, input_hash, summary, extractor.actor, clock.now_iso())
        report["touched"] = True
    for key, report in reports.items():  # items of entities that left the graph
        for contribution in store.list(key):
            if is_entity_resource(contribution.resource) and contribution.resource.removeprefix(ENTITY_RESOURCE_PREFIX) not in graph:
                store.remove(key, contribution.resource)
                report["touched"] = True
    results = []
    for key, report in sorted(reports.items()):
        touched = report.pop("touched")
        if not touched:
            results.append(EntityExtractionReport(outcome=ExtractionOutcome.SKIPPED_UNCHANGED_CHUNKS, reason="every entity item is unchanged", **report))
            continue
        report["outcome"] = ExtractionOutcome.SAVED
        merge_and_save(key, FACT_SPECS[report["entity"]]["model"], extractor.actor, report)
        if report["outcome"] == ExtractionOutcome.SAVED and report.get("action") == SaveAction.UNCHANGED:
            report["outcome"] = ExtractionOutcome.UNCHANGED
        results.append(EntityExtractionReport(**report))
    return results


def item_json(key: str, entity_id: str) -> dict | None:
    """The stored item of one entity (its contribution's value), for reports and tests; None when there is none."""
    stored = ContributionStore().get(key, entity_resource(entity_id))
    return json.loads(stored.value_json) if stored else None
