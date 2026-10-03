"""Loads and validates the JSON specs the agent writes (the judgment part). Scripts do the rest.

Model spec:
    {"class": "Environment", "doc": "One deployment environment.", "role": "entitybound",
     "imports": ["from docfactory.entitymodels.facts.slo import Slo"],
     "fields": [ <field spec>, ... ]}

    role          document models only, required: the sub-folder of documentmodels/, one of
                  documents (a document body), shared (reused by every document type, supplied by the
                  caller) or entitybound (a section whose fields bind to entity facts)

Field spec (unknown keys are errors):
    name          snake_case identifier
    type          annotation text, e.g. "str", "list[Component]", "str | NotApplicable"
    description   for an LLM: meaning + an example ("e.g. ...") + what a good value looks like
    default       "REQUIRED" (mandatory) or "None", "[]", "''", "False", "Status.DRAFT", ...
    question      optional, asked when the field is missing; must end with "?"
    na_allowed    optional bool; true only if the type includes NotApplicable
    scored        optional bool, default true
    binding       document models only: "caller", "composed" or "<Entity>.<field>"
    min_length    optional int >= 1, only for a field typed exactly "str" (e.g. a non-empty reason)
    pattern       optional regular expression, only for a field typed "str" or "str | None" (e.g. an ISO 8601 timestamp)
    render_as     optional, "list" (default), "table" or "numbered": how a list field is rendered to Markdown ("numbered" is for lists of str)
    example       Python expression used as test data (obviously test data, never real knowledge)
"""
import ast
import json
import re

import conventions as C
import naming

FIELD_KEYS = {"name", "type", "description", "default", "question", "na_allowed", "scored", "binding", "example", "min_length", "render_as", "pattern"}
MODEL_KEYS = {"class", "doc", "role", "imports", "fields"}
REQUIRED = "REQUIRED"
EXAMPLE_MARKER = re.compile(r"e\.g\.|for example|such as|example", re.IGNORECASE)


class SpecError(ValueError):
    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise SpecError([f"cannot read {path}: {error}"]) from error


def type_names(annotation: str) -> set:
    tree = ast.parse(annotation, mode="eval")
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def type_problems(annotation: str) -> list:
    """Rules: no dict/Any/object, no bare list/set/tuple (items must be typed)."""
    try:
        tree = ast.parse(annotation, mode="eval")
    except SyntaxError as error:
        return [f"type {annotation!r} is not valid Python: {error.msg}"]
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        else:
            continue
        if name in C.FORBIDDEN_TYPE_NAMES:
            problems.append(f"type {annotation!r} uses {name}: use a typed model instead")
        elif name in C.BARE_CONTAINER_NAMES:
            parent = parents.get(node)
            if not (isinstance(parent, ast.Subscript) and parent.value is node):
                problems.append(f"type {annotation!r} has an untyped {name}: give it an item type")
    return problems


def is_expression(text: str) -> bool:
    try:
        ast.parse(text, mode="eval")
        return True
    except SyntaxError:
        return False


def default_of(field: dict):
    """(is_required, expression)"""
    default = field.get("default", REQUIRED)
    return default == REQUIRED, default


def _default_problem(default: str):
    if default in (REQUIRED, "[]"):
        return None
    try:
        ast.literal_eval(default)
        return None
    except (ValueError, SyntaxError):
        pass
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+", default):
        return None  # enum member such as Status.DRAFT
    return f"default {default!r} must be REQUIRED, [] , a literal, or an enum member"


