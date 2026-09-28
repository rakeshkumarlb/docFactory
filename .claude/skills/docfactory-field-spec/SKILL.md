---
name: docfactory-field-spec
description: How to write the JSON spec for a docFactory model or field (description, question, default, na_allowed, binding, example). Reference for the pydantic-developer-agent; the scripts validate everything written here.
user-invocable: false
---

# Writing a model / field spec

You supply the **judgment**: names, types, descriptions, questions, defaults. The scripts in `.claude/scripts/` turn a valid spec into code and reject an invalid one with a precise message. Never hand-write a model file that a script can generate.

## Model spec (`<scratchpad>/<ClassName>.spec.json`, never inside the repo)

```json
{
  "class": "Environment",
  "doc": "One deployment environment of an application (e.g. Production).",
  "imports": ["from docfactory.entitymodels.slo import Slo"],
  "fields": [
    {
      "name": "url",
      "type": "str | NotApplicable",
      "default": "None",
      "description": "Base URL of the environment, e.g. https://kitchen.example.com. N/A when it has no URL.",
      "question": "What is the base URL of this environment?",
      "na_allowed": true,
      "example": "\"https://example.test\""
    }
  ]
}
```

Unknown keys are errors. Keys: `class`, `doc`, `role`, `imports`, `fields`; per field `name`, `type`, `description`, `default`, `question`, `na_allowed`, `scored`, `binding`, `min_length`, `example`.

`role` is for **document models only, and required there**: `documents` (a document body), `shared` (reused by every document type, supplied by the caller) or `entitybound` (a section whose fields bind to entity facts). It picks the sub-folder of `documentmodels/`. Other kinds must not have it.

## Rules per key (all checked by `field_spec.py`)

| Key | Rule |
|---|---|
| `name` | snake_case |
| `type` | Typed only. No `dict`, `Dict`, `Any`, `object`, `Mapping`; no bare `list`/`set`/`tuple`. Lists are `list[ItemModel]` or `list[str]`. Each nested model is a class in its own file, imported through `imports`. Optional single values are `X | None` |
| `description` | For an LLM reader, at least 20 characters: what it means, **an example of a good value (`e.g. ...`)**, what "good" looks like. Not needed only when `scored` is false |
| `question` | Asked when the field is missing. Ends with `?`. Omit it when the description already reads as a question |
| `default` | `"REQUIRED"` (mandatory) or an honest empty default: `"None"`, `"[]"`, `"''"`, `"False"`, `"Status.DRAFT"`. A default is a placeholder, never knowledge |
| mandatory | Only what identifies the object or makes it meaningless. When in doubt, optional |
| `na_allowed` | `true` only when "not applicable" is a real answer to the question. Then the type must include `NotApplicable` (e.g. `str \| NotApplicable`) and the default must not be `REQUIRED`. Otherwise the type must not mention it |
| `scored` | `false` only for purely technical fields (excluded from completeness) |
| `binding` | Document models only, and required there: `"caller"` (supplied by the caller, e.g. document control), `"composed"` (a nested section model that carries its own bindings) or `"Entity.field"` (the entity model and field must already exist) |
| `min_length` | Optional integer >= 1, only for a field typed exactly `str`: use it for mandatory text that must not be empty (names, reasons). The generated test checks an empty string is rejected |
| `example` | A Python expression used as test data. Obviously test data (`"Test-Env"`), never something that looks like real knowledge |
| `imports` | Single import statements for the nested types and enums you use. `BaseModel`, `Any`, `dict` are refused. `DocFactoryModel`, `doc_field` and `NotApplicable` are added automatically |

## Never

- Invent field content, defaults or examples that pass as knowledge to lift completeness.
- Put two classes in one file. Item types and enums each get their own file (create them first, deepest first).
- Guess. If the field list, meaning or question of a field is missing, stop and return the open questions in your report.

## Enums

An `Enum`/`StrEnum` is a class, so it gets its own file in the folder of its owner (`entitymodels/`, `documentmodels/<role>/` or `models/`), named after the class in snake_case, with a one-line docstring, no logic, and its own test file (`tests/test_<snake>.py`, checking members and values). Scripts do not generate enums; write it by hand, then run the quality gate.
