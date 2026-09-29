# docFactory (Pydantic approach)

Keeps application documentation (currently the Overview and the SMTD) up to date from structured knowledge. Knowledge is held as **Pydantic-validated JSON objects in SQLite**; documents are **composed Pydantic objects** rendered to Markdown by deterministic code.

## Status

- **Phase 1 (current): fully deterministic.** Seed data -> hard-coded tool calls -> validated facts in SQLite -> composed document objects -> `.md` files. No LLM, no RAG, no approval gate, no provenance, no history. Everything is unit-testable.
- **Phase 2 (later, not designed yet): RAG + LLM.** Retrieval over the original documents, an LLM constructs the same tool calls, validation errors become feedback that tells it what to look for next. Provenance, evidence quotes, history and the approval gate are added then (see "Phase 2 roadmap").

Nothing described here exists until it appears in the repo. If something is unclear, ask the user before coding.

## Principles

1. **Single Responsibility (strongest rule).** Every class lives in its own file, and every module has one reason to change.
   - Every Pydantic class, including small nested item classes, is in its own file. Entity models go in `docfactory/entitymodels/facts/` (facts, which have a saver) or `docfactory/entitymodels/items/` (nested items and enums, no saver), document models in `docfactory/documentmodels/`, common and shared models in `docfactory/models/`.
   - Every entity saver is in its own file under `docfactory/entitysaver/`; every document saver is in its own file under `docfactory/documentsaver/<role>/`.
   - The file is named after its class in snake_case (`ApplicationOverview` -> `application_overview.py`, `ApplicationOverviewSaver` -> `application_overview_saver.py`). A module never defines two classes.
   - A class does one thing: a model describes and validates data, a saver stores it, the renderer renders it, the database module talks to SQLite. None of them does another's job.
   - A test enforces the file and naming rule (see "Tests").
2. **The facts in `KnowledgeFacts` are the source of truth.** Generated documents are views of them, never the other way round.
3. **Only valid data is stored.** Every write goes through a Pydantic model. Invalid input is rejected with a structured error and nothing is written.
4. **Models are the contract.** Every model and field has a description written for an LLM: what it means, what a good value looks like, what to ask when it is missing. The same model is the validator, the LLM's tool schema and the documentation.
5. **Deterministic code does all the work that can be deterministic:** validation, canonical JSON, hashing, SQL, completeness, composition, rendering. An LLM (Phase 2) only does judgment work: find the information and construct the call.
6. **Never invent values.** A default is a placeholder, not knowledge. Completeness counts only what was actually answered. Do not fill fields to raise a score.
7. **Errors are feedback.** A rejected call returns errors precise enough for a caller (test or LLM) to fix the payload or go and find the missing information.
8. **Only tools write to the database.** No hand-edited rows, no hand-edited generated documents.

## Data flow

```
seed data (Phase 1)  ----\
                          >-- XSaver.save() --validate--> KnowledgeFacts (JSON, hash, completeness, version)
LLM over RAG (Phase 2) --/                                              |
                                                                        v
              document models (composed Pydantic) --build--> document objects --> DocumentOutputs
                                                                        |
                                                                        v
                                                       render (deterministic) --> output/<app>/<doc>.md
```

## Models

One Pydantic v2 model per file, in three folders. `models/` is flat; `entitymodels/` has two sub-folders, `facts/` and `items/`; `documentmodels/` has one sub-folder per role (below):

| Folder | Holds | Examples |
|---|---|---|
| `docfactory/entitymodels/facts/` | **EntityModels that are knowledge facts**: every entity model that has a saver in `entitysaver/` | `ApplicationOverview`, `Architecture`, `Environments`, `FunctionalRequirements`, `NonFunctionalRequirements`, `Slo`, `Kpis` |
| `docfactory/entitymodels/items/` | **EntityModels that are nested items and enums**: every entity model with no saver | `Environment`, `Requirement`, `Alert`, `Component`, `RequirementPriority` |
| `docfactory/documentmodels/<role>/` | **DocumentModels**: output documents, their sections and their parts, in three role sub-folders (below) | `OverviewDocument`, `DocumentControl`, `RevisionHistory`, `ApplicationSummarySection`, `RevisionEntry` |
| `docfactory/models/` | **Machinery models**: reusable building blocks of the system itself, independent of any application knowledge. They make the code work; they hold no information about an application | the base model, `doc_field`, `NotApplicable`, `SaveAction`, `SaveResult`, `SaveError` |

