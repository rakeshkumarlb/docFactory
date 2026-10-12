"""Score a scope's entity graph (and facts) against an expectations file such as tests/corpus/jobmatch_expectations.json. Read-only, no LLM.

Per type: expected entities found (a produced entity matches when its name or an alias equals the expected name or an expected alias,
compared with `name_key`), missing ones, duplicates (two produced entities matching one expected), forbidden ones produced, and extras
(produced, neither expected, allowed nor forbidden). Relations: an expected (source, target) pair is found when the source entity links to the
target entity. Fields: the item of the fact that holds the entity (found by the expected name or aliases) has the field containing the text.
"""
import json
from pathlib import Path

from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.entity_store import EntityStore
from docfactory.extract.model_shapes import identity_field
from docfactory.models.entity_record import EntityRecord
from docfactory.recognize.entity_resolver import name_key
from docfactory.recognize.type_vocabulary import item_types


def _keys(names: list[str]) -> set[str]:
    return {name_key(n) for n in names if name_key(n)}


def _entity_keys(record: EntityRecord) -> set[str]:
    return _keys([record.name, *record.aliases])


def _find(graph: list[EntityRecord], names: list[str]) -> EntityRecord | None:
    wanted = _keys(names)
    return next((r for r in graph if _entity_keys(r) & wanted), None)


def score_types(graph: list[EntityRecord], expected_types: dict) -> tuple[list[str], int, int]:
    """(report lines, expected entities found, expected entities in total) per type."""
    lines, found_total, expected_total = [], 0, 0
    for type_name, spec in expected_types.items():
        produced = [r for r in graph if r.type == type_name]
        missing, duplicates, matched = [], [], set()
        for expected in spec["expected"]:
            keys = _keys([expected["name"], *expected.get("aliases", [])])
            hits = [r for r in produced if _entity_keys(r) & keys]
            matched |= {r.entity_id for r in hits}
            if not hits:
                missing.append(expected["name"])
            elif len(hits) > 1:
                duplicates.append(f"{expected['name']} = {', '.join(r.name for r in hits)}")
        forbidden_keys, allowed_keys = _keys(spec.get("forbidden", [])), _keys(spec.get("allowed", []))
        forbidden = [r.name for r in produced if _entity_keys(r) & forbidden_keys]
        extras = [r.name for r in produced if r.entity_id not in matched and not _entity_keys(r) & (forbidden_keys | allowed_keys)]
        found = len(spec["expected"]) - len(missing)
        found_total, expected_total = found_total + found, expected_total + len(spec["expected"])
        lines.append(f"{type_name}: {found}/{len(spec['expected'])} found, {len(produced)} produced")
        lines += [f"  missing: {', '.join(missing)}"] if missing else []
        lines += [f"  duplicates: {'; '.join(duplicates)}"] if duplicates else []
        lines += [f"  FORBIDDEN: {', '.join(forbidden)}"] if forbidden else []
        lines += [f"  extra: {', '.join(extras)}"] if extras else []
    return lines, found_total, expected_total


def score_relations(graph: list[EntityRecord], relations: list[dict]) -> list[str]:
    lines = []
    for relation in relations:
        source, target = _find(graph, [relation["source"]]), _find(graph, [relation["target"]])
        ok = source is not None and target is not None and any(link.target == target.entity_id for link in source.links)
        lines.append(f"  {'ok ' if ok else 'NO '} {relation['source']} -> {relation['target']} ({relation.get('note', '')})")
    return lines


def score_fields(scope: str, fields: list[dict], expected_types: dict) -> list[str]:
    lines, store, mapping = [], BundleStore(), item_types()
    for check in fields:
        label = f"{check['type']} {check['entity']}.{check['field']} contains {check['contains']!r}"
        if check["type"] not in mapping:
            lines.append(f"  NO  {label}: no fact holds this type")
            continue
        entity, field, model = mapping[check["type"]]
        fact = store.read_fact(f"{scope}.{entity}")
        items = json.loads(fact.value).get(field, []) if fact else []
        aliases = next((e.get("aliases", []) for e in expected_types.get(check["type"], {}).get("expected", []) if e["name"] == check["entity"]), [])
        keys = _keys([check["entity"], *aliases])
        item = next((i for i in items if name_key(str(i.get(identity_field(model), ""))) in keys), None)
        value = "" if item is None else json.dumps(item.get(check["field"], ""), ensure_ascii=False)
        ok = check["contains"].lower() in value.lower()
        lines.append(f"  {'ok ' if ok else 'NO '} {label}" + ("" if ok else (": no such item" if item is None else f": {value[:80]}")))
    return lines


def score(scope: str, expectations_file: Path) -> str:
    """The plain-text score of `scope` against the expectations file."""
    expectations = json.loads(Path(expectations_file).read_text(encoding="utf-8"))
    graph = EntityStore().list(scope)
    type_lines, found, total = score_types(graph, expectations["types"])
    relation_lines = score_relations(graph, expectations.get("relations", []))
    field_lines = score_fields(scope, expectations.get("fields", []), expectations["types"])
    return "\n".join([f"{scope}: {found}/{total} expected entities found ({len(graph)} entities in the graph)", *type_lines,
                      f"relations ({sum(l.startswith('  ok') for l in relation_lines)}/{len(relation_lines)}):", *relation_lines,
                      f"fields ({sum(l.startswith('  ok') for l in field_lines)}/{len(field_lines)}):", *field_lines])