def validate_field(field, kind=None) -> list:
    if not isinstance(field, dict):
        return ["field spec must be an object"]
    label = f"field {field.get('name', '?')!r}"
    problems = [f"{label}: unknown key {key!r}" for key in sorted(set(field) - FIELD_KEYS)]
    for key in ("name", "type", "description", "example"):
        if not isinstance(field.get(key), str) or not field.get(key, "").strip():
            problems.append(f"{label}: '{key}' is required")
    if problems and any("is required" in p for p in problems):
        return problems
    name, annotation, description = field["name"], field["type"], field["description"]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        problems.append(f"{label}: name must be snake_case")
    problems += [f"{label}: {p}" for p in type_problems(annotation)]
    if not is_expression(field["example"]):
        problems.append(f"{label}: example is not a Python expression")

    required, default = default_of(field)
    if not isinstance(default, str):
        problems.append(f"{label}: default must be a string holding a Python expression")
    elif (problem := _default_problem(default)):
        problems.append(f"{label}: {problem}")

    na_allowed = field.get("na_allowed", False)
    if not isinstance(na_allowed, bool) or not isinstance(field.get("scored", True), bool):
        problems.append(f"{label}: na_allowed and scored must be true or false")
    if not problems:
        has_na_type = C.NOT_APPLICABLE in type_names(annotation)
        if na_allowed and not has_na_type:
            problems.append(f"{label}: na_allowed needs the type to include {C.NOT_APPLICABLE}")
        if has_na_type and not na_allowed:
            problems.append(f"{label}: type includes {C.NOT_APPLICABLE} but na_allowed is not true")
        if na_allowed and required:
            problems.append(f"{label}: a mandatory field is answered by definition; N/A makes no sense")

    render_as = field.get("render_as")
    if render_as is not None and render_as not in ("list", "table", "numbered"):
        problems.append(f"{label}: render_as must be 'list', 'table' or 'numbered'")
    min_length = field.get("min_length")
    if min_length is not None:
        if not isinstance(min_length, int) or isinstance(min_length, bool) or min_length < 1:
            problems.append(f"{label}: min_length must be an integer >= 1")
        elif annotation.strip() != "str":
            problems.append(f"{label}: min_length is only for fields typed exactly 'str'")

    pattern = field.get("pattern")
    if pattern is not None:
        if annotation.strip() not in ("str", "str | None"):
            problems.append(f"{label}: pattern is only for fields typed 'str' or 'str | None'")
        else:
            try:
                re.compile(pattern)
            except (re.error, TypeError):
                problems.append(f"{label}: pattern is not a valid regular expression")

    if len(description.strip()) < 20:
        problems.append(f"{label}: description is too short to guide an LLM (min 20 characters)")
    elif field.get("scored", True) and not EXAMPLE_MARKER.search(description):
        problems.append(f"{label}: description needs an example of a good value (e.g. ...)")
    question = field.get("question")
    if question is not None and (not isinstance(question, str) or not question.strip().endswith("?")):
        problems.append(f"{label}: question must be a sentence ending with '?'")

    binding = field.get("binding")
    if kind == "document-model":
        if not binding:
            problems.append(f"{label}: document fields need a binding (caller, composed or Entity.field)")
    elif binding:
        problems.append(f"{label}: binding is only for document models")
    if binding and binding not in (C.BINDING_CALLER, C.BINDING_COMPOSED):
        if not re.fullmatch(r"[A-Z][A-Za-z0-9]*(\.[a-z][a-z0-9_]*)+", binding):
            problems.append(f"{label}: binding must be caller, composed or Entity.field[.subfield]")
    return problems


def validate_import(line) -> list:
    if not isinstance(line, str):
        return ["import must be a string"]
    try:
        tree = ast.parse(line)
    except SyntaxError:
        return [f"import {line!r} is not valid Python"]
    if len(tree.body) != 1 or not isinstance(tree.body[0], (ast.Import, ast.ImportFrom)):
        return [f"import {line!r} must be exactly one import statement"]
    names = {alias.name for alias in tree.body[0].names}
    banned = names & (C.FORBIDDEN_TYPE_NAMES | {"BaseModel"})
    return [f"import {line!r} brings in banned name(s) {sorted(banned)}"] if banned else []


def validate_model_spec(spec, kind) -> list:
    if not isinstance(spec, dict):
        return ["model spec must be an object"]
    problems = [f"unknown key {key!r}" for key in sorted(set(spec) - MODEL_KEYS)]
    name = spec.get("class")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Za-z0-9]*", name):
        problems.append("'class' must be a PascalCase class name")
    if not isinstance(spec.get("doc"), str) or len(spec.get("doc", "").strip()) < 10:
        problems.append("'doc' (class docstring, for an LLM reader) is required, min 10 characters")
    elif '"""' in spec["doc"] or "\\" in spec["doc"]:
        problems.append("'doc' must not contain triple quotes or backslashes")
    problems += naming.role_problems(kind, spec.get("role"))
    for line in spec.get("imports", []):
        problems += validate_import(line)
    fields = spec.get("fields")
    if not isinstance(fields, list) or not fields:
        problems.append("'fields' must be a non-empty list")
        return problems
    seen = set()
    for field in fields:
        problems += validate_field(field, kind)
        if isinstance(field, dict) and field.get("name") in seen:
            problems.append(f"duplicate field name {field['name']!r}")
        seen.add(field.get("name") if isinstance(field, dict) else None)
    return problems


def load_model_spec(path, kind) -> dict:
    spec = load_json(path)
    problems = validate_model_spec(spec, kind)
    if problems:
        raise SpecError(problems)
    return spec


def entity_fields(class_name: str):
    """Field names of an entity model, or None when the class is not found in entitymodels/."""
    files = naming.find_class(class_name, ("entitymodels",))
    if len(files) != 1:
        return None
    tree = ast.parse(files[0].read_text(encoding="utf-8"))
    cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == class_name)
    return {n.target.id for n in cls.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}


def binding_problems(fields) -> list:
    """A fact binding `Entity.field[.sub]` must point at an existing entity model and field."""
    problems = []
    for field in fields:
        binding = field.get("binding")
        if not binding or binding in (C.BINDING_CALLER, C.BINDING_COMPOSED):
            continue
        entity, attribute = binding.split(".")[:2]
        known = entity_fields(entity)
        if known is None:
            problems.append(f"field {field['name']!r}: binding {binding!r}: entity model {entity} does not exist yet")
        elif attribute not in known:
            problems.append(f"field {field['name']!r}: binding {binding!r}: {entity} has no field {attribute!r}")
    return problems