**The dividing line:** `models/` is for machinery (how the system validates, saves and reports). Anything that describes information about an application or its environment, including a small nested item type such as `Alert`, `Component`, `Environment` or `Integration`, is an entity model and lives in `entitymodels/` (`facts/` when it has a saver, else `items/`; nothing sits directly in `entitymodels/`), even when it is never saved on its own and even when a document section also uses it. Document models import entity models where they need them; the reverse never happens. `models/` never imports `entitymodels/` or `documentmodels/`.

**Document model roles.** Every file in `documentmodels/` (and every document saver in `documentsaver/`) lives in exactly one role sub-folder, picked by what the class depends on:

| Role folder | Holds | Fields bind to | May import from |
|---|---|---|---|
| `documents/` | A document body, composed of sections: one per document type (`OverviewDocument`, `SmtdDocument`) | `composed` sections | `entitybound/`, `shared/` |
| `shared/` | Reusable parts every document type uses, supplied by the caller: `DocumentControl`, `RevisionHistory`, `RevisionEntry`, and `MissingInfo` | `caller` | nothing in `documentmodels/` |
| `entitybound/` | A section in a specific format over entity facts: `ApplicationSummarySection`, `KpiSummarySection` | `Entity.field` | nothing in `documentmodels/` |

Nothing goes deeper than the role folder. A document saver mirrors its model's role (`documentsaver/shared/document_control_saver.py` saves `documentmodels/shared/document_control.py`); `entitybound/` has no savers because a section is stored inside its document body. `shared/` here means "shared across document types"; a type used by both entities and documents is an entity model.

- An entity is an **aggregate**: list-like content (requirements, environments, components, SLOs) is a list of typed item models inside one object.
- All models derive from one base model (`docfactory/models/`, its own file) that sets `extra="forbid"` (a hallucinated field is an error) and requires a description on every field (enforced by a test).
- **Mandatory fields are the absolutely necessary ones only** (what identifies the object or makes it meaningless). Everything else has a default where a default is legitimate (`None`, empty list, empty string). If no honest default exists, the field is mandatory.
- Field metadata beyond the type: `description` (meaning and what a good answer contains), `question` (asked when the field is missing; defaults to the description), whether `N/A` is a legal answer (`na_allowed`), and `scored` (default true).
- Two kinds of knowledge fact, distinguished only by scope in the key:
  - **Common** to all applications: `Shared.Kpis`, `Shared.Slo` (AppID NULL).
  - **Application-specific:** `ReadmeForge.ApplicationOverview`, `ReadmeForge.Architecture` (AppID = `ReadmeForge`).
- **Output-specific** content (document control, revision history) is not a knowledge fact. It belongs to one generated document and lives in `DocumentOutputs` (see "Documents").
- Models are Python code, versioned by git. There is no schema-version column in Phase 1.

## Database (SQLite, `db/docfactory.sqlite`)

Two tables with the same shape, plus completeness and version columns.

| Column (KnowledgeFacts) | Column (DocumentOutputs) | Meaning |
|---|---|---|
| `FactKey` (PK) | `DocumentKey` (PK) | Unique key: `<Scope>.<Name>[.<SubName>...]`. Scope is an application name or `Shared`. |
| `Value` | `Value` | The validated object as canonical JSON text (sorted keys, no extra whitespace, UTF-8) |
| `Hashcode` | `Hashcode` | SHA-256 hex of the canonical `Value` |
| `AppID` (nullable) | `AppID` (nullable) | The application; NULL means common/shared |
| `Completeness` | `Completeness` | 0-100 (REAL): how much of the object has been actually answered (see below) |
| `Version` | `Version` | Integer, starts at 1, incremented automatically by the base saver each time the stored value changes |

