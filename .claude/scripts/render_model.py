"""Renders a model file and its test file from a validated spec. Pure functions, no I/O."""
import json

import conventions as C
import field_spec as F
import naming


def q(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def render_field(field: dict) -> str:
    required, default = F.default_of(field)
    args = []
    if not required:
        args.append("default_factory=list" if default == "[]" else f"default={default}")
    args.append(f"description={q(field['description'])}")
    if field.get("question"):
        args.append(f"question={q(field['question'])}")
    if field.get("na_allowed"):
        args.append("na_allowed=True")
    if field.get("min_length"):
        args.append(f"min_length={field['min_length']}")
    if field.get("pattern"):
        args.append(f"pattern={q(field['pattern'])}")
    if field.get("scored") is False:
        args.append("scored=False")
    if field.get("binding"):
        args.append(f"binding={q(field['binding'])}")
    if field.get("render_as") in ("table", "numbered"):
        args.append(f'render_as="{field["render_as"]}"')
    body = "".join(f"        {arg},\n" for arg in args)
    return f"    {field['name']}: {field['type']} = {C.FIELD_HELPER}(\n{body}    )"


def needs_not_applicable(fields) -> bool:
    return any(C.NOT_APPLICABLE in F.type_names(f["type"]) for f in fields)


def field_import_lines(fields) -> list:
    """Imports every generated model file needs (the spec's own imports are added separately)."""
    lines = [
        f"from {C.BASE_MODEL_MODULE} import {C.BASE_MODEL}",
        f"from {C.FIELD_HELPER_MODULE} import {C.FIELD_HELPER}",
    ]
    if needs_not_applicable(fields):
        lines.append(f"from {C.NOT_APPLICABLE_MODULE} import {C.NOT_APPLICABLE}")
    return lines


def merge_imports(*groups) -> list:
    seen, ordered = set(), []
    for group in groups:
        for line in group:
            if line not in seen:
                seen.add(line)
                ordered.append(line)
    return ordered


def render_model(spec: dict) -> str:
    imports = merge_imports(field_import_lines(spec["fields"]), sorted(spec.get("imports", [])))
    fields = "\n".join(render_field(f) for f in spec["fields"])
    return (
        "\n".join(imports)
        + f"\n\n\nclass {spec['class']}({C.BASE_MODEL}):\n"
        + f'    """{spec["doc"].strip()}"""\n\n'
        + fields
        + "\n"
    )


def payload_literal(fields) -> str:
    return "{\n" + "".join(f"    {q(f['name'])}: {f['example']},\n" for f in fields) + "}"


def render_model_test(spec: dict, module: str) -> str:
    cls, fields = spec["class"], spec["fields"]
    mandatory = [f for f in fields if F.default_of(f)[0]]
    optional = [f for f in fields if not F.default_of(f)[0]]
    na_fields = [f["name"] for f in fields if f.get("na_allowed")]
    other_fields = [f["name"] for f in fields if not f.get("na_allowed")]

    imports = merge_imports(
        ["import pytest", "from pydantic import ValidationError", ""],
        [f"from {module} import {cls}", f"from {C.NOT_APPLICABLE_MODULE} import {C.NOT_APPLICABLE}"],
        sorted(spec.get("imports", [])),
    )
    out = ["\n".join(imports), "", f"MINIMAL = {payload_literal(mandatory) if mandatory else '{}'}", "", f"FULL = {payload_literal(fields)}", ""]

    out.append(f"\ndef test_minimal_payload_is_valid():\n    {cls}.model_validate(MINIMAL)\n")
    out.append(f"\ndef test_full_payload_round_trips():\n    obj = {cls}.model_validate(FULL)\n    assert {cls}.model_validate(obj.model_dump()) == obj\n")
    if mandatory:
        names = ", ".join(q(f["name"]) for f in mandatory)
        out.append(
            f"\n@pytest.mark.parametrize(\"field\", [{names}])\n"
            "def test_missing_mandatory_field_is_rejected(field):\n"
            "    payload = {k: v for k, v in FULL.items() if k != field}\n"
            "    with pytest.raises(ValidationError) as caught:\n"
            f"        {cls}.model_validate(payload)\n"
            "    assert field in {error[\"loc\"][0] for error in caught.value.errors()}\n"
        )
    out.append(
        f"\ndef test_extra_field_is_rejected():\n    with pytest.raises(ValidationError):\n        {cls}.model_validate({{**FULL, \"not_a_field\": \"x\"}})\n"
    )
    if optional:
        checks = []
        for f in optional:
            default = F.default_of(f)[1]
            expected = "[]" if default == "[]" else default
            operator = "is" if default in ("None", "True", "False") else "=="
            checks.append(f"    assert obj.{f['name']} {operator} {expected}")
        out.append(f"\ndef test_optional_fields_default_to_their_declared_defaults():\n    obj = {cls}.model_validate(MINIMAL)\n" + "\n".join(checks) + "\n")
    short = [f["name"] for f in fields if f.get("min_length")]
    if short:
        names = ", ".join(q(n) for n in short)
        out.append(
            f"\n@pytest.mark.parametrize(\"field\", [{names}])\n"
            "def test_empty_text_is_rejected_where_min_length_is_set(field):\n"
            "    with pytest.raises(ValidationError):\n"
            f"        {cls}.model_validate({{**FULL, field: \"\"}})\n"
        )
    patterned = [f["name"] for f in fields if f.get("pattern")]
    if patterned:
        names = ", ".join(q(n) for n in patterned)
        out.append(
            f"\n@pytest.mark.parametrize(\"field\", [{names}])\n"
            "def test_text_not_matching_the_pattern_is_rejected(field):\n"
            "    with pytest.raises(ValidationError):\n"
            f"        {cls}.model_validate({{**FULL, field: \"not matching the pattern\"}})\n"
        )
    if na_fields:
        names = ", ".join(q(n) for n in na_fields)
        out.append(
            f"\n@pytest.mark.parametrize(\"field\", [{names}])\n"
            "def test_not_applicable_is_accepted_where_allowed(field):\n"
            f"    {cls}.model_validate({{**FULL, field: {C.NOT_APPLICABLE}(reason=\"Not relevant for this test.\")}})\n"
        )
    if other_fields:
        names = ", ".join(q(n) for n in other_fields)
        out.append(
            f"\n@pytest.mark.parametrize(\"field\", [{names}])\n"
            "def test_not_applicable_is_rejected_where_not_allowed(field):\n"
            "    with pytest.raises(ValidationError):\n"
            f"        {cls}.model_validate({{**FULL, field: {C.NOT_APPLICABLE}(reason=\"Not relevant for this test.\")}})\n"
        )
    return "\n".join(out).replace("\n\n\n\n", "\n\n\n")


def test_file_name(class_name: str) -> str:
    return f"test_{naming.to_snake(class_name)}.py"
