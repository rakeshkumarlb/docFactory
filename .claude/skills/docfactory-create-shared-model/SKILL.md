---
name: docfactory-create-shared-model
description: Build the base classes and package skeleton (DocFactoryModel, doc_field, NotApplicable, SaveResult, the bundle package) or create one shared model in docfactory/models/
argument-hint: skeleton | <ClassName> [what it is for]
context: fork
agent: docfactory-pydantic-developer-agent
model: sonnet
background: false
---

You are running as the **docfactory-pydantic-developer-agent**. Follow these steps exactly, in order. Scripts are run from the project root. Read `CLAUDE.md` first (Models, The bundle, Completeness, Tests).

Request: $ARGUMENTS

## Mode

- `skeleton` -> build everything below, stage by stage (part 1). Idempotent: a file that already exists and passes its tests is skipped, never overwritten.
- `<ClassName>` -> create that one shared model (part 2).

Run the quality gate (`docfactory-quality-gate`) after **each** stage of part 1, not only at the end.

## Part 1: skeleton

Hand-written stages are the one-time code the scripts derive from. Everything has a test in `tests/test_<file stem>.py`. A module never defines two classes; `doc_field`, `canonical`, `completeness`, `validation_errors` and `key_patterns` are function modules (no class).

### Stage A: project files and base model
1. `pyproject.toml`: project `docfactory`, dependency `pydantic>=2`, `[tool.pytest.ini_options]` with `pythonpath = ["."]` and `testpaths = ["tests"]`. Empty `docfactory/__init__.py`, and an `__init__.py` in each of the folders `models`, `entitymodels` (+ `facts`, `items`), `documentmodels` and `bundle`.
2. `docfactory/models/doc_factory_model.py`: `DocFactoryModel(pydantic.BaseModel)` with `model_config = ConfigDict(extra="forbid")` and a docstring. The only class allowed to derive from `BaseModel` directly. Test: an extra field is rejected.
3. `docfactory/models/doc_field.py`: a function with exactly this contract (the generators emit calls to it):
   `doc_field(default=..., *, default_factory=None, description, question=None, na_allowed=False, scored=True, min_length=None)`.
   It returns `pydantic.Field(...)`: `description` is the field's description; `question` (falling back to `description`), `na_allowed`, `scored` go into `json_schema_extra` under those key names; `min_length` is forwarded to `Field`; `default=...` means required. Test: each piece of metadata reads back from `Model.model_fields[name].json_schema_extra`; required vs default vs default_factory.

### Stage B: shared models (scaffolded)
For each, follow part 2 in this order: `NotApplicable`, `SaveAction`, `SaveError`, `SaveResult`. Contracts:
- `NotApplicable`: one mandatory `reason: str` with `min_length: 1` (an empty reason is a validation error).
- `SaveAction`: `StrEnum` with `CREATED`, `UPDATED`, `UNCHANGED`, `REJECTED` (hand-written, own file, own test).
- `SaveError`: `path` (dotted, e.g. `environments.0.name`), `message`, `error_type` mandatory strings; `received`, `expected`, `field_description`, `question` optional `str | None` (JSON text or plain text, never `Any`).
- `SaveResult`: `ok: bool`, `key: str`, `action: SaveAction` mandatory; `version: int | None`, `hashcode: str | None`, `completeness: float | None` default `None`; `errors: list[SaveError]` default `[]`.

### Stage C: infrastructure (hand-written, in this order)
1. `docfactory/canonical.py`: `canonical_json(value) -> str` (sorted keys, separators `(",", ":")`, `ensure_ascii=False`) and `sha256_hex(text) -> str` (SHA-256 of UTF-8). Tests: key order does not change output; known hash.
2. `docfactory/completeness.py`: `completeness(obj) -> float` (0-100) and `field_counts(obj) -> tuple[int, int]` (answered, total) implementing `CLAUDE.md` "Completeness" exactly: a field is answered when its value differs from its default (compare with `default` or `default_factory()`), or is a `NotApplicable`; mandatory fields are answered; `scored=False` fields are excluded (read `json_schema_extra`); nested model -> recurse over its fields, absent = one unanswered field; list of models -> fields of every item, empty list = one unanswered field; `NotApplicable` on a list or nested field = one answered field. Tests: every "Item-level scoring" and "Defaults do not count" case listed in `CLAUDE.md`, each with the arithmetic in a comment; use test-only models declared in the test module.
3. `docfactory/key_patterns.py`: `SHARED = "Shared"` and `pattern_matches(pattern, key)` (whole-segment match; `{app}`, `{component}`, `{doctype}` stand for one non-empty segment; `Shared` is not an `{app}`). `docfactory/validation_errors.py`: `json_text(value)` and `validation_errors(model, pydantic_error) -> list[SaveError]` (every error carries `path`, Pydantic `message` and `error_type`, `received` and `expected` as text, and the field's `description` as `field_description` plus its `question`, found by walking `model_fields` along the error location). Tests: the "Missing mandatory... / Wrong type / Bad enum / Extra field / error inside a list item" cases of `CLAUDE.md` "Tests", with test-only models declared in the test module.
4. `docfactory/bundle/`: the OKF bundle store, hand-written once (see `CLAUDE.md` "The bundle" for every contract): `fact_registry.py` (the `FACT_SPECS` dict, one entry per fact; `scaffold_model.py` adds entries to it), `paths.py`, `file_io.py`, `key_check.py`, `BundleStore` and the concept-file readers/writers. This stage only checks that `docfactory/bundle/fact_registry.py` exists with a `FACT_SPECS = {` dict; if the bundle package is missing, stop with `Gaps: the bundle package is hand-written; ask the maintainer`.
5. `tests/conftest.py`: fixture `tmp_bundle` sets `DOCFACTORY_BUNDLE` and `DOCFACTORY_OUTPUT` to folders under `tmp_path` (monkeypatch). Every test that touches the bundle or the output folder uses it.
6. `tests/test_structure.py`: the `CLAUDE.md` "Tests: Structure" cases. Load `.claude/scripts/check_structure.py` with `importlib` from its path and assert `collect([], want_tests=False) == []`; add the runtime checks scripts cannot do: every field of every model class in `models/`, `entitymodels/`, `documentmodels/` has a non-empty description and no annotation contains `dict` or `Any`.

Facts are written and read only through `BundleStore` (`BundleStore().write_fact(key, payload)`); there are no savers, no database and no registry besides `fact_registry.py`.

Then run the gate one last time and stop. Do **not** create entities or documents here.

## Part 2: one shared model

1. Confirm the class is infrastructure or an item type used by **both** entities and documents. If it belongs to one side only, stop and say so.
2. `python .claude/scripts/resolve_target.py shared-model <ClassName>`. Exit 1 means stop and report `errors`. If `docfactory/models/doc_factory_model.py` or `doc_field.py` is missing, stop: `Gaps: run /docfactory-create-shared-model skeleton first`.
3. Get the fields from the request and `CLAUDE.md`. If unclear, stop and return questions under `Gaps`; do not invent fields.
4. Write `<scratchpad>/<ClassName>.spec.json` following `docfactory-field-spec`.
5. `python .claude/scripts/scaffold_model.py shared-model <spec.json> --dry-run`, fix rejections, then run it without `--dry-run`. Shared models are never facts.
6. Quality gate (`docfactory-quality-gate`).