Rules enforced by code, not by convention:
- `AppID` is NULL exactly when the key scope is `Shared`; otherwise it equals the key's first segment, case-sensitive.
- The key must match one of the saver's own key patterns; the saver's model validates the value. (A registry that picks the saver from the key is Phase 2.)
- **The whole object is saved, and only when its hash differs.** Identical `Hashcode` = no-op (`UNCHANGED`): the row, its `Version` and its `Completeness` are untouched. A different hash replaces the row's `Value` and `Hashcode`, recomputes `Completeness` and sets `Version = Version + 1`. First write is `Version = 1`. There are no partial updates: a caller sends the complete object.
- `Version` counts changes to the current row only. Phase 1 keeps no history of old values and no provenance (Phase 2).
- **Multi-component applications:** each component has its own keys, `<App>.Components.<Component>.<Entity>`, e.g. `ReadmeForge.Components.api.Architecture`, `ReadmeForge.Components.worker.Environments`. `AppID` is still the application (`ReadmeForge`). The application-level keys (`ReadmeForge.Architecture`, `ReadmeForge.Environments`, ...) hold the high-level view of the whole application. Component keys reuse the same models as application keys. The component name is free text and is not validated.
- Key examples: `ReadmeForge.ApplicationOverview`, `ReadmeForge.Architecture`, `Shared.Kpis`; documents: `ReadmeForge.Outputs.SMTD`, `ReadmeForge.Outputs.SMTD.DocumentControl`, `ReadmeForge.Outputs.SMTD.RevisionHistory`.

### Completeness

A field is **answered** when its value differs from its default, or it holds a legal `N/A`. A field still equal to its default is **not yet answered**, even if the caller passed the default explicitly. `N/A` counts as answered: the question was considered and the answer is "not applicable". Mandatory fields are answered by definition (validation guarantees them).

- `Completeness = answered fields / total fields * 100`. Every field has the same weight.
- **N/A** is a typed value, `NotApplicable(reason)`, with a non-empty reason. It is accepted only on fields declared `na_allowed`; anywhere else it is a validation error.
- **All list items and nested values are typed Pydantic models.** No `dict`, `Any` or `list[dict]` in any model (a test enforces this). Scoring is **item-level and recursive**, counting leaf fields:
  - A nested single model is replaced by its own fields. If it is absent (still its default) it counts as one unanswered field.
  - A list of models is replaced by the fields of every item, so each item's unanswered fields lower the score. An empty list counts as one unanswered field.
  - A `NotApplicable` value on a list or nested-model field counts as one answered field (nothing further to score).
  - The number of items is not fixed by the schema, so total fields grows with the data. A list with one complete item scores 100% for that list; completeness measures how filled-in what is present is. Missing whole items are found by the document's expectations, not by this score.
- For a document object, "fields" are the document model's fields (a field filled from a fact is answered, a missing fact is not).
- Fields marked `scored=False` (e.g. purely technical ones) are excluded from both counts.

## Savers

Plain Python, no framework. Everything is deterministic and callable from tests and seed scripts. Phase 1 calls a saver directly (`ApplicationOverviewSaver().save(key, payload)`); there is no registry and no generic dispatcher (both Phase 2).

- **`BaseSaver`** (`docfactory/base_saver.py`, generic over the model) owns all shared behaviour, so concrete savers contain no logic of their own:
  1. check the key against the saver's own `key_patterns`; derive `AppID` (NULL for `Shared`)
  2. validate the payload with the Pydantic model
  3. canonical JSON -> SHA-256 hash
  4. read the existing row: same hash -> `UNCHANGED`; no row -> `CREATED`, `Version = 1`; different hash -> `UPDATED`, `Version + 1`
  5. compute completeness
  6. write in one transaction (never on `REJECTED`)
