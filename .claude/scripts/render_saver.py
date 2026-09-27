"""Renders a saver file and its test file from the model spec. Pure functions, no I/O."""
import ast
import json

import conventions as C
import field_spec as F
import naming
import render_model


def _mutate_string_leaf(value):
    """(mutated value, found) - the first string leaf inside value (recursing through dict/list), '-changed' appended."""
    if isinstance(value, str):
        return value + "-changed", True
    if isinstance(value, list):
        for index, item in enumerate(value):
            mutated, found = _mutate_string_leaf(item)
            if found:
                new = list(value)
                new[index] = mutated
                return new, True
        return value, False
    if isinstance(value, dict):
        for key, item in value.items():
            mutated, found = _mutate_string_leaf(item)
            if found:
                new = dict(value)
                new[key] = mutated
                return new, True
        return value, False
    return value, False


def changed_field(spec: dict):
    """(name, changed value source) of the first field with a mutable string leaf in its example, else None.

    A field's example is a literal (a plain string, or a dict/list composed of literals for a nested
    or list-of-model field, per the FULL/MINIMAL convention in render_model.payload_literal). The first
    string leaf found, at any depth, is mutated; the whole (possibly nested) value is re-rendered with
    repr() so the result is always valid Python source, not just valid for plain string fields.
    """
    for field in spec["fields"]:
        try:
            value = ast.literal_eval(field["example"])
        except (ValueError, SyntaxError):
            continue
        mutated, found = _mutate_string_leaf(value)
        if found:
            return field["name"], repr(mutated)
    return None


def render_saver(info: dict, patterns: list) -> str:
    model, saver = info["model_class"], info["saver_class"]
    literal = "(" + ", ".join(json.dumps(p) for p in patterns) + ("," if len(patterns) == 1 else "") + ")"
    return (
        f"from {C.BASE_SAVER_MODULE} import {C.BASE_SAVER}\n"
        f"from {info['model_module']} import {model}\n\n\n"
        f"class {saver}({C.BASE_SAVER}[{model}]):\n"
        f'    """Saves {model} objects."""\n\n'
        f"    model = {model}\n"
        f"    key_patterns = {literal}\n"
    )


def render_saver_test(info: dict, spec: dict, patterns: list) -> str:
    saver_kind = C.SAVERS[info["kind"]]
    model, saver = info["model_class"], info["saver_class"]
    key = naming.sample_key(patterns[0])
    component_key = next((naming.sample_key(p) for p in patterns if "{component}" in p), None)
    mandatory = next((f["name"] for f in spec["fields"] if F.default_of(f)[0]), None)
    name, changed = changed_field(spec)
    imports = render_model.merge_imports(
        ["import hashlib", "import json", "import os", "import sqlite3", "", "import pytest", ""],
        [f"from {info['model_module']} import {model}", f"from {info['saver_module']} import {saver}"],
        sorted(spec.get("imports", [])),
    )
    out = [
        "\n".join(imports),
        "",
        'pytestmark = pytest.mark.usefixtures("tmp_db")',
        "",
        f"SAVER = {saver}()",
        f'KEY = "{key}"',
        f"_FULL = {render_model.payload_literal(spec['fields'])}",
        f"PAYLOAD = {model}.model_validate(_FULL).model_dump(mode=\"json\")",
        f"CHANGED = {model}.model_validate({{**_FULL, {json.dumps(name)}: {changed}}}).model_dump(mode=\"json\")",
        "",
        "",
        "def _row(key):",
        '    con = sqlite3.connect(os.environ["DOCFACTORY_DB"])',
        "    con.row_factory = sqlite3.Row",
        "    try:",
        f'        return con.execute("SELECT * FROM {saver_kind["table"]} WHERE {saver_kind["key_column"]} = ?", (key,)).fetchone()',
        "    finally:",
        "        con.close()",
        "",
        "",
        "def test_created_stores_canonical_json_hash_app_id_and_version_1():",
        f"    result = SAVER.save(KEY, PAYLOAD)",
        '    assert result.ok and result.action == "CREATED" and result.version == 1',
        "    row = _row(KEY)",
        '    stored = json.loads(row["Value"])',
        f"    assert stored == {model}.model_validate(PAYLOAD).model_dump(mode=\"json\")",
        '    assert row["Value"] == json.dumps(stored, sort_keys=True, separators=(",", ":"), ensure_ascii=False)',
        '    assert row["Hashcode"] == hashlib.sha256(row["Value"].encode("utf-8")).hexdigest()',
        f'    assert row["AppID"] == {naming.app_id_of(key)!r}',
        '    assert row["Version"] == 1 and 0 <= row["Completeness"] <= 100',
        "",
        "",
        "def test_same_payload_is_unchanged_and_touches_nothing():",
        f"    SAVER.save(KEY, PAYLOAD)",
        "    before = dict(_row(KEY))",
        f"    result = SAVER.save(KEY, PAYLOAD)",
        '    assert result.ok and result.action == "UNCHANGED" and result.version == 1',
        "    assert dict(_row(KEY)) == before",
        "",
        "",
        "def test_changed_payload_updates_and_changing_back_is_a_new_version():",
        f"    first = SAVER.save(KEY, PAYLOAD)",
        f"    second = SAVER.save(KEY, CHANGED)",
        '    assert second.action == "UPDATED" and second.version == 2 and second.hashcode != first.hashcode',
        f"    third = SAVER.save(KEY, PAYLOAD)",
        '    assert third.action == "UPDATED" and third.version == 3 and third.hashcode == first.hashcode',
        "",
        "",
        "def test_invalid_payload_is_rejected_and_nothing_is_written():",
        f'    result = SAVER.save(KEY, {{**PAYLOAD, "not_a_field": "x"}})',
        '    assert not result.ok and result.action == "REJECTED"',
        "    assert result.errors and all(e.path and e.message and e.error_type for e in result.errors)",
        "    assert _row(KEY) is None",
    ]
    if mandatory:
        out += [
            "",
            "",
            "def test_missing_mandatory_field_error_carries_description_and_question():",
            f'    payload = {{k: v for k, v in PAYLOAD.items() if k != "{mandatory}"}}',
            f"    result = SAVER.save(KEY, payload)",
            '    assert result.action == "REJECTED" and _row(KEY) is None',
            f'    error = next(e for e in result.errors if "{mandatory}" in e.path)',
            "    assert error.field_description and error.question",
        ]
    if component_key:
        out += [
            "",
            "",
            "def test_component_key_stores_the_application_as_app_id():",
            f'    result = SAVER.save("{component_key}", PAYLOAD)',
            '    assert result.ok and result.action == "CREATED"',
            f'    assert _row("{component_key}")["AppID"] == {naming.app_id_of(component_key)!r}',
        ]
    return "\n".join(out) + "\n"
