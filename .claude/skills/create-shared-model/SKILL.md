---
name: create-shared-model
description: Build the base classes and package skeleton (DocFactoryModel, doc_field, NotApplicable, SaveResult, BaseSaver, db) or create one shared model in docfactory/models/
argument-hint: skeleton | <ClassName> [what it is for]
disable-model-invocation: true
context: fork
agent: pydantic-developer-agent
model: sonnet
background: false
---

You are running as the **pydantic-developer-agent**. Follow these steps exactly, in order. Scripts are run from the project root. Read `CLAUDE.md` first (Models, Database, Completeness, Savers, Tests).

Request: $ARGUMENTS

## Mode

- `skeleton` -> build everything below, stage by stage (part 1). Idempotent: a file that already exists and passes its tests is skipped, never overwritten.
- `<ClassName>` -> create that one shared model (part 2).

Run the quality gate (`docfactory-quality-gate`) after **each** stage of part 1, not only at the end.

## Part 1: skeleton

Hand-written stages are the one-time code the scripts derive from. Everything has a test in `tests/test_<file stem>.py`. A module never defines two classes; `doc_field`, `canonical`, `completeness` and `db` are function modules (no class).

### Stage A: project files and base model
1. `pyproject.toml`: project `docfactory`, dependency `pydantic>=2`, `[tool.pytest.ini_options]` with `pythonpath = ["."]` and `testpaths = ["tests"]`. Empty `docfactory/__init__.py`, and an `__init__.py` in each of the five folders.
2. `docfactory/models/doc_factory_model.py`: `DocFactoryModel(pydantic.BaseModel)` with `model_config = ConfigDict(extra="forbid")` and a docstring. The only class allowed to derive from `BaseModel` directly. Test: an extra field is rejected.
3. `docfactory/models/doc_field.py`: a function with exactly this contract (the generators emit calls to it):
   `doc_field(default=..., *, default_factory=None, description, question=None, na_allowed=False, scored=True, binding=None, min_length=None)`.
   It returns `pydantic.Field(...)`: `description` is the field's description; `question` (falling back to `description`), `na_allowed`, `scored`, `binding` go into `json_schema_extra` under those key names; `min_length` is forwarded to `Field`; `default=...` means required. Test: each piece of metadata reads back from `Model.model_fields[name].json_schema_extra`; required vs default vs default_factory.

### Stage B: shared models (scaffolded)
For each, follow part 2 in this order: `NotApplicable`, `SaveAction`, `SaveError`, `SaveResult`. Contracts:
- `NotApplicable`: one mandatory `reason: str` with `min_length: 1` (an empty reason is a validation error).
- `SaveAction`: `StrEnum` with `CREATED`, `UPDATED`, `UNCHANGED`, `REJECTED` (hand-written, own file, own test).
- `SaveError`: `path` (dotted, e.g. `environments.0.name`), `message`, `error_type` mandatory strings; `received`, `expected`, `field_description`, `question` optional `str | None` (JSON text or plain text, never `Any`).
- `SaveResult`: `ok: bool`, `key: str`, `action: SaveAction` mandatory; `version: int | None`, `hashcode: str | None`, `completeness: float | None` default `None`; `errors: list[SaveError]` default `[]`.