- **Entity savers** (`docfactory/entitysaver/`, one file each, e.g. `application_overview_saver.py`) inherit `BaseSaver`, declare only the model and key pattern, and write `KnowledgeFacts`.
- **Document savers** (`docfactory/documentsaver/documents/` and `docfactory/documentsaver/shared/`, one file each, e.g. `document_control_saver.py`, `revision_history_saver.py`) inherit `BaseSaver`, declare only the model and key pattern, and write `DocumentOutputs` (body, `.DocumentControl`, `.RevisionHistory`).
- Return value is always a `SaveResult` model, never an exception for bad input:

```
SaveResult { ok, key, action: CREATED|UPDATED|UNCHANGED|REJECTED, version, hashcode, completeness,
             errors: [ SaveError { path, message, error_type, received, expected, field_description, question } ] }
```

- On `REJECTED` nothing is written. Each error carries the Pydantic message plus the field's description and question, so the caller knows what to fix or what to find out.
- Read side (Phase 1): `db.get_row(table, key)` and `db.list_rows(table, app_id=None)` return stored rows. Typed `get_fact` / `list_facts` / `get_document` wrappers are Phase 2.

## Documents

- A document type (Overview, SMTD, ...) is a composed **DocumentModel**: it is made of section models, and each section is made of entity models or fields of them. Sections are reusable across document types (e.g. `DocumentControl` in every document). Each is its own file in the `docfactory/documentmodels/<role>/` folder for its role (see "Models").
- Each document field declares its **binding**: which fact key(s) supply it (for example `Architecture.environments`) and the same field metadata as entities (description, question, `na_allowed`).
- `build_document` is deterministic: it reads the app's facts and the shared facts, fills the document object, marks each field as content, `N/A - <reason>`, or missing, and computes completeness. It does not invent content.
- Missing fields produce the **MissingInfo** list (field, question, expected source), generated from the model metadata, not written by hand.
- **Every output document is three rows in `DocumentOutputs`**, each a validated Pydantic object with its own hash, completeness and version:
  - `ReadmeForge.Outputs.SMTD` - the document body (all chapters), **without** document control and revision history. Built from the knowledge facts.
  - `ReadmeForge.Outputs.SMTD.DocumentControl` - document id, title, version, status, owner, approvers, dates. Supplied by the caller (seed data in Phase 1), not derived from knowledge facts.
  - `ReadmeForge.Outputs.SMTD.RevisionHistory` - the list of revisions (version, date, author, change summary). Supplied by the caller.
  All three use the same `<App>.Outputs.<DocType>` prefix, so a document's parts are found by prefix. `DocumentControl` and `RevisionHistory` are reused by every document type.
- `render_markdown` assembles the final `.md` from the three rows (default order: document control, revision history, body). Same rows in, same bytes out. The `.md` file under `output/<app>/` is a view and never truth. The body's completeness is computed over the body only; document control and revision history score their own.

## The `pydantic-developer-agent` (first deliverable of Phase 1)

Before any model or saver is written, we create a specialized agent, `.claude/agents/pydantic-developer-agent.md`, with reusable prompts, built strongly around the principles above. All models and savers are then produced through it, so they come out uniform.

