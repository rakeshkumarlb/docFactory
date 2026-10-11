"""Renders the test file of a new fact (an entity model in entitymodels/facts/) from its model spec. Pure functions, no I/O.

The test saves the fact through BundleStore: it is stored as an OKF concept file with canonical JSON, a hash and a version, an unchanged
payload changes nothing, a changed one is a new version, and an invalid one is rejected with feedback and writes nothing.
"""
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


def render_fact_test(info: dict, spec: dict, scope: str) -> str:
    """The test file for the fact `info["model_class"]`; `scope` is `app` or `shared` (decides the sample keys)."""
    model = info["model_class"]
    key = naming.sample_key(naming.fact_pattern(model, scope)[0])
    component_key = naming.sample_key(naming.fact_pattern(model, scope)[1]) if scope == "app" else None
    mandatory = next((f["name"] for f in spec["fields"] if F.default_of(f)[0]), None)
    name, changed = changed_field(spec)
    imports = render_model.merge_imports(
        ["import pytest", ""],
        [
            f"from {info['model_module']} import {model}",
            "from docfactory.bundle.bundle_store import BundleStore",
            "from docfactory.canonical import canonical_json, sha256_hex",
            "from docfactory.models.save_action import SaveAction",
        ],
        sorted(spec.get("imports", [])),
    )
    out = [
        "\n".join(imports),
        "",
        'pytestmark = pytest.mark.usefixtures("tmp_bundle")',
        "",
        f'KEY = "{key}"',
        f"_FULL = {render_model.payload_literal(spec['fields'])}",
        f'PAYLOAD = {model}.model_validate(_FULL).model_dump(mode="json")',
        f'CHANGED = {model}.model_validate({{**_FULL, {json.dumps(name)}: {changed}}}).model_dump(mode="json")',
        "",
        "",
        "def test_created_is_a_concept_file_with_canonical_json_hash_and_version_1():",
        "    result = BundleStore().write_fact(KEY, PAYLOAD)",
        "    assert result.ok and result.action == SaveAction.CREATED and result.version == 1",
        "    record = BundleStore().read_fact(KEY)",
        f'    assert record.value == canonical_json({model}.model_validate(PAYLOAD).model_dump(mode="json"))',
        "    assert record.hashcode == sha256_hex(record.value) == result.hashcode",
        f"    assert record.app_id == {naming.app_id_of(key)!r}",
        "    assert record.version == 1 and 0 <= record.completeness <= 100",
        "",
        "",
        "def test_same_payload_is_unchanged_and_touches_nothing():",
        "    BundleStore().write_fact(KEY, PAYLOAD)",
        "    before = BundleStore().read_fact(KEY)",
        "    result = BundleStore().write_fact(KEY, PAYLOAD)",
        "    assert result.ok and result.action == SaveAction.UNCHANGED and result.version == 1",
        "    assert BundleStore().read_fact(KEY) == before",
        "",
        "",
        "def test_changed_payload_updates_and_changing_back_is_a_new_version():",
        "    first = BundleStore().write_fact(KEY, PAYLOAD)",
        "    second = BundleStore().write_fact(KEY, CHANGED)",
        "    assert second.action == SaveAction.UPDATED and second.version == 2 and second.hashcode != first.hashcode",
        "    third = BundleStore().write_fact(KEY, PAYLOAD)",
        "    assert third.action == SaveAction.UPDATED and third.version == 3 and third.hashcode == first.hashcode",
        "",
        "",
        "def test_invalid_payload_is_rejected_and_nothing_is_written():",
        '    result = BundleStore().write_fact(KEY, {**PAYLOAD, "not_a_field": "x"})',
        "    assert not result.ok and result.action == SaveAction.REJECTED",
        "    assert result.errors and all(e.path and e.message and e.error_type for e in result.errors)",
        "    assert BundleStore().read_fact(KEY) is None",
    ]
    if mandatory:
        out += [
            "",
            "",
            "def test_missing_mandatory_field_error_carries_description_and_question():",
            f'    payload = {{k: v for k, v in PAYLOAD.items() if k != "{mandatory}"}}',
            "    result = BundleStore().write_fact(KEY, payload)",
            "    assert result.action == SaveAction.REJECTED and BundleStore().read_fact(KEY) is None",
            f'    error = next(e for e in result.errors if "{mandatory}" in e.path)',
            "    assert error.field_description and error.question",
        ]
    if component_key:
        out += [
            "",
            "",
            "def test_component_key_stores_the_application_as_app_id():",
            f'    result = BundleStore().write_fact("{component_key}", PAYLOAD)',
            "    assert result.ok and result.action == SaveAction.CREATED",
            f'    assert BundleStore().read_fact("{component_key}").app_id == {naming.app_id_of(component_key)!r}',
        ]
    return "\n".join(out) + "\n"
