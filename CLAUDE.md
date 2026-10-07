# docFactory (Pydantic approach)

Keeps application documentation (currently the Overview and the SMTD) up to date from structured knowledge. Knowledge is held as **Pydantic-validated JSON objects in SQLite**; documents are **composed Pydantic objects** rendered to Markdown by deterministic code.

## Status

- **Phase 1 (DONE, closed 2026-10-03): fully deterministic.** Seed data -> hard-coded tool calls -> validated facts in SQLite -> composed document objects -> `.md` files. No LLM, no RAG, no approval gate, no provenance, no history. Everything is unit-testable.
- **Phase 2 (DONE, redesigned and closed 2026-10-03): Ingest.** Original files (text, PDF, Word, HTML, ...) arrive in `incoming/`, move to `staging/`, are chunked deterministically from the raw file, tagged with entities against an ontology (rules first, a small LLM fallback for what the rules cannot tag or place), and moved into `DocStore/<scope>/`; the `DocStore`, `DocStoreHistory`, `DocChunks` and `DocChunkTags` tables track them (see "Phase 2: Ingest"). Verified on a real 50-page SRS and live against the test corpus (`tests/corpus/`).
- **Phase 3 (DONE, redesigned and closed 2026-10-04): Extract knowledge (OKF).** **3a** is the deterministic OKF layer (columns, history table, typed reads; no LLM): OKF v0.2 metadata lives only in `KnowledgeFacts` columns, and the content of every fact is the validated JSON in `Value` (the OKF markdown files under `bundles/` were removed on 2026-10-07, see "OKF stays in the table"). **3b** (redesigned 2026-10-04) extracts on top of Phase 2's tagged chunks: per entity tagged in a `DocStore` file, its chunks go in small batches, one fresh single-tool LLM call per batch returns a partial object, and code checks, merges (batches, then every contributing file via `FactContributions`) and saves through the entity saver. The first 3b build (one agent, 18 tools, whole document) failed on a real 50-page SRS and was removed. Verified live on that SRS (all 172 non-empty FR and 162 NFR identifiers) and on the corpus SRS and its revision (see "Phase 3: Extract knowledge (OKF)"). `README.md` explains the process and lists the commands.
- **Phase 4 (PENDING: rework, next; a first build exists, see "Phase 4: Generate"): Generate.** Each fact's OKF metadata and JSON value are indexed in a SQLite+numpy vector index, RAG finds the relevant facts, a document-generator agent reads their JSON in full and calls the document savers; rendering stays deterministic. Verified live only on the ReadmeForge Overview; to be reworked after Phase 3 (SRS as the standard template, MissingInfo when incomplete, no silent stop on large payloads, an embedding provider without local models).
- **Phase 5 (PENDING, planned in outline): Human in the loop.** The approval gate as a workflow (agents propose, humans approve, tools apply), built on LangGraph checkpointing and interrupts.
- **Phase 6 (PENDING, planned in outline): Automate.** A watcher for `incoming/`, automatic triggering of the agents and the end-to-end workflow.
- **Triggers are manual until Phase 6:** files are moved into `incoming/` and the user runs each agent by hand.

Nothing described here exists until it appears in the repo. If something is unclear, ask the user before coding.

## Principles

1. **Single Responsibility (strongest rule).** Every class lives in its own file, and every module has one reason to change.
   - Every Pydantic class, including small nested item classes, is in its own file. Entity models go in `docfactory/entitymodels/facts/` (facts, which have a saver) or `docfactory/entitymodels/items/` (nested items and enums, no saver), document models in `docfactory/documentmodels/`, common and shared models in `docfactory/models/`.
   - Every entity saver is in its own file under `docfactory/entitysaver/`; every document saver is in its own file under `docfactory/documentsaver/<role>/`.
   - The file is named after its class in snake_case (`ApplicationOverview` -> `application_overview.py`, `ApplicationOverviewSaver` -> `application_overview_saver.py`). A module never defines two classes.
   - A class does one thing: a model describes and validates data, a saver stores it, the renderer renders it, the database module talks to SQLite. None of them does another's job.
   - A test enforces the file and naming rule (see "Tests").
2. **The facts in `KnowledgeFacts` are the source of truth.** Generated documents are views of them, never the other way round. `.md` files under `output/` are views too (written for visibility), never edited by hand. The content of a fact is its validated JSON (`Value`); OKF is only the metadata in its row.
3. **Only valid data is stored.** Every write goes through a Pydantic model. Invalid input is rejected with a structured error and nothing is written.
4. **Models are the contract.** Every model and field has a description written for an LLM: what it means, what a good value looks like, what to ask when it is missing. The same model is the validator, the LLM's tool schema and the documentation.
5. **Deterministic code does all the work that can be deterministic:** validation, canonical JSON, hashing, SQL, completeness, composition, rendering. An LLM (Phases 2-4) only does judgment work: classify an incoming file, find the information and construct the call. Moving files, hashing, DB rows, frontmatter, indexing and rendering stay deterministic.
6. **Never invent values.** A default is a placeholder, not knowledge. Completeness counts only what was actually answered. Do not fill fields to raise a score.
7. **Errors are feedback.** A rejected call returns errors precise enough for a caller (test or LLM) to fix the payload or go and find the missing information.
8. **Only tools write to the database.** No hand-edited rows, no hand-edited generated documents.
9. **The tool layer is plain in-process Python function tools over the savers.** The tools an agent calls are ordinary Python functions that wrap the entity savers, the document savers and the read functions, collected in an in-process registry. No MCP server, no framework-specific tool classes. The tool schema is derived from the Pydantic models (Principle 4). Agent loops and any orchestration framework (LangGraph in Phase 5) only call these functions; they never contain business logic, so the tool layer is testable without an LLM and survives a change of runtime.
10. **Least privilege for agents.** Every agent is given only the tools it needs to do its task, nothing more. Tools are grouped in **tool packages**, one package per agent (ingestion, extraction, generator), and an agent can reach only the tools of its own package. File operations are deterministic code that no agent controls; no agent gets a shell, a general file system or database access. A tool needed by two agents is listed in both packages explicitly. A test enforces each package's exact tool list, so a tool cannot be added to an agent unnoticed.