- **The agent** knows and enforces: single responsibility (one class per file, file name = snake_case of the class, correct folder), the base model, descriptions and questions on every field, honest defaults and minimal mandatory fields, typed lists and no `dict`/`Any`, `NotApplicable` only where `na_allowed`, scoring rules, and that savers inherit `BaseSaver` and contain no logic. It writes a test with every class it creates and runs the suite before it reports done.
- **Entry skills** (in `.claude/skills/`, invoked as `/name`), one per repeatable task, each pinning the agent and model (`context: fork`, `agent: pydantic-developer-agent`, `model: sonnet`) and defining the exact step-by-step procedure: `create-shared-model` (base classes and package skeleton, or one shared model), `create-entity-model` and `create-document-model` (each also creates the saver where one belongs), `add-field`, `review-models`. Two reference skills (`docfactory-field-spec`, `docfactory-quality-gate`) are preloaded into the agent. Skills cannot be `.claude/commands/` files: only skills support `agent` and `context: fork`.
- **Deterministic scripts** (`.claude/scripts/`, tested in `tests/scripts/`): the agent supplies judgment as a JSON spec; scripts resolve names and paths, generate models, savers and their tests, add fields, check structure and run the quality gate. Conventions the generated code relies on (base model `DocFactoryModel`, field helper `doc_field`, `BaseSaver`, key-pattern placeholders) are in `.claude/scripts/conventions.py`.
- The agent never edits the database or generated documents by hand, and never invents field content.

## Phase 1 build order

1. **Create the `pydantic-developer-agent` and its prompts** (above).
2. Package skeleton via the agent: base model, `NotApplicable`, `SaveError`, `SaveResult`, `BaseSaver`, canonical JSON + hash, completeness, database setup.
3. **One or two entities end to end**, with tests, before adding more. Proposed: `ApplicationOverview` (app-specific) and `Kpis` (shared, AppID NULL).
4. One small document type over those entities, with its `DocumentControl` and `RevisionHistory`, `build_document` and `render_markdown`, checked against a golden `.md` file.
5. Seed data as Python calling the save tools (hard-coded, no parsing of source documents).
6. Widen: more entities, and the SMTD (the document with the most fields). **Phase 1 scope is closed here:** two document types (Overview, SMTD) and one sample application (ReadmeForge). Further document types (SRS, BRD, standalone SOP) and further sample applications are out of scope.

### Tests (pytest, every test uses a temporary database)

- **Structure:** every module in `models/`, `entitymodels/<facts|items>/`, `documentmodels/<role>/`, `entitysaver/` and `documentsaver/<role>/` defines exactly one class, named after the file (snake_case); documents and savers sit in a role folder, a class in `entitymodels/facts/` has a matching saver and one in `entitymodels/items/` has none (nothing sits directly in `entitymodels/`), a document saver sits in the same role as its model, and `documentmodels/` roles only import as allowed by the role table; every Pydantic class is under `models/`, `entitymodels/` or `documentmodels/`, and entity and document models are in the right one; every field of every registered model has a description; no model contains `dict`, `Any` or untyped list items.
- Valid payload -> `CREATED`, row has canonical JSON, correct SHA-256, correct AppID, completeness, `Version = 1`.
- Same payload again -> `UNCHANGED`, `Version` and row untouched; changed payload -> `UPDATED`, new hash, `Version = 2`; changing back is a new change (`Version = 3`), not a revert.
- A new saver subclass gets versioning and hash-skipping with no code of its own.
- Component keys (`ReadmeForge.Components.api.Architecture`) store AppID `ReadmeForge` and validate with the same model as `ReadmeForge.Architecture`.
- Key order in the payload does not change the hash.
- Missing mandatory field, wrong type, bad enum, extra field -> `REJECTED`, nothing written, errors contain path, description and question.
- `Shared.*` key stores NULL AppID; an app key with a mismatching AppID is rejected; a key matching none of the saver's key patterns is rejected.
- Defaults do not count as answered (even when passed explicitly); a legal `NotApplicable(reason)` does; `N/A` on a field without `na_allowed`, or with an empty reason, is rejected; completeness = answered / total.
- Item-level scoring: an empty list is one unanswered field; a list of two items (one complete, one half-filled) scores over both items' fields; an absent nested model is one unanswered field, a present one is scored by its own fields; `NotApplicable` on a list is one answered field.
- Every JSON file under `samples/` validates against the model of its folder, and every sample folder has a model (`tests/test_samples.py`).
- Build + render of the sample document (body + `.DocumentControl` + `.RevisionHistory`) matches the golden file; rendering twice gives identical bytes; a missing fact yields `MISSING` and a MissingInfo question; rendering with a missing `.DocumentControl` row fails with a clear error rather than a blank section.