### Stage C: infrastructure (hand-written, in this order)
1. `docfactory/canonical.py`: `canonical_json(value) -> str` (sorted keys, separators `(",", ":")`, `ensure_ascii=False`) and `sha256_hex(text) -> str` (SHA-256 of UTF-8). Tests: key order does not change output; known hash.
2. `docfactory/completeness.py`: `completeness(obj) -> float` (0-100) and `field_counts(obj) -> tuple[int, int]` (answered, total) implementing `CLAUDE.md` "Completeness" exactly: a field is answered when its value differs from its default (compare with `default` or `default_factory()`), or is a `NotApplicable`; mandatory fields are answered; `scored=False` fields are excluded (read `json_schema_extra`); nested model -> recurse over its fields, absent = one unanswered field; list of models -> fields of every item, empty list = one unanswered field; `NotApplicable` on a list or nested field = one answered field. Tests: every "Item-level scoring" and "Defaults do not count" case listed in `CLAUDE.md`, each with the arithmetic in a comment; use test-only models declared in the test module.
3. `docfactory/db.py`: `db_path()` (env `DOCFACTORY_DB`, else `db/docfactory.sqlite` under the project root), `connect()` (creates the file/folder and runs `init_schema`), `init_schema(con)` (idempotent `CREATE TABLE IF NOT EXISTS` for `KnowledgeFacts` keyed by `FactKey` and `DocumentOutputs` keyed by `DocumentKey`; columns `Value TEXT NOT NULL`, `Hashcode TEXT NOT NULL`, `AppID TEXT NULL`, `Completeness REAL NOT NULL`, `Version INTEGER NOT NULL`), `get_row(table, key)`, `write_row(table, key, value, hashcode, app_id, completeness, version)` (one transaction, insert or replace), `list_rows(table, app_id=None)`. Parameterised SQL only; table names come from a fixed whitelist. Tests use a temporary file.
4. `docfactory/base_saver.py`: `BaseSaver(Generic[M])` with class attributes `model` and `key_patterns` and method `save(key, payload, app_id=None) -> SaveResult`. Table is `DocumentOutputs` when the concrete class's `__module__` contains `documentsaver`, else `KnowledgeFacts`. Behaviour, in this order, exactly `CLAUDE.md` "BaseSaver": (1) key must match one of `key_patterns` (whole-segment placeholders `{app}`, `{component}`, `{doctype}`), derive AppID (`Shared` -> NULL, else first segment, case-sensitive; a passed `app_id` that differs is rejected); (2) validate with the model; (3) `canonical_json(model.model_dump(mode="json"))` and hash; (4) same hash -> `UNCHANGED` (row untouched), no row -> `CREATED` version 1, different hash -> `UPDATED` version + 1; (5) completeness; (6) write in one transaction, never on `REJECTED`. Never raise for bad input: every failure is a `SaveResult` with `ok=False`, `action=REJECTED` and `SaveError`s carrying `path`, Pydantic `message` and `error_type`, `received` and `expected` as text, and the field's `description` (as `field_description`) and `question`, found by walking `model_fields` along the error location. Tests: every "Valid payload / Same payload / Component keys / Key order / Missing mandatory... / Shared / a key matching none of the saver's own `key_patterns` is rejected" case in `CLAUDE.md` "Tests", using test-only model and saver classes declared in the test module (set `__module__ = "docfactory.documentsaver.test"` in a class body to test the document table).
5. `tests/conftest.py`: fixture `tmp_db` sets `DOCFACTORY_DB` to a file under `tmp_path` (monkeypatch) and initialises the schema. Every test that touches the database uses it.
6. `tests/test_structure.py`: the `CLAUDE.md` "Tests: Structure" cases. Load `.claude/scripts/check_structure.py` with `importlib` from its path and assert `collect([], want_tests=False) == []`; add the runtime checks scripts cannot do: every field of every model class in `models/`, `entitymodels/`, `documentmodels/` has a non-empty description and no annotation contains `dict` or `Any`.

Phase 1 has **no registry, no generic `save_fact` / `save_document` dispatchers and no read-side wrappers** (all Phase 2). Callers use a saver directly (`ApplicationOverviewSaver().save(key, payload)`) and read rows through `db.get_row` / `db.list_rows`. Do not create `registry.py` or `tools.py`.

Then run the gate one last time and stop. Do **not** create entities, documents or savers here.

## Part 2: one shared model

1. Confirm the class is infrastructure or an item type used by **both** entities and documents. If it belongs to one side only, stop and say so.
2. `python .claude/scripts/resolve_target.py shared-model <ClassName>`. Exit 1 means stop and report `errors`. If `docfactory/models/doc_factory_model.py` or `doc_field.py` is missing, stop: `Gaps: run /create-shared-model skeleton first`.
3. Get the fields from the request and `CLAUDE.md`. If unclear, stop and return questions under `Gaps`; do not invent fields.
4. Write `<scratchpad>/<ClassName>.spec.json` following `docfactory-field-spec`.
5. `python .claude/scripts/scaffold_model.py shared-model <spec.json> --dry-run`, fix rejections, then run it without `--dry-run`. Shared models get no saver.
6. Quality gate (`docfactory-quality-gate`).