## Data flow

```
seed data (Phase 1)  ----------------\
                                      >-- XSaver.save() --validate--> KnowledgeFacts (Value = entity JSON, hash, completeness, version,
extraction (Phase 3): merged ------/                                  OKF metadata columns + YmlFrontmatter, trust, lifecycle)
FactContributions, one per file                                                         |
        ^ one small call per batch of an entity's tagged chunks                         v
incoming/ -> staging/ -> chunk + tag (ontology rules, LLM fallback) (Phase 2) -> DocStore/ (+ DocStore, DocChunks, DocChunkTags)   vector index of metadata + JSON (Phase 4)
                                                                                        |
                                              DocumentGeneratorAgent <-- RAG + get_fact (the JSON value)
                                                                        |
                                              document savers --validate--> DocumentOutputs
                                                                        |
              document models (composed Pydantic) --build--> document objects (Phase 1: build_document from facts)
                                                                        v
                                                       render (deterministic) --> output/<app>/<doc>.md
```

In Phase 4 the generator agent supplies the document JSON through the document savers; `build_document` / `render_markdown` remain the deterministic Phase 1 path and are not replaced.

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
| `documents/` | A document body, composed of sections: one per document type (`OverviewDocument`, `SmtdDocument`, `SrsDocument`, `SopDocument`) | `composed` sections | `entitybound/`, `shared/` |
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