## Repo layout

```
.claude/agents/        pydantic-developer-agent.md, sample-generator-agent.md
.claude/skills/        Entry skills (create-shared-model, create-entity-model, create-document-model, add-field, review-models) and reference skills (docfactory-field-spec, docfactory-quality-gate)
.claude/scripts/       Deterministic scripts the skills call (scaffold, add field, check structure, gate)
docfactory/            Python package (pydantic v2 is the only runtime dependency)
  models/              Machinery models, one class per file: base model, doc_field, NotApplicable, SaveAction, SaveResult, SaveError
  entitymodels/        EntityModels, one class per file, in two sub-folders:
    facts/             the facts, each with a saver: ApplicationOverview, Architecture, Environments, Deployment, Monitoring, BackupRecovery, KnownErrors, Sop, Support, Slo, Kpis, FunctionalRequirements, NonFunctionalRequirements
    items/             nested item types and enums, no saver: Environment, Requirement, Alert, Component, RequirementPriority, ...
  documentmodels/      DocumentModels, one class per file, in role sub-folders:
    documents/         document bodies (OverviewDocument, SmtdDocument)
    shared/            caller-supplied parts reused by every document (DocumentControl, RevisionHistory, RevisionEntry, MissingInfo)
    entitybound/       one section per entity fact (ApplicationSummarySection, ArchitectureSection, KpiSummarySection, ...)
  entitysaver/         One entity saver per file (write KnowledgeFacts)
  documentsaver/       One document saver per file (write DocumentOutputs), mirroring the model's role
    documents/         savers of document bodies
    shared/            savers of DocumentControl, RevisionHistory
  base_saver.py        BaseSaver
  db.py                Connection, schema creation, upsert, reads
  canonical.py         canonical JSON + SHA-256
  completeness.py      completeness scoring
  build.py render.py   build_document, render_markdown, MissingInfo
samples/<entity>/      Example JSON payloads per entity (ReadmeForge, plus shared Kpis and Slo)
seed/                  Hard-coded seed scripts for the ReadmeForge sample (Phase 1): overview, SMTD, requirements
tests/                 pytest; tests/golden/ holds the golden .md files, tests/scripts/ tests the .claude/scripts
db/docfactory.sqlite   The database (gitignored)
output/<app>/          Rendered documents and MissingInfo files
```

Env `DOCFACTORY_DB` points the code at another database file (tests use a temporary one).

## Phase 2 roadmap (not designed; do not implement)

- A **registry** that maps key patterns to models and savers (built by discovering the `BaseSaver` subclasses in `entitysaver/` and `documentsaver/`), generic `save_fact(key, payload)` / `save_document(key, payload)` dispatchers and typed read wrappers (`get_fact`, `list_facts`, `get_document`) on top of it, and per-entity `save_<entity>` wrappers as LLM tool definitions.
- Ingest original documents, chunk and index them for retrieval (RAG).
- An LLM agent reads the model schemas, retrieves relevant chunks and calls the same `save_*` tools; `REJECTED` results and low completeness drive follow-up retrieval or a question to a human.
- Add provenance and evidence quotes (every fact traceable to a source passage), history of replaced values, and conflict handling when new information contradicts a stored value.
- Add the human approval gate: agents propose, humans approve, tools apply.
- Answers to MissingInfo questions re-enter as documents.

## Working rules

- Read this file first. When something is unclear, ask the user.
- One class per file, in the right folder (Principle 1). Create models and savers through the `pydantic-developer-agent`.
- Write to the database only through the tools. Never edit generated documents by hand; change the models or documents and regenerate.
- Changing a model changes stored data's meaning: say so and update the tests and golden files in the same change.
- Descriptions on models and fields are part of the product: write them for an LLM reader (meaning, example of a good value, what to ask if missing).
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes.
- Keep the repo in git so data-shape changes are diffable.
