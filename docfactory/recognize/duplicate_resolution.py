"""Entity resolution of a scope: find the entities of one type that are the same thing under different names, across all documents.
Code orchestrates; the LLM answers once per type.

Recognition matches a window's entities to the catalog it is shown, but a small model still sometimes creates 'AI Engine' beside
'AI-Driven Matching Engine'. This step looks at each type's whole list at once:
1. per entity type with at least two entities, the hash of its entities (as the merge produced them without the type's own decisions);
2. unchanged hash since the stored decision = no call (unless `force`); else one fresh single-tool call (`DuplicateResolver`);
3. the decisions of every type are stored (`ResolutionStore`) and the entity graph is rebuilt, which folds each duplicate into the kept entity.
A type whose call failed keeps its earlier decisions and is asked again on the next run.
"""
from docfactory import clock
from docfactory.agents.duplicate_resolver import DuplicateResolver
from docfactory.bundle.resolution_store import ResolutionStore
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.entity_record import EntityRecord


def type_hashes(graph: list[EntityRecord]) -> dict[str, str]:
    """Entity type -> hash of its entities' ids, names, aliases and summaries, for every type with at least two entities."""
    by_type: dict[str, list[EntityRecord]] = {}
    for entity in graph:
        by_type.setdefault(entity.type, []).append(entity)
    return {t: sha256_hex(canonical_json([[e.entity_id, e.name, e.aliases, e.summary] for e in sorted(es, key=lambda e: e.entity_id)]))
            for t, es in sorted(by_type.items()) if len(es) > 1}


def resolve_scope(scope: str, unresolved: list[EntityRecord], resolver: DuplicateResolver, force: bool = False) -> list[str]:
    """Ask for the duplicates of every changed type of `unresolved` (the scope's graph merged without resolution decisions), store the
    decisions and return report lines."""
    store = ResolutionStore()
    stored = store.get(scope)
    asked = dict(entry.split("=", 1) for entry in (stored.asked if stored else []))
    groups = list(stored.groups) if stored else []
    lines: list[str] = []
    calls = 0
    for type_name, current in type_hashes(unresolved).items():
        if asked.get(type_name) == current and not force:
            continue
        entities = [e for e in unresolved if e.type == type_name]
        found, note = resolver.resolve_type(scope, type_name, entities)
        calls += 1
        if found is None:
            lines.append(f"  {type_name}: {note}; asked again next run")
            continue
        ids = {e.entity_id for e in entities}
        groups = [g for g in groups if g.keep not in ids] + found  # this type's earlier decisions are replaced
        asked[type_name] = current
        lines += [f"  {type_name}: {g.keep} = {', '.join(g.same)}" + (f" ({g.reason})" if g.reason else "") for g in found]
    if calls:
        store.save(scope, groups, [f"{t}={h}" for t, h in sorted(asked.items())], resolver.actor, clock.now_iso())
    return [f"{scope}: entity resolution, {calls} calls, {len(groups)} groups"] + lines