Two tables with the same shape, plus completeness and version columns. `KnowledgeFacts` additionally has the OKF columns (Phase 3, see "Phase 3: Extract knowledge (OKF)"); `KnowledgeFactsHistory` and `KnowledgeFactSources` (a derived index of each fact's `sources`, written by the saver, used by `list_facts_by_source`) support it. `FactContributions` (Phase 3 redesign) holds what each `DocStore` file contributed to an extracted fact; the fact is their merge.

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
- The key must match one of the saver's own key patterns; the saver's model validates the value. (The key pattern -> saver resolution in the registry is added in Phase 3; the registry itself is built in Phase 2, see "Tool layer".)
- **The whole object is saved, and only when its hash differs.** Identical `Hashcode` = no-op (`UNCHANGED`): the row's `Value`, `Hashcode`, `Version` and `Completeness` are untouched. (For a knowledge fact saved with `meta`, only the OKF metadata columns and `YmlFrontmatter` are refreshed in place, still without a version bump; see Phase 3.) A different hash replaces the row's `Value` and `Hashcode`, recomputes `Completeness` and sets `Version = Version + 1`. First write is `Version = 1`. There are no partial updates: a caller sends the complete object.
- `Version` counts changes to the current row only. Phase 1 keeps no history of old values and no provenance (provenance arrives in Phase 3 through OKF `sources` and trust fields).
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

Plain Python, no framework. Everything is deterministic and callable from tests and seed scripts. Phase 1 calls a saver directly (`ApplicationOverviewSaver().save(key, payload)`); the Phase 2 registry holds only the ingestion tools, and the generic dispatcher arrives in Phase 3, see "Tool layer".

- **`BaseSaver`** (`docfactory/base_saver.py`, generic over the model) owns all shared behaviour, so concrete savers contain no logic of their own:
  1. check the key against the saver's own `key_patterns`; derive `AppID` (NULL for `Shared`)
  2. validate the payload with the Pydantic model
  3. canonical JSON -> SHA-256 hash
  4. read the existing row: same hash -> `UNCHANGED`; no row -> `CREATED`, `Version = 1`; different hash -> `UPDATED`, `Version + 1`
  5. compute completeness
  6. write in one transaction (never on `REJECTED`); entity savers also write the OKF columns, a `KnowledgeFactsHistory` row on `UPDATED` and the source index (`docfactory/fact_writer.py`)
- **Entity savers** (`docfactory/entitysaver/`, one file each, e.g. `application_overview_saver.py`) inherit `BaseSaver`, declare only the model and key pattern, and write `KnowledgeFacts`.
- **Document savers** (`docfactory/documentsaver/documents/` and `docfactory/documentsaver/shared/`, one file each, e.g. `document_control_saver.py`, `revision_history_saver.py`) inherit `BaseSaver`, declare only the model and key pattern, and write `DocumentOutputs` (body, `.DocumentControl`, `.RevisionHistory`).
- Return value is always a `SaveResult` model, never an exception for bad input:

```
SaveResult { ok, key, action: CREATED|UPDATED|UNCHANGED|REJECTED, version, hashcode, completeness,
             errors: [ SaveError { path, message, error_type, received, expected, field_description, question } ] }
```

- On `REJECTED` nothing is written. Each error carries the Pydantic message plus the field's description and question, so the caller knows what to fix or what to find out.
- Read side (Phase 1): `db.get_row(table, key)` and `db.list_rows(table, app_id=None)` return stored rows. Typed `get_fact` / `list_facts` / `list_facts_by_source` (returning `FactRecord`) are in `docfactory/facts.py` (Phase 3a); `get_document` / `list_documents` (returning `DocumentRecord`) are in `docfactory/documents.py` (Phase 4a).

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

## The `docfactory-pydantic-developer-agent` (first deliverable of Phase 1)

Before any model or saver is written, we create a specialized agent, `.claude/agents/docfactory-pydantic-developer-agent.md`, with reusable prompts, built strongly around the principles above. All models and savers are then produced through it, so they come out uniform.

- **The agent** knows and enforces: single responsibility (one class per file, file name = snake_case of the class, correct folder), the base model, descriptions and questions on every field, honest defaults and minimal mandatory fields, typed lists and no `dict`/`Any`, `NotApplicable` only where `na_allowed`, scoring rules, and that savers inherit `BaseSaver` and contain no logic. It writes a test with every class it creates and runs the suite before it reports done.
- **Entry skills** (in `.claude/skills/`, invoked as `/docfactory-<task>`; **every skill and custom agent in this project is named with the `docfactory-` prefix** so it is easy to identify, enforced by a test), one per repeatable task, each pinning the agent and model (`context: fork`, `agent: docfactory-pydantic-developer-agent`, `model: sonnet`) and defining the exact step-by-step procedure: `docfactory-create-shared-model` (base classes and package skeleton, or one shared model), `docfactory-create-entity-model` and `docfactory-create-document-model` (each also creates the saver where one belongs), `docfactory-add-field`, `docfactory-review-models`. Two reference skills (`docfactory-field-spec`, `docfactory-quality-gate`) are preloaded into the agent. Skills cannot be `.claude/commands/` files: only skills support `agent` and `context: fork`.
- **Deterministic scripts** (`.claude/scripts/`, tested in `tests/scripts/`): the agent supplies judgment as a JSON spec; scripts resolve names and paths, generate models, savers and their tests, add fields, check structure and run the quality gate. Conventions the generated code relies on (base model `DocFactoryModel`, field helper `doc_field`, `BaseSaver`, key-pattern placeholders) are in `.claude/scripts/conventions.py`.
- The agent never edits the database or generated documents by hand, and never invents field content.

## Phase 1 build order

1. **Create the `docfactory-pydantic-developer-agent` and its prompts** (above).
2. Package skeleton via the agent: base model, `NotApplicable`, `SaveError`, `SaveResult`, `BaseSaver`, canonical JSON + hash, completeness, database setup.
3. **One or two entities end to end**, with tests, before adding more. Proposed: `ApplicationOverview` (app-specific) and `Kpis` (shared, AppID NULL).
4. One small document type over those entities, with its `DocumentControl` and `RevisionHistory`, `build_document` and `render_markdown`, checked against a golden `.md` file.
5. Seed data as Python calling the save tools (hard-coded, no parsing of source documents).
6. Widen: more entities, and the SMTD (the document with the most fields). 7. SRS and SOP document types over the requirements, monitoring, support and SOP facts, with ReadmeForge samples (SOP: Datadog-monitored production, five alert runbooks). **Phase 1 scope is closed here:** four document types (Overview, SMTD, SRS, SOP) and one sample application (ReadmeForge). Further document types (BRD, ...) and further sample applications are out of scope.

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
- Every JSON file under `samples/json/` validates against the model of its folder, and every sample folder has a model (`tests/test_samples.py`).
- Build + render of the sample document (body + `.DocumentControl` + `.RevisionHistory`) matches the golden file; rendering twice gives identical bytes; a missing fact yields `MISSING` and a MissingInfo question; rendering with a missing `.DocumentControl` row fails with a clear error rather than a blank section.

## Repo layout

```
.claude/agents/        docfactory-pydantic-developer-agent.md, docfactory-sample-generator-agent.md
.claude/skills/        Entry skills (docfactory-create-shared-model, docfactory-create-entity-model, docfactory-create-document-model, docfactory-add-field, docfactory-review-models) and reference skills (docfactory-field-spec, docfactory-quality-gate)
.claude/scripts/       Deterministic scripts the skills call (scaffold, add field, check structure, gate)
docfactory/            Python package (pydantic v2 is the only runtime dependency)
  models/              Machinery models, one class per file: base model, doc_field, NotApplicable, SaveAction, SaveResult, SaveError
  entitymodels/        EntityModels, one class per file, in two sub-folders:
    facts/             the facts, each with a saver: ApplicationOverview, Architecture, Environments, Deployment, Monitoring, BackupRecovery, KnownErrors, Sop, Support, Slo, Kpis, FunctionalRequirements, NonFunctionalRequirements
    items/             nested item types and enums, no saver: Environment, Requirement, Alert, Component, RequirementPriority, ...
  documentmodels/      DocumentModels, one class per file, in role sub-folders:
    documents/         document bodies (OverviewDocument, SmtdDocument, SrsDocument, SopDocument)
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
samples/json/<entity>/ Example JSON payloads per entity (ReadmeForge, plus shared Kpis and Slo)
seed/                  Hard-coded seed scripts for the ReadmeForge sample (Phase 1): overview, SMTD, requirements, SRS and SOP
tests/                 pytest; tests/golden/ holds the golden .md files, tests/scripts/ tests the .claude/scripts
db/docfactory.sqlite   The database (gitignored)
output/<app>/          Rendered documents and MissingInfo files
docfactory/ingest/     Phase 2: the deterministic pipeline (pipeline.py: stage, lookup, commit, report), chunking.py + chunkers/ (pdf, word, html, text), tagging.py, scope_rules.py, chunk_rebuild, docstore_reads, paths, file_hash, target_rules. Function modules, no LLM
docfactory/ontology/   Phase 2: signals.json (tagging signals per entity), signals.py (validated load), ontology_render.py (docs/ontology.md and the compact LLM summary)
docfactory/tools/      Phase 2: Tool, ToolRegistry, ToolPackage (one class per file) and the two single-tool ingestion fallback packages (ingestion_tools.py). Phase 3 adds the extraction package; Phase 4 the generator package (generation_tools.py)
docfactory/agents/     Phase 2: ModelClient (abstract), OllamaModelClient (default), AnthropicModelClient (optional), FakeModelClient (tests), AgentLoop, IngestionFallback (tag and scope calls), model_client_factory, run_ingestion (manual trigger). Phase 5: LangGraph graph, checkpointer and approval nodes
docfactory/env_file.py Loads .env into the environment (shell variables win); used only by entry points and the live test
incoming/              Phase 2: drop zone for new original files (gitignored runtime data)
staging/               Phase 2: files being ingested, and files waiting for a human decision (gitignored runtime data)
DocStore/<scope>/...   Phase 2: classified originals (gitignored runtime data); scope = application name, shared, general
docs/ontology.md       Phase 2: generated view of the ontology (entities, facts, tagging signals)
.claude/agents/        also docfactory-chunk-tagger-agent.md and docfactory-scope-agent.md (Phase 2 fallback prompts)
tests/corpus/          Phase 2: build_corpus.py, incoming/ (messy PDF/Word/HTML/text originals), revisions/ (a changed SRS), corpus_expectations.json; tests/live_support.py: the live tests' server check
.env / .env.example    Local LLM settings (.env is gitignored)
docs/okf/SPEC.md       Phase 3a: verbatim copy of the OKF v0.2 spec
README.md              The process end to end and every command to run (keep it in step with the entry points)
docfactory/clock.py    now_iso() (tests replace it)
docfactory/okf_frontmatter.py fact_writer.py facts.py   Phase 3a: deterministic frontmatter rendering (the YmlFrontmatter column), fact storing with the OKF columns (called by BaseSaver), typed reads
seed/seed_meta.py      SEED_META: the FactMeta (generated_by `seed`) every seeded fact is saved with
docfactory/saver_resolution.py  Phase 3b: entity_saver_classes(), entity_saver_for(entity), saver_for_key(key) (exactly one saver per key), ordered_value (a stored value in model field order, for the vector index text)
docfactory/extract/   Phase 3b (redesign): function modules, no classes: batching (BATCH_CHARS, chunks_hash), fact_keys, partial_schema, model_shapes, grounding (identities in the text, duplicates, placeholders, ungrounded values, tidy identifiers), merge, priority_keywords (SHALL -> MUST, ...), missing_questions, extraction_pipeline (extract_file, format_reports)
docfactory/contributions.py  Phase 3b: typed access to FactContributions (FactContribution); EXISTING = '(existing)' for a value stored before any extraction
docfactory/tools/extraction_tools.py  Phase 3b: the single-tool extraction package (submit_extraction), built per call for one entity and one batch; schema_slim.py: inline_refs for tool schemas
docfactory/agents/    also Phase 3b: AgentLoop (the shared thin loop), EntityExtractor (one call per batch), run_extraction, prompt_file
docfactory/models/    also Phase 3b: ExtractionOutcome, FactContribution, EntityExtractionReport
.claude/agents/        also docfactory-entity-extractor-agent.md (Phase 3b runtime prompt, loaded by EntityExtractor)
docfactory/retrieval/ Phase 4a: Embedder (abstract), OllamaEmbedder, FakeEmbedder, embedder_factory, VectorIndex (abstract), SqliteVectorIndex (FactIndex table, cosine in numpy), index_rebuild (`python -m docfactory.retrieval.index_rebuild`)
docfactory/documents.py  Phase 4a: get_document / list_documents (typed reads of DocumentOutputs)
docfactory/models/    also Phase 4a: RetrievalHit, DocumentRecord
docfactory/saver_resolution.py  also Phase 4: document_saver_classes(), document_saver_for_key(key)
docfactory/tools/generation_tools.py  Phase 4b: the generator package
docfactory/agents/    also Phase 4b: GeneratorAgent, run_generation
.claude/agents/        also docfactory-document-generator-agent.md (Phase 4b runtime prompt, loaded by the loop)
--- planned, do not create until the phase starts ---
docfactory/agents/    Phase 5 adds the LangGraph graph, checkpointer and approval nodes
```

Env `DOCFACTORY_DB` points the code at another database file (tests use a temporary one). `DOCFACTORY_INCOMING`, `DOCFACTORY_STAGING` and `DOCFACTORY_DOCSTORE` relocate `incoming/`, `staging/` and `DocStore/` (tests use temporary folders). LLM settings (from `.env`): `DOCFACTORY_PROVIDER` (`ollama` default, or `anthropic`), `DOCFACTORY_MODEL`, `OLLAMA_HOST`, `OLLAMA_API_KEY`, `DOCFACTORY_NUM_CTX` (Ollama context window, default 16384; enough for extraction, whose one tool schema is at most ~1.5k tokens; the generator agent needs more, e.g. 65536). Embeddings (Phase 4): `DOCFACTORY_EMBED_MODEL` (default `nomic-embed-text`), `DOCFACTORY_EMBED_HOST` and `DOCFACTORY_EMBED_API_KEY`; Ollama Cloud serves no embedding models, so point the embedder at a local Ollama (e.g. `http://localhost:11434`, model `mxbai-embed-large`); the chat key is never sent to the embed host.

## Phases 2-6 (outline agreed; not designed in detail; do not implement)

Pipeline: **Ingest (move to store) > Extract knowledge (OKF) > Retrieve (RAG over each fact's metadata and JSON, then the fact's JSON in full) > Generate documents (document savers, then deterministic rendering).** Phases 5 and 6 wrap this pipeline in a human approval gate and then automate it. Each phase is built, tested and closed before the next starts. All agents are run manually until Phase 6.

### Tool layer (decision, Principle 9)
- **Function tools:** every capability an agent may use is a plain Python function with typed arguments and a typed return (a `SaveResult` for writes). Write tools wrap one saver each (`save_<entity>`, `save_<document>`); read tools wrap `db` reads; the ingestion fallback tools only validate and hand back an answer (file moves are pipeline code, not tools). No MCP.
- **Registry and tool packages (Principle 10):** an in-process registry holds every function tool by name, each with a name, a description written for an LLM, and a schema derived from its argument and return models. A **tool package** is a named, fixed list of registry tools for one agent. An agent is constructed with exactly one package and the loop can only call tools in it; a call to any other tool is refused. The registry and the package are each one class in their own file (Principle 1) and contain no business logic.
- **Registry types are built as the need arises:** each phase adds only the tool types and packages its agent needs, not a general catalogue up front. Tool types so far: answer tools (ingestion fallback), saver tools (extraction, later document generation), read tools, retrieval tools.
- **Where and when it is added:**
  - **Phase 2 (the registry is built here):** the registry, the tool and tool-package types, and (after the redesign) two **single-tool fallback packages**: `ingestion-tagging` = [`submit_chunk_tags`] and `ingestion-scope` = [`submit_scope`]. Each fallback call gets exactly one of them. The tools validate the model's answer and hand it back; they write nothing and move nothing (the pipeline does). Tests pin both lists.
  - **Phase 3 (after the 2026-10-04 redesign):** a **single-tool extraction package** `extraction` = [`submit_extraction`], built per call for one entity and one batch of its chunks. The tool validates the partial object against the entity's partial model and hands it back; it writes nothing (the pipeline merges and calls the entity saver). The first build's 18-tool package (`save_fact`, `save_<entity>`, reads) was removed. Tests pin the list; key pattern -> saver resolution stays tested in `saver_resolution`.
  - **Phase 4:** add the **generator package**: the document savers (`save_document`, `get_document`) and the retrieval tool (RAG query), plus the read tools it needs (`get_fact` returns the JSON value). It contains no entity savers.
  - **Phase 5:** LangGraph nodes call the registry tools unchanged and respect the same packages.
- Agent loops (Phases 2-4) are thin: call the model, run the requested tool, return its result to the model, stop on `ok` or a retry cap. They are tested with a fake model.

### Decisions already made
- `KnowledgeFacts` remains the source of truth. Document savers write `DocumentOutputs`; every other saver writes `KnowledgeFacts`. There is **no separate `KnowledgeStore` table**: `KnowledgeFacts` is extended instead.
- LLMs only classify, extract and construct calls; everything else is deterministic (Principle 5). Validation errors (`REJECTED`) stay the feedback loop.
- Files in `DocStore/` are written only by tools. Nothing is hand-edited.
- Runtime dependencies beyond pydantic are added only in the phase that needs them: pdfplumber, python-docx and beautifulsoup4 in Phase 2 (the format-aware chunkers; markitdown was dropped in the redesign; the Ollama client uses only the standard library; `anthropic` is an optional extra), numpy (the vector index) in Phase 4, LangGraph in Phase 5. `reportlab` is dev-only (corpus generation and tests).

### Phase 2: Ingest (redesigned 2026-10-03)
Phase 2 is **ingestion, chunking and movement** only; extraction is Phase 3. The first design (an LLM agent with six file tools that read the whole document, classified it and stored a markitdown sidecar) was replaced after it proved expensive and unreliable on a real 50-page SRS: markitdown flattens PDF tables (an ID column, then a statement column), and the LLM read every page just to classify. The redesign does everything deterministically and calls the LLM only where the rules give no answer.

**Flow per file** (`docfactory/ingest/pipeline.py`, code orchestrates; four headline steps: stage + lookup, chunk, entity recognition, move):
1. **Stage:** `incoming/<name>` moves to `staging/` (env `DOCFACTORY_STAGING`). From here a failure leaves the file in staging; nothing is deleted except a verified SAME duplicate. Files left in staging are retried on every run.
2. **Lookup** in `DocStore` by file name and by hash across all scopes: same name and hash with the stored file present on disk with that hash = **SAME** (staged copy discarded); same name and hash but the stored file missing or altered = **REPAIRED** (put back, chunks rewritten, version unchanged); same content under another name = left in staging as a duplicate; same name in exactly one scope with another hash = **CHANGED** (scope inherited, version + 1); same name in several scopes = left in staging; otherwise **NEW**.
3. **Chunk the original** (`ingest/chunking.py`, readers in `ingest/chunkers/`): PDF with `pdfplumber` (body size from paragraph-length lines; headings are clearly larger lines, numbered ones get their level from the numbering; in a numbered document unnumbered large lines such as cover titles and diagram labels stay text; tables read row by row so an identifier stays with its statement, `FR-85. | The system SHALL ...`; table-of-contents lines, page numbers and running headers dropped; symbol-font bullets become '-'), Word with `python-docx` (heading styles, tables), HTML with `BeautifulSoup` (h1-h6, tables, nothing read twice), text/markdown (headings, numbering, markdown tables). A chunk is one section with its heading trail (`3. ... > 3.1. ... > 3.1.1. ...`), never splitting a section's element; a table header row is kept once per section; sections over 4000 chars split into parts; a leading title styled as a heading stays front matter; no headings = 1500-char parts. No text (scanned PDF) or an unsupported type = left in staging.
4. **Tag chunks with entities** (`ingest/tagging.py`) against the **ontology** (below): heading term in the chunk's own heading 4, in a parent heading 3 (inherited), identifier pattern 4, keywords 1 each up to 3; an entity tags at score >= 3 **and** with a strong signal (keywords alone never tag); the longest heading match wins ('non-functional requirements' is not 'functional requirements'); plurals match. A chunk may carry several entities. Chunks no entity reaches are **unmapped**.
5. **LLM fallback for unmapped chunks** (`agents/ingestion_fallback.py`): one call, fresh context, one tool `submit_chunk_tags`; it sees the compact ontology summary and only the unmapped chunks' headings and first 300 chars. Code validates the answer (closed entity list, only the asked chunks, every asked chunk answered) and feeds errors back; accepted tags keep origin `llm/<model>`. A failed or empty call leaves the chunks unmapped.
6. **Scope (NEW only)** (`ingest/scope_rules.py`): only shared entities tagged (Slo, Kpis) = `shared`; else the name from a document-control row (`Title | ...`) or the title line, with document-type wording removed ('Software Requirements Specification for', '(working draft 0.3)', 'on-call runbooks') and line-break hyphens mended; an existing folder matching ignoring case and punctuation is reused; the folder name replaces other characters with '-' (`AI-Driven-Job-Matching-Platform`). An unconfident scope goes to the **scope fallback**: one call, one tool `submit_scope` (application name, `shared`, `general` or null); null leaves the file in staging with both reasons.
7. **Move + commit:** `staging/<name>` -> `DocStore/<scope>/<name>`, then one transaction writes `DocStore` / `DocStoreHistory`, `DocChunks` and `DocChunkTags`. If the write fails the file goes back to staging and a replaced original is restored. On CHANGED the report names the entities whose chunks changed or disappeared (to re-extract).
8. **Report** per file: outcome, target, version, chunk count, entity -> chunk count (with how many by the LLM), unmapped chunks, changed entities, reason.

**Ontology:** `docfactory/ontology/signals.json` (edited by people) holds per entity the heading terms, identifier patterns and keywords, validated by `EntitySignals`; a test fails when an entity has no entry, an entry names an unknown entity or appears twice. `docs/ontology.md` is generated (`python -m docfactory.ontology.ontology_render`) from the entity models plus the signals; `ontology_summary()` is the compact form sent to the LLM.

**Tables:** `DocStore` (`FullPath` PK, `Hashcode`, `Version`, `Timestamp`) and `DocStoreHistory` (a row per change) as before; `DocChunks` (`FullPath`, `ChunkNo`, `Heading`, `PageFrom`, `PageTo`, `Text`, `TextHash`) and `DocChunkTags` (`FullPath`, `ChunkNo`, `Entity`, `Origin` = `rule` or `llm/<model>`, `Score`, `Evidence`). The entity map of a file is a query over `DocChunkTags`. Chunks and tags are derived data: `python -m docfactory.ingest.chunk_rebuild` re-chunks and re-tags (rules only) every stored original after the chunkers or signals change. No text sidecar is written; `docstore_reads.read_docstore_text` rebuilds a file's text from its chunks for the Phase 3 tools.

**As built and verified (2026-10-03):** models `DocChunk`, `ChunkTag`, `ChunkTagProposal`, `EntitySignals`, `IngestOutcome`, `IngestReport`. On the real SRS (50-page PDF): 76 chunks, 67 tagged by rules (FunctionalRequirements 25, NonFunctionalRequirements 29, ApplicationOverview 12, ...; 11 chunks carry two entities), 9 unmapped for the fallback, scope `AI-Driven-Job-Matching-Platform` from the Document Control title row. Live corpus test (`pytest -m live tests/test_live_ingestion.py`, `gemma4:31b` on Ollama Cloud): the fallback tagged the informal ReadmeForge SRS, put the standards PDF in `shared` via its Slo tags, refused a scope for personal notes; the duplicate PDF stayed in staging; the revision came in as CHANGED v2 naming the entities to re-extract. `AgentLoop` nudges once on an empty reply and then fails loudly (the silent stop seen in extraction and generation). Files are processed in case-insensitive name order on every OS. `python -m docfactory.agents.run_ingestion [--no-llm]`.

**Provider-neutral model interface (unchanged):** `ModelClient.complete(system, messages, tools)` over neutral machinery models; default provider Ollama (local, or Ollama Cloud with `OLLAMA_HOST=https://ollama.com` and `OLLAMA_API_KEY`), Anthropic optional; cut-off responses raise; connection and 5xx errors are retried; tested with `FakeModelClient`.

### Phase 3: Extract knowledge (OKF)
- **Extraction** turns the tagged chunks of a new or changed `DocStore` file into facts through the existing entity savers (since the 2026-10-04 redesign: small per-batch LLM calls, code merges and saves; see "Phase 3 redesign" below). No LLM writes the database directly.
- **`KnowledgeFacts` is made OKF v0.2 compliant** (spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md; a verbatim copy is in `docs/okf/SPEC.md`). New columns, all derived by the base saver, none hand-written:

| Column | Meaning |
|---|---|
| `FactType` | OKF `type`: the entity model name in words, e.g. `Application Overview` |
| `Title`, `Description` | OKF `title` and the one-sentence `description` |
| `Tags`, `Sources` | OKF `tags` and `sources[]`, each a JSON list |
| `YmlFrontmatter` | The same OKF metadata rendered as YAML text (derived from the columns above plus trust and lifecycle). `FactKey` is the id and `Value` is the content, the validated JSON document |
| `GeneratedBy`, `GeneratedAt` | Trust: OKF `generated {by, at}` |
| `Verified` | Trust: OKF `verified [{by, at}]`, stored as a JSON list; empty = unverified |
| `Status` | Lifecycle: `draft` \| `stable` \| `deprecated` (this is the doc status) |
| `StaleAfter` | Lifecycle & freshness: ISO 8601 instant; stale when now >= `StaleAfter` |

- **OKF stays in the table (user, 2026-10-07).** OKF describes a fact's metadata only; the content is the structured JSON defined by the entity model, validated by its saver. There are no knowledge files: the `bundles/` markdown files, their body renderer, `bundle_rebuild`, `okf_check`, the `FilePath` column and `read_okf_file` were removed because a second, markdown representation of the content bypassed the models (the generator read markdown instead of the JSON). `db.py` drops `FilePath` from an existing table. Rows saved before the typed columns existed get them on their next save with `meta` (re-run the seeds; re-extract with `--force`). The caller supplies the judgment fields (`title`, `description`, `tags`, `sources`) in `FactMeta`; since the redesign code derives all of them except `description`, which comes from the extraction call's one-sentence summary.
- **OKF v0.2 metadata:** `YmlFrontmatter` is parseable YAML with a non-empty `type`. Also used: `title`, `description`, `resource`, `tags`; `sources[]` (`resource` required, `id`, `title`, `last_modified`) pointing at the `DocStore` files the fact came from; `generated`, `verified` with the actor convention `<producer>/<version>` (agents), `human:<id>`, `process:<id>`; `status`; `stale_after`. Bundle files, links, `index.md` and `log.md` are not used.
- **Trust rule:** LLM output is always `Status = draft` with `generated.by` = agent and model. Only a human action adds `verified` with a `human:<id>` actor and promotes to `stable` (to be confirmed when Phase 3 is designed).
**Phase 3 design decisions (2026-10-03):**
- **Hash and Version cover `Value` only.** A re-extraction with the same `Value` but different metadata (new source, title, tags) is `UNCHANGED`: no version bump, but the metadata columns and `YmlFrontmatter` are refreshed in place.
- **`KnowledgeFactsHistory` table**, mirroring `DocStoreHistory`: `FactKey`, `Hashcode`, `Version`, `Timestamp`, `GeneratedBy`; PK (`FactKey`, `Version`). A row is added on every `UPDATED`. It records that a change happened and who made it, not the old value. `DocumentOutputs` is unchanged.
- **Caller-supplied judgment fields** travel in two machinery models in `models/`: `FactMeta` (`title`, `description`, `tags`, `sources`, `generated_by`) and `FactSource` (`resource`, `id`, `title`, `last_modified`). Everything else in the frontmatter is derived.
- **Re-extraction rule:** when a `DocStore` file is `CHANGED`, the user runs `run_extraction` on it by hand; only entities whose chunks changed are extracted (superseded by the redesign: the chunks hash per contribution decides, `list_facts_by_source` remains a read).
- **Conflicts:** until Phase 5 there is no approval and every LLM write is `draft`; `KnowledgeFactsHistory` is the audit trail. (The redesign replaced "last write wins" with the per-file contribution merge, conflicts reported.)
- **Trust:** `generated.by` = `okf-extraction-agent/<model>`; `verified` stays empty until Phase 5.
- **Migration:** `db.py` adds the new columns idempotently to an existing `KnowledgeFacts` table. Phase 1 seeds are re-run so every seeded fact gets its metadata (`generated.by` = `seed`, `Status` = `draft`).
- **Typed reads** (`get_fact`, `list_facts`, `list_facts_by_source`) arrive in 3a; `get_document` stays Phase 4.
- **3a as built (2026-10-03):** `FactMeta`, `FactSource`, `FactVerification`, `FactRecord`, `FactStatus` are in `models/`. `BaseSaver.save(key, payload, app_id=None, meta=None)`: `meta` is for entity savers only (a document save with `meta` is rejected, `meta_not_allowed`). A new or changed value is always `draft`, unverified, `generated.at` = now; without `meta` the actor is `docfactory/unspecified` and the title is the key. The frontmatter holds `type` (the model name in words), `title`, `description`, `tags`, `sources`, `generated`, `verified`, `status`, `stale_after` and the producer-defined `fact_key`, `version`, `completeness`.
- **Scope of 3a:** `docs/okf/SPEC.md`, schema and migration, `FactMeta` / `FactSource`, metadata writer called by the base saver (entity savers only), typed reads, tests, and updated golden files and docs. No LLM.
- **First 3b build (2026-10-03, removed 2026-10-04):** one `ExtractionAgent` with an 18-tool package (`list_docstore`, `read_docstore_text`, `get_fact`, `list_facts`, `save_fact`, 13 typed `save_<entity>`) read the whole document and saved whole facts. It worked on the small corpus SRS but on a real 50-page SRS wrote a 37-45 KB fact in one call and stopped silently. Lessons kept: the actor and source timestamps are set by code, never by the model; identifiers must come from the document (the model minted `FR-001` otherwise); bundle bodies follow the model's field order.

**Phase 3 redesign (decided and built 2026-10-04, closed the same day):**
- **Per entity, per batch, one tool.** For each entity tagged in a `DocStore` file (`DocChunkTags`), its chunks are packed in document order into batches of up to `BATCH_CHARS` = 3500 characters (chunks never split). Each batch is one fresh `AgentLoop` (`EntityExtractor`) with exactly one tool, `submit_extraction(values, summary)`, that sees only the entity's meaning and that batch. `values` is a **partial object**: the entity model with every top-level field optional (`partial_schema`, built with `create_model`, never declared by hand); list items keep their mandatory fields. Live, 6000-character batches dense with requirement rows overflowed one reply (empty replies); 3500 did not.
- **The tool checks, code decides.** `submit_extraction` refuses (with feedback the model acts on): invalid values (`SaveError`s with field description and question), placeholder text such as `N/A: not mentioned` (leave the field out), two items sharing an identifier, and item identifiers not found in the batch text. It strips trailing punctuation from identifiers (`FR-01.` -> `FR-01`). It writes nothing.
- **A failed batch of several chunks is split in half and retried**; a failed single chunk is reported and the contribution keeps no chunks hash, so the next run retries. One failed batch never stops the others.
- **Facts merge across documents (important decision, user, 2026-10-04).** Several documents may contribute to one fact, so extracting one document never wipes what others gave. Table `FactContributions` (`FactKey`, `Resource` = DocStore path, `Value` = canonical JSON of what that file states, `Hashcode`, `ChunksHash`, `Description`, `GeneratedBy`, `Timestamp`; PK `FactKey, Resource`) is derived extraction data. The fact = deterministic merge of all its contributions (`extract/merge.py`): newest DocStore file first; scalars first non-empty, a different value elsewhere is a reported conflict; string lists unioned (case and spacing ignored); model lists unioned by the item's identity field (its first mandatory field: `id`, `name`, `title`, `role`; a test pins one for every item model), same-identity items merged field by field. Batches of one file merge with the same rules. A CHANGED file replaces only its own contribution, so an item removed from it disappears unless another file states it. A fact stored before any extraction (seeds) becomes the lowest-precedence contribution `(existing)`.
- **Skips and removals.** Unchanged `ChunksHash` = `SKIPPED_UNCHANGED_CHUNKS`, no LLM call (`--force` overrides); this is how a CHANGED file re-extracts only its changed entities. An entity no longer tagged in a file loses that file's contribution and the fact is re-merged (`REMOVED`). A merged fact the saver rejects (e.g. an overview without `purpose`) is `REJECTED` but the contribution is kept for a later document.
- **Scope rule (user, 2026-10-04).** The key comes from the DocStore folder: `<App>.<Entity>`; `Slo` / `Kpis` (savers with only `Shared.` keys) come only from files in `DocStore/shared/` (an application document never overwrites a common standard); `general/` gives no facts. Component keys are not derived.
- **Metadata.** Code derives `title` ('<scope> <entity in words>'), `tags` ([entity, `extracted`]), `generated_by` (`okf-extraction-agent/<model>`) and `sources` (every contributing file with its DocStore timestamp); `description` is the newest contribution's one-sentence summary from the model (user, 2026-10-04).
- **Priorities from keywords (user, 2026-10-04).** A requirement item whose priority the model left empty gets the one its own statement (`description` / `statement`) states: SHALL / MUST / REQUIRED -> MUST, SHOULD / RECOMMENDED -> SHOULD, MAY / OPTIONAL (capitals only) -> COULD, strongest keyword winning; the model's own priority is never changed (`extract/priority_keywords.py`).
- **Report** (`EntityExtractionReport`, outcomes in `ExtractionOutcome`): key, outcome, version, completeness, chunks, batches, failed batches, items, priorities from keywords, contributing files, batch problems, conflicts, values not grounded in the text (identifiers and model-written titles excluded), missing-info questions (one line per unanswered field, list item fields counted 'missing in k of n'), save errors.
- **Entry point:** `python -m docfactory.agents.run_extraction "<DocStore path>" [--entity <Entity> ...] [--force]`. `ExtractionAgent`, its package and `docfactory-okf-extraction-agent.md` were removed; `docfactory-entity-extractor-agent.md` is the runtime prompt (fill only what the chunks state, the document's wording and identifiers, text under a numbered item stays in that item).
- **Verified live (2026-10-04, `gemma4:31b` on Ollama Cloud, default `DOCFACTORY_NUM_CTX`):** the real 50-page SRS gives all 172 non-empty FR identifiers (FR-47/48 are empty rows in the PDF) plus 14 unnumbered items, all 162 NFR identifiers, ApplicationOverview at 83%, Architecture, BackupRecovery, Environments, Monitoring; Slo skipped by scope; priorities FR MUST 127 / SHOULD 53, NFR MUST 165, none contradicting its keyword; FR in 10 calls (1m38), NFR in 6 (1m14); a second run makes no LLM call. `pytest -m live tests/test_live_extraction.py`: the corpus SRS (tagged by the ingestion fallback) gives its three requirements, its revision updates `FunctionalRequirements` to v2 and skips unchanged entities.
- **Left open (none blocks Phase 4):** near-duplicate list entries across batches that differ in wording (e.g. two phrasings of one capability) are not merged; chunks tagged by the ingestion fallback with doubtful entities (real SRS 4.1 User Interfaces, 6.1, 6.3 tagged FunctionalRequirements) yield unnumbered items until the tags are reviewed; `index.md` / `log.md` are not written; `verified` and `stable` wait for Phase 5.

### Phase 4: Generate
- Each fact's `YmlFrontmatter` plus its JSON `Value` (in model field order) is indexed in the vector store; it is rebuilt from the database and sits behind one interface.
- A **DocumentGeneratorAgent** receives a document request, runs the RAG query against the index to find the relevant knowledge records and where they are, then reads each relevant fact's JSON in full (`get_fact`), and builds the document JSON for the document savers. Retrieval prefers `stable` over `draft` and flags `draft`, `deprecated` and stale content.
- Document generation then continues as in Phase 1: validation in the document savers, `DocumentOutputs`, deterministic `render_markdown`. Answers to MissingInfo questions re-enter as documents or sources.

**Phase 4 as built (2026-10-03):**
- **Decisions:** the vector index is a SQLite table plus numpy behind the `VectorIndex` interface (no new heavy dependency; one row per fact); embeddings come from Ollama `/api/embed` behind the `Embedder` interface (`FakeEmbedder` in tests). The embedding model is `DOCFACTORY_EMBED_MODEL`; Ollama Cloud has no embedding models, so `DOCFACTORY_EMBED_HOST` points the embedder at a local server (verified with `mxbai-embed-large`).
- **4a (deterministic, no LLM):** table `FactIndex` (FactKey, TextHash of the embedded text, EmbedModel, Dim, float32 Vector blob), derived and rebuildable, never truth. `SqliteVectorIndex.rebuild()` embeds only facts whose metadata, value or embedding model changed and removes deleted facts. `query()` returns `RetrievalHit`s (key, score, title, type, status, stale, description, from the typed columns), best first, limited to the application plus `Shared`; `stable` gets a +0.05 boost over `draft`, `deprecated` is excluded unless asked for, `stale` means now >= `StaleAfter`. `documents.get_document` / `list_documents` return `DocumentRecord`; `saver_resolution.document_saver_for_key` resolves a body key to exactly one document saver.
- **4b:** the `generator` package holds exactly `search_knowledge`, `get_fact`, `list_facts`, `get_document`, `get_document_schema`, `save_document` and one `save_<document>` tool per document body saver (`save_overview_document`, `save_smtd_document`, `save_sop_document`, `save_srs_document`); a test pins the list. It has no entity savers, no file tools and no savers for `DocumentControl` / `RevisionHistory` (the caller supplies those). Document savers take no `meta`, so a generated body carries no actor; recording who generated a document is left to Phase 5. `GeneratorAgent(client, index).run(app_id, doc_type)` is a thin `AgentLoop` subclass with the runtime prompt `.claude/agents/docfactory-document-generator-agent.md`. Manual trigger `python -m docfactory.agents.run_generation <App> <Overview|SMTD|SRS|SOP>`: rebuilds the index, runs the agent, prints the saved version and completeness, and renders to `output/<App>/<Type>.md` only if the `.DocumentControl` and `.RevisionHistory` rows exist.
- **Verified live** (`pytest -m live tests/test_live_generation.py`, `gemma4:31b` on Ollama Cloud, embeddings from a local Ollama `mxbai-embed-large`): the agent generated the ReadmeForge Overview at 100% completeness and every value in it appears in the deterministic `build_document` result.
- **Not done in Phase 4:** a MissingInfo list for an agent-generated body (the agent's summary names the gaps; `build_document` still produces the list); retrieval does not hide draft or stale hits (it flags them and the prompt requires naming them); only the Overview has been exercised live, SMTD, SRS and SOP are covered by fake-model tests only.

### Phase 5: Human in the loop
- The approval gate becomes a workflow: **agents propose, humans approve, tools apply.** It is built with **LangGraph**, used for orchestration and its **checkpointing** (durable state, `interrupt` to pause for a human, resume with the decision). LangGraph is introduced here and only here; it does not replace the tool layer (Principle 9).
- Graph nodes call the registry tools. Proposals (a classification, a fact payload, a generated document) are held in the checkpoint, not written to the database. Only after approval does the node call the saver. Rejection returns feedback to the agent.
- The human approval is what adds `verified` with a `human:<id>` actor and promotes `draft` to `stable` (see the Phase 3 trust rule).
- To design in Phase 5: which steps need approval (classification, facts, documents), the checkpoint store (SQLite, kept apart from `docfactory.sqlite`), the approval interface (CLI first), and the timeout and escalation rule for pending approvals.

### Phase 6: Automate
- A watcher for `incoming/`, automatic triggering of the agents, and the end-to-end workflow: ingest, extract, approve, generate, render. Triggers become automatic; the approval gate from Phase 5 stays.
- To design in Phase 6: the watcher, the trigger rules (new or changed file, stale fact, changed fact -> regenerate the affected documents), failure and retry handling, and monitoring of runs.

## Working rules

- Read this file first. When something is unclear, ask the user.
- One class per file, in the right folder (Principle 1). Create models and savers through the `docfactory-pydantic-developer-agent`.
- Write to the database only through the tools. Never edit generated documents or `DocStore/` files by hand; change the models or documents and regenerate.
- Changing a model changes stored data's meaning: say so and update the tests and golden files in the same change.
- Descriptions on models and fields are part of the product: write them for an LLM reader (meaning, example of a good value, what to ask if missing).
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes.
- Keep the repo in git so data-shape changes are diffable.
