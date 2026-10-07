# docFactory (Pydantic approach)

Keeps application documentation (Overview, SMTD, SRS, SOP) up to date from structured knowledge. Knowledge is held as **Pydantic-validated JSON objects in SQLite**; documents are **composed Pydantic objects** rendered to Markdown by deterministic code.

## Status

- **Phase 1 (DONE, closed 2026-10-03): the deterministic core.** Seed data -> saver calls -> validated facts in SQLite -> composed document objects -> `.md` files. No LLM. Everything is unit-testable.
- **Phase 2 (DONE, closed 2026-10-03): Ingest.** Original files (text, PDF, Word, HTML) arrive in `incoming/`, move to `staging/`, are chunked deterministically from the raw file, tagged with entities against an ontology (rules first, a small LLM fallback for what the rules cannot tag or place), and moved into `DocStore/<scope>/`; the `DocStore`, `DocStoreHistory`, `DocChunks` and `DocChunkTags` tables track them (see "Phase 2: Ingest").
- **Phase 3 (DONE, closed 2026-10-04): Extract knowledge (OKF).** **3a** is the deterministic OKF layer: OKF v0.2 metadata in `KnowledgeFacts` columns, history table, typed reads; the content of every fact is the validated JSON in `Value`. **3b** extracts from Phase 2's tagged chunks: per entity tagged in a `DocStore` file, its chunks go in small batches, one fresh single-tool LLM call per batch returns a partial object, and code checks, merges (batches, then every contributing file via `FactContributions`) and saves through the entity saver (see "Phase 3: Extract knowledge (OKF)").
- **Phase 4 (DONE, closed 2026-10-07): Generate.** For an application and a document template, code groups the stored fact JSON by the template's bindings into the document body, maintains the document control and revision history, saves them through the document savers and renders `output/<App>/<DocType>.md`. One small, checked LLM call turns the deterministic gaps into the document's needs list (the `MissingInfo` row, rendered to `<DocType>.missing.md`) (see "Phase 4: Generate").
- **Phase 5 (PENDING, outline only): Human in the loop.** The approval gate as a workflow (agents propose, humans approve, tools apply), built on LangGraph checkpointing and interrupts.
- **Phase 6 (PENDING, outline only): Automate.** A watcher for `incoming/`, automatic triggering and the end-to-end workflow.
- **Triggers are manual until Phase 6:** files are moved into `incoming/` and the user runs each step by hand. `README.md` explains the process and lists the commands.

Nothing described here exists until it appears in the repo. If something is unclear, ask the user before coding.

## Principles

1. **Single Responsibility (strongest rule).** Every class lives in its own file, and every module has one reason to change.
   - Every Pydantic class, including small nested item classes, is in its own file. Entity models go in `docfactory/entitymodels/facts/` (facts, which have a saver) or `docfactory/entitymodels/items/` (nested items and enums, no saver), document models in `docfactory/documentmodels/`, common and shared models in `docfactory/models/`.
   - Every entity saver is in its own file under `docfactory/entitysaver/`; every document saver is in its own file under `docfactory/documentsaver/<role>/`.
   - The file is named after its class in snake_case (`ApplicationOverview` -> `application_overview.py`, `ApplicationOverviewSaver` -> `application_overview_saver.py`). A module never defines two classes; a function module defines none.
   - A class does one thing: a model describes and validates data, a saver stores it, the renderer renders it, the database module talks to SQLite. None of them does another's job.
   - Tests enforce the file and naming rule (see "Tests").
2. **The facts in `KnowledgeFacts` are the source of truth.** Generated documents are views of them, never the other way round. `.json` files under `knowledgefacts/` and `.md` files under `output/` are views too (written for visibility), never edited by hand. The content of a fact is its validated JSON (`Value`); OKF is only the metadata in its row.
3. **Only valid data is stored.** Every write goes through a Pydantic model. Invalid input is rejected with a structured error and nothing is written.
4. **Models are the contract.** Every model and field has a description written for an LLM: what it means, what a good value looks like, what to ask when it is missing. The same model is the validator, the LLM's tool schema and the documentation.
5. **Deterministic code does all the work that can be deterministic:** validation, canonical JSON, hashing, SQL, completeness, merging, composition, document control, revision history, rendering, moving files. An LLM only does judgment work: tag what the rules cannot tag, pick a scope the rules cannot pick, find the information in a batch of chunks, and phrase a document's gaps as a needs list. Every LLM call has exactly one tool, and code checks its answer.
6. **Never invent values.** A default is a placeholder, not knowledge. Completeness counts only what was actually answered. Do not fill fields to raise a score.
7. **Errors are feedback.** A rejected call returns errors precise enough for a caller (test or LLM) to fix the payload or go and find the missing information.
8. **Only tools write to the database.** No hand-edited rows, no hand-edited generated documents.
9. **The tool layer is plain in-process Python function tools.** The tools an LLM call uses are ordinary Python functions with typed arguments, collected in an in-process registry. No MCP server, no framework-specific tool classes. The tool schema is derived from the Pydantic models (Principle 4). Agent loops and any orchestration framework (LangGraph in Phase 5) only call these functions; they never contain business logic, so the tool layer is testable without an LLM and survives a change of runtime.
10. **Least privilege for agents.** Every LLM call is given only the tools it needs, nothing more. Tools are grouped in **tool packages**, one package per kind of call (ingestion tagging, ingestion scope, extraction, generation needs), and a call can reach only the tools of its own package. File operations are deterministic code that no agent controls; no agent gets a shell, a general file system or database access. A test pins each package's exact tool list, so a tool cannot be added unnoticed.

## Data flow

```
incoming/ -> staging/ -> chunk + tag (ontology rules, LLM fallback) (Phase 2) -> DocStore/ (+ DocStore, DocChunks, DocChunkTags)
                                                                                        |
        one small LLM call per batch of an entity's tagged chunks (Phase 3)  <----------/
                                   |
                                   v
            FactContributions, one per file --merge--\
seed data (Phase 1) ------------------------------------>-- XSaver.save() --validate--> KnowledgeFacts (Value = entity JSON, hash, completeness,
                                                                                          version, OKF metadata columns, trust, lifecycle)
                                                                                          + views knowledgefacts/<scope>/<Entity>.json / .missing.md
                                                                                        |
            document template (composed document model, bindings <Entity>.<field>)      |  (Phase 4)
                                                                                        v
              build_document --> body; code --> DocumentControl, RevisionHistory --document savers--> DocumentOutputs
              gaps (unfilled fields + open questions of bound fields) --one checked LLM call--> MissingInfo row
                                                                                        |
              render_markdown --> output/<App>/<DocType>.md        MissingInfo --> output/<App>/<DocType>.missing.md
```

## Models

One Pydantic v2 model per file, in three folders. `models/` is flat; `entitymodels/` has two sub-folders, `facts/` and `items/`; `documentmodels/` has one sub-folder per role (below):

| Folder | Holds | Examples |
|---|---|---|
| `docfactory/entitymodels/facts/` | **EntityModels that are knowledge facts**: every entity model that has a saver in `entitysaver/` | `ApplicationOverview`, `Architecture`, `Environments`, `FunctionalRequirements`, `NonFunctionalRequirements`, `Slo`, `Kpis` |
| `docfactory/entitymodels/items/` | **EntityModels that are nested items and enums**: every entity model with no saver | `Environment`, `Requirement`, `Alert`, `Component`, `RequirementPriority` |
| `docfactory/documentmodels/<role>/` | **DocumentModels**: output documents, their sections and their parts, in three role sub-folders (below) | `OverviewDocument`, `DocumentControl`, `RevisionHistory`, `MissingInfo`, `ApplicationSummarySection` |
| `docfactory/models/` | **Machinery models**: reusable building blocks of the system itself, independent of any application knowledge. They make the code work; they hold no information about an application | the base model, `doc_field`, `NotApplicable`, `SaveAction`, `SaveResult`, `SaveError`, `FactMeta`, the run reports |

**The dividing line:** `models/` is for machinery (how the system validates, saves and reports). Anything that describes information about an application or its environment, including a small nested item type such as `Alert`, `Component`, `Environment` or `Integration`, is an entity model and lives in `entitymodels/` (`facts/` when it has a saver, else `items/`; nothing sits directly in `entitymodels/`), even when it is never saved on its own and even when a document section also uses it. Document models import entity models where they need them; the reverse never happens. `models/` never imports `entitymodels/` or `documentmodels/`.

**Document model roles.** Every file in `documentmodels/` (and every document saver in `documentsaver/`) lives in exactly one role sub-folder, picked by what the class depends on:

| Role folder | Holds | Fields bind to | May import from |
|---|---|---|---|
| `documents/` | A document body, composed of sections: one per document type (`OverviewDocument`, `SmtdDocument`, `SrsDocument`, `SopDocument`) | `composed` sections | `entitybound/`, `shared/` |
| `shared/` | Parts every document type uses, written by the generate process: `DocumentControl`, `RevisionHistory` and its `RevisionEntry`, `MissingInfo` (the needs list) and its `DocumentGap`, `DocumentNeed`, `NeedsOrigin` | `caller` | nothing in `documentmodels/` |
| `entitybound/` | A section in a specific format over entity facts: `ApplicationSummarySection`, `KpiSummarySection`, ... | `Entity.field` | nothing in `documentmodels/` |

Nothing goes deeper than the role folder. A document saver mirrors its model's role (`documentsaver/shared/document_control_saver.py` saves `documentmodels/shared/document_control.py`); `entitybound/` has no savers because a section is stored inside its document body. `shared/` here means "shared across document types"; a type used by both entities and documents is an entity model.

- An entity is an **aggregate**: list-like content (requirements, environments, components, SLOs) is a list of typed item models inside one object.
- All models derive from one base model (`docfactory/models/`, its own file) that sets `extra="forbid"` (a hallucinated field is an error) and requires a description on every field (enforced by a test).
- **Mandatory fields are the absolutely necessary ones only** (what identifies the object or makes it meaningless). Everything else has a default where a default is legitimate (`None`, empty list, empty string). If no honest default exists, the field is mandatory. **Fields of `entitybound/` sections are never mandatory**: a section is a view, and a fact that is not there yet is a gap, not an invalid document.
- Field metadata beyond the type (`doc_field`): `description` (meaning and what a good answer contains), `question` (asked when the field is missing; defaults to the description), whether `N/A` is a legal answer (`na_allowed`), `scored` (default true), `binding` (documents), `render_as` (`list`, `numbered`, `table`), and the constraints `min_length`, `max_length`, `ge`, `pattern`.
- Two kinds of knowledge fact, distinguished only by scope in the key:
  - **Common** to all applications: `Shared.Kpis`, `Shared.Slo` (AppID NULL).
  - **Application-specific:** `ReadmeForge.ApplicationOverview`, `ReadmeForge.Architecture` (AppID = `ReadmeForge`).
- **Output-specific** content (document control, revision history, needs list) is not a knowledge fact. It belongs to one generated document and lives in `DocumentOutputs` (see "Documents").
- Models are Python code, versioned by git. There is no schema-version column.

## Database (SQLite, `db/docfactory.sqlite`)

`KnowledgeFacts` and `DocumentOutputs` have the same core shape. `KnowledgeFacts` additionally has the OKF columns (see "Phase 3: Extract knowledge (OKF)"), supported by `KnowledgeFactsHistory` and `KnowledgeFactSources` (a derived index of each fact's `sources`, written by the saver, used by `list_facts_by_source`). `FactContributions` holds what each `DocStore` file contributed to an extracted fact; the fact is their merge. The ingestion tables are described under "Phase 2: Ingest".

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
- The key must match one of the saver's own key patterns; the saver's model validates the value. `saver_resolution.py` resolves a key to exactly one saver. Key segments become folder and file names (`knowledgefacts/`), so an unsafe segment is rejected (`key_unsafe_path`).
- **The whole object is saved, and only when its hash differs.** Identical `Hashcode` = no-op (`UNCHANGED`): the row's `Value`, `Hashcode`, `Version` and `Completeness` are untouched (for a knowledge fact saved with `meta`, only the OKF metadata columns and `YmlFrontmatter` are refreshed in place, still without a version bump). A different hash replaces the row's `Value` and `Hashcode`, recomputes `Completeness` and sets `Version = Version + 1`. First write is `Version = 1`. There are no partial updates: a caller sends the complete object.
- `Version` counts changes to the current row. `KnowledgeFactsHistory` records each change of a fact (who and when, not the old value).
- **Multi-component applications:** each component has its own keys, `<App>.Components.<Component>.<Entity>`, e.g. `ReadmeForge.Components.api.Architecture`. `AppID` is still the application (`ReadmeForge`). The application-level keys (`ReadmeForge.Architecture`, ...) hold the high-level view of the whole application. Component keys reuse the same models as application keys. The component name is free text and is not validated.
- Key examples: `ReadmeForge.ApplicationOverview`, `ReadmeForge.Architecture`, `Shared.Kpis`; documents: `ReadmeForge.Outputs.SMTD`, `ReadmeForge.Outputs.SMTD.DocumentControl`, `ReadmeForge.Outputs.SMTD.RevisionHistory`, `ReadmeForge.Outputs.SMTD.MissingInfo`.

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

Plain Python, no framework. Everything is deterministic and callable from tests, seed scripts and pipelines (`ApplicationOverviewSaver().save(key, payload)`); no LLM calls a saver directly (see "Tool layer").

- **`BaseSaver`** (`docfactory/base_saver.py`, generic over the model) owns all shared behaviour, so concrete savers contain no logic of their own:
  1. check the key against the saver's own `key_patterns`; derive `AppID` (NULL for `Shared`)
  2. validate the payload with the Pydantic model
  3. canonical JSON -> SHA-256 hash
  4. read the existing row: same hash -> `UNCHANGED`; no row -> `CREATED`, `Version = 1`; different hash -> `UPDATED`, `Version + 1`
  5. compute completeness
  6. write in one transaction (never on `REJECTED`); entity savers also write the OKF columns, a `KnowledgeFactsHistory` row on `UPDATED`, the source index (`docfactory/fact_writer.py`) and the fact's views under `knowledgefacts/` (`docfactory/fact_files.py`)
- `save(key, payload, app_id=None, meta=None)`: `meta` (`FactMeta`) is for entity savers only; a document save with `meta` is rejected (`meta_not_allowed`).
- **Entity savers** (`docfactory/entitysaver/`, one file each) inherit `BaseSaver`, declare only the model and key pattern, and write `KnowledgeFacts`.
- **Document savers** (`docfactory/documentsaver/documents/` and `docfactory/documentsaver/shared/`, one file each) inherit `BaseSaver`, declare only the model and key pattern, and write `DocumentOutputs` (body, `.DocumentControl`, `.RevisionHistory`, `.MissingInfo`).
- Return value is always a `SaveResult` model, never an exception for bad input:

```
SaveResult { ok, key, action: CREATED|UPDATED|UNCHANGED|REJECTED, version, hashcode, completeness,
             errors: [ SaveError { path, message, error_type, received, expected, field_description, question } ] }
```

- On `REJECTED` nothing is written. Each error carries the Pydantic message plus the field's description and question, so the caller knows what to fix or what to find out.
- Read side: `db.get_row(table, key)` and `db.list_rows(table, app_id=None)` return stored rows. Typed `get_fact` / `list_facts` / `list_facts_by_source` (returning `FactRecord`) are in `docfactory/facts.py`; `get_document` / `list_documents` (returning `DocumentRecord`) are in `docfactory/documents.py`.

## Documents

- A document type (Overview, SMTD, SRS, SOP) is a composed **DocumentModel**, its **template**: it is made of `entitybound/` section models, and each section field is bound to a fact field. Sections are reusable across document types. Each is its own file in the `docfactory/documentmodels/<role>/` folder for its role (see "Models"). A new document type is a new body model (through the developer agent) plus one line in `docfactory/generation/doc_types.py`; no new generation code.
- Each document field declares its **binding**: which fact field supplies it (for example `FunctionalRequirements.requirements`), plus the same field metadata as entities (description, question, `na_allowed`).
- `build_document` is deterministic: it reads the app's facts and the shared facts, copies every answered bound field into the document object, and leaves the rest at their defaults, listed as gaps. It does not invent content and never fails on a missing fact (`BuildError` only means a wrongly wired template).
- **Every output document is four rows in `DocumentOutputs`**, each a validated Pydantic object with its own hash, completeness and version:
  - `<App>.Outputs.<DocType>` - the document body (all chapters), **without** document control and revision history. Built from the knowledge facts.
  - `<App>.Outputs.<DocType>.DocumentControl` - document id, title, version, status, owner, approvers, dates. Never from knowledge facts: maintained by the generate process (the ReadmeForge seeds supply their own).
  - `<App>.Outputs.<DocType>.RevisionHistory` - the list of revisions (version, date, author, change summary). Never from knowledge facts: maintained by the generate process (the seeds supply their own).
  - `<App>.Outputs.<DocType>.MissingInfo` - the needs list: the document's gaps and the questions to ask for them (see "Phase 4: Generate").
  All four use the same `<App>.Outputs.<DocType>` prefix, so a document's parts are found by prefix.
- `render_markdown` assembles the final `.md` from the body, document control and revision history (order: document control, revision history, body); it refuses with a clear `RenderError` when a row is missing. `render_needs_markdown` renders the `MissingInfo` row to `<DocType>.missing.md`. Same rows in, same bytes out. The files under `output/<App>/` are views and never truth. The body's completeness is computed over the body only; the other rows score their own.

## The `docfactory-pydantic-developer-agent`

All models and savers are produced through a specialized agent, `.claude/agents/docfactory-pydantic-developer-agent.md`, built around the principles above, so they come out uniform.

- **The agent** knows and enforces: single responsibility (one class per file, file name = snake_case of the class, correct folder), the base model, descriptions and questions on every field, honest defaults and minimal mandatory fields, typed lists and no `dict`/`Any`, `NotApplicable` only where `na_allowed`, scoring rules, and that savers inherit `BaseSaver` and contain no logic. It writes a test with every class it creates and runs the suite before it reports done.
- **Entry skills** (in `.claude/skills/`, invoked as `/docfactory-<task>`; **every skill and custom agent in this project is named with the `docfactory-` prefix**, enforced by a test), one per repeatable task, each pinning the agent and model (`context: fork`, `agent: docfactory-pydantic-developer-agent`, `model: sonnet`) and defining the exact step-by-step procedure: `docfactory-create-shared-model` (base classes and package skeleton, or one shared model), `docfactory-create-entity-model` and `docfactory-create-document-model` (each also creates the saver where one belongs), `docfactory-add-field`, `docfactory-review-models`. Two reference skills (`docfactory-field-spec`, `docfactory-quality-gate`) are preloaded into the agent. Skills cannot be `.claude/commands/` files: only skills support `agent` and `context: fork`.
- **Deterministic scripts** (`.claude/scripts/`, tested in `tests/scripts/`): the agent supplies judgment as a JSON spec; scripts resolve names and paths, generate models, savers and their tests, add fields, check structure and run the quality gate. Conventions the generated code relies on (base model `DocFactoryModel`, field helper `doc_field`, `BaseSaver`, key-pattern placeholders) are in `.claude/scripts/conventions.py`. The spec scripts do not yet emit the `ge` and `max_length` constraints of `doc_field`; write those by hand.
- The agent never edits the database or generated documents by hand, and never invents field content.

## Sample data

- **ReadmeForge** (the Phase 1 sample application): hard-coded seed scripts in `seed/` save its facts from `samples/json/<entity>/` and build, save and render its four documents with their own document control and revision history. The golden files in `tests/golden/` are these outputs.
- **AI-Driven-Job-Matching-Platform** (a real 50-page SRS): a committed snapshot of one end-to-end run (ingest, extract, generate) in `samples/DocStore/`, `samples/knowledgefacts/` and `samples/output/`. Copies for reading; the code never reads them.

## Tests (pytest, every test uses a temporary database and temporary folders)

- **Structure:** every module in `models/`, `entitymodels/<facts|items>/`, `documentmodels/<role>/`, `entitysaver/` and `documentsaver/<role>/` defines exactly one class, named after the file (snake_case); documents and savers sit in a role folder, a class in `entitymodels/facts/` has a matching saver and one in `entitymodels/items/` has none, a document saver sits in the same role as its model, and `documentmodels/` roles only import as allowed by the role table; every Pydantic class is under `models/`, `entitymodels/` or `documentmodels/`; every field of every registered model has a description; no model contains `dict`, `Any` or untyped list items. In `tools/`, `agents/`, `ingest/`, `ontology/`, `extract/` and `generation/`, a class module defines one class named after the file and a function module defines none (`tests/test_phase2_structure.py`).
- Savers: valid payload -> `CREATED` with canonical JSON, SHA-256, AppID, completeness and `Version = 1`; same payload -> `UNCHANGED`; changed payload -> `UPDATED`, `Version = 2`; changing back is a new change (`Version = 3`); a new saver subclass gets all this with no code of its own; key order does not change the hash; component keys store the application's AppID; `Shared.*` stores NULL AppID; a mismatching AppID or a key matching none of the saver's patterns is rejected; missing mandatory field, wrong type, bad enum, extra field -> `REJECTED`, nothing written, errors with path, description and question.
- Completeness: defaults are not answered (even when passed explicitly); a legal `NotApplicable(reason)` is; `N/A` on a field without `na_allowed`, or with an empty reason, is rejected; item-level scoring as above.
- Every JSON file under `samples/json/` validates against the model of its folder, and every sample folder has a model (`tests/test_samples.py`).
- Build + render of the ReadmeForge documents match the golden files; rendering twice gives identical bytes; a missing fact leaves its field at the default and listed as a gap; rendering with a missing `.DocumentControl` row fails with a clear error.
- Ingestion, extraction and generation pipelines are tested with a fake model client; the tool packages' exact tool lists are pinned. Live tests (`-m live`) call the configured LLM and skip themselves when it is unreachable.

## Repo layout

```
.claude/agents/        docfactory-pydantic-developer-agent.md, docfactory-sample-generator-agent.md (development agents); docfactory-chunk-tagger-agent.md, docfactory-scope-agent.md, docfactory-entity-extractor-agent.md, docfactory-needs-list-agent.md (runtime prompts of the LLM calls)
.claude/skills/        Entry skills (docfactory-create-shared-model, docfactory-create-entity-model, docfactory-create-document-model, docfactory-add-field, docfactory-review-models) and reference skills (docfactory-field-spec, docfactory-quality-gate)
.claude/scripts/       Deterministic scripts the skills call (scaffold, add field, check structure, gate)
docfactory/            Python package
  models/              Machinery models, one class per file: base model, doc_field, NotApplicable, SaveAction, SaveResult, SaveError, FactMeta, FactSource, FactVerification, FactRecord, FactStatus, FactQuestion, DocumentRecord, the ingestion, extraction and generation models and reports, the model-client messages
  entitymodels/        EntityModels, one class per file, in two sub-folders:
    facts/             the facts, each with a saver: ApplicationOverview, Architecture, Environments, Deployment, Monitoring, BackupRecovery, KnownErrors, Sop, Support, Slo, Kpis, FunctionalRequirements, NonFunctionalRequirements
    items/             nested item types and enums, no saver: Environment, Requirement, Alert, Component, RequirementPriority, ...
  documentmodels/      DocumentModels, one class per file, in role sub-folders:
    documents/         document bodies (OverviewDocument, SmtdDocument, SrsDocument, SopDocument)
    shared/            DocumentControl, RevisionHistory, RevisionEntry, MissingInfo, DocumentGap, DocumentNeed, NeedsOrigin
    entitybound/       one section per entity fact (ApplicationSummarySection, ArchitectureSection, KpiSummarySection, ...)
  entitysaver/         One entity saver per file (write KnowledgeFacts)
  documentsaver/       One document saver per file (write DocumentOutputs), mirroring the model's role
    documents/         savers of document bodies
    shared/            savers of DocumentControl, RevisionHistory, MissingInfo
  base_saver.py        BaseSaver
  db.py                Connection, schema creation and migration, upsert, reads
  canonical.py         canonical JSON + SHA-256
  completeness.py      completeness scoring
  clock.py             now_iso() (tests replace it)
  build.py             build_document and its helpers (fact_key, load_fact, is_answered, bound_fields)
  render.py            render_markdown, render_needs_markdown
  facts.py documents.py  typed reads of KnowledgeFacts (FactRecord) and DocumentOutputs (DocumentRecord)
  okf_frontmatter.py fact_writer.py   the YmlFrontmatter column; fact storing with the OKF columns (called by BaseSaver)
  fact_files.py open_questions.py missing_md.py   the knowledgefacts/ views; `python -m docfactory.fact_files` rewrites them all from the database and removes orphans
  contributions.py     typed access to FactContributions (FactContribution); EXISTING = '(existing)' for a value stored before any extraction
  saver_resolution.py  entity_saver_classes(), entity_saver_for(entity), saver_for_key(key), document_saver_classes(), document_saver_for_key(key), ordered_value (a stored value in model field order)
  env_file.py          Loads .env into the environment (shell variables win); used only by entry points and live tests
  ingest/              Phase 2 function modules: pipeline (stage, lookup, commit, report), chunking + chunkers/ (pdf, word, html, text), tagging, scope_rules, chunk_rebuild, docstore_reads, paths, file_hash, target_rules. No LLM
  ontology/            signals.json (tagging signals per entity, edited by people), signals.py (validated load), ontology_render.py (docs/ontology.md and the compact LLM summary)
  extract/             Phase 3 function modules: batching (BATCH_CHARS, chunks_hash), fact_keys, partial_schema, model_shapes, grounding, merge, priority_keywords, missing_questions, extraction_pipeline (extract_file, format_reports)
  generation/          Phase 4 function modules: doc_types (DOC_TYPES: body model, saver, document name per type), gaps (document_gaps, gaps_hash), document_control (next_control), revision_history (changed_sections, section_sources, revision_summary, next_history), fallback_needs, generate_document (generate, format_reports, output_dir)
  generate.py          Entry point `python -m docfactory.generate <App> <DocType|all> [--no-llm]`
  tools/               Tool, ToolRegistry, ToolPackage (one class per file); the single-tool packages ingestion_tools (submit_chunk_tags, submit_scope), extraction_tools (submit_extraction), needs_tools (submit_needs); schema_slim (inline_refs for tool schemas)
  agents/              ModelClient (abstract), OllamaModelClient (default), AnthropicModelClient (optional), FakeModelClient (tests), model_client_factory, AgentLoop (the shared thin loop), prompt_file, IngestionFallback, EntityExtractor, NeedsWriter; entry points run_ingestion, run_extraction
samples/json/<entity>/ Example JSON payloads per entity (ReadmeForge, plus shared Kpis and Slo), used by the seeds and tests
samples/DocStore/ samples/knowledgefacts/ samples/output/   Committed snapshot of the AI-Driven-Job-Matching-Platform end-to-end run
seed/                  Hard-coded seed scripts for ReadmeForge (overview, requirements, SMTD, SRS and SOP); seed_meta.py: SEED_META, the FactMeta (generated_by `seed`) every seeded fact is saved with
tests/                 pytest; tests/golden/ holds the golden .md files, tests/scripts/ tests the .claude/scripts; tests/corpus/ (build_corpus.py, messy originals, a revised SRS, corpus_expectations.json); tests/live_support.py: the live tests' server check
docs/ontology.md       Generated view of the ontology (entities, facts, tagging signals)
docs/okf/SPEC.md       Verbatim copy of the OKF v0.2 spec
README.md              The process end to end and every command to run (keep it in step with the entry points)
STATUS.md              Where the work stands: phase states, runtime state, next steps
.env / .env.example    Local LLM settings (.env is gitignored)
--- runtime data, gitignored ---
db/docfactory.sqlite   The database
incoming/              Drop zone for new original files
staging/               Files being ingested, and files waiting for a human decision
DocStore/<scope>/...   Classified originals; scope = application name, shared, general
knowledgefacts/<scope>/...  One JSON file per fact key, the key segments as folders (ReadmeForge/Sop.json, Shared/Kpis.json, ReadmeForge/Components/api/Architecture.json): the fact's Value in model field order, and next to it `<Entity>.missing.md`, the fact's open questions (none = no file). Written only by the saver
output/<App>/          Rendered documents (<DocType>.md) and their needs lists (<DocType>.missing.md)
--- planned, do not create until the phase starts ---
docfactory/agents/     Phase 5 adds the LangGraph graph, checkpointer and approval nodes
```

Env `DOCFACTORY_DB` points the code at another database file (tests use a temporary one). `DOCFACTORY_INCOMING`, `DOCFACTORY_STAGING`, `DOCFACTORY_DOCSTORE`, `DOCFACTORY_KNOWLEDGEFACTS` and `DOCFACTORY_OUTPUT` relocate `incoming/`, `staging/`, `DocStore/`, `knowledgefacts/` and `output/` (tests use temporary folders). LLM settings (from `.env`): `DOCFACTORY_PROVIDER` (`ollama` default, or `anthropic`), `DOCFACTORY_MODEL`, `OLLAMA_HOST`, `OLLAMA_API_KEY`, `DOCFACTORY_NUM_CTX` (Ollama context window, default 16384; enough for every call, whose one tool schema is at most ~1.5k tokens). The model in use is `gemma4:31b` on Ollama Cloud.

Runtime dependencies: pydantic, pdfplumber, python-docx and beautifulsoup4 (the chunkers); `anthropic` is an optional extra; the Ollama client uses only the standard library. LangGraph arrives in Phase 5. Dev only: pytest, reportlab (corpus generation), pyyaml. A dependency is added only in the phase that needs it.

## Pipeline (Phases 2-6)

**Ingest (move to store) > Extract knowledge (OKF) > Generate documents.** Phases 5 and 6 wrap this pipeline in a human approval gate and then automate it. Each phase is built, tested and closed before the next starts. All steps are run manually until Phase 6.

### Tool layer (Principles 9 and 10)
- **Function tools:** every capability an LLM call may use is a plain Python function with typed arguments and a typed return. All tools today are **answer tools**: they validate the model's answer against a model, return feedback the model can act on, and hand an accepted answer back to the calling code. They write nothing and move nothing; the pipelines save through the savers and move the files.
- **Registry and tool packages:** an in-process registry (`ToolRegistry`) holds tools by name, each with a description written for an LLM and a schema derived from its typed signature. A **tool package** (`ToolPackage`) is a named, fixed list of registry tools; a call is constructed with exactly one package and the loop can only call tools in it (any other call is refused). Each package is built per call, so its tool closes over that call's input (the batch text, the gaps).
- **The packages** (each pinned by a test):
  - `ingestion-tagging` = [`submit_chunk_tags`] and `ingestion-scope` = [`submit_scope`] (Phase 2 fallback calls).
  - `extraction` = [`submit_extraction`] (Phase 3, one entity and one batch of its chunks).
  - `generation-needs` = [`submit_needs`] (Phase 4, one document's gaps).
  - **Phase 5:** LangGraph nodes call the registry tools unchanged and respect the same packages.
- `AgentLoop` is thin: call the model, run the requested tool, return its result to the model, stop when the model answers in text or at a turn cap; it nudges once on an empty reply and then fails loudly. It is tested with a fake model.
- **Provider-neutral model interface:** `ModelClient.complete(system, messages, tools)` over neutral machinery models; default provider Ollama (local, or Ollama Cloud with `OLLAMA_HOST=https://ollama.com` and `OLLAMA_API_KEY`), Anthropic optional; cut-off responses raise; connection and 5xx errors are retried; tested with `FakeModelClient`.

### Decisions
- `KnowledgeFacts` is the source of truth. Document savers write `DocumentOutputs`; entity savers write `KnowledgeFacts`. There is no separate knowledge-store table.
- LLMs only tag, scope, extract and phrase; everything else is deterministic (Principle 5). Validation errors (`REJECTED`) and tool refusals are the feedback loop.
- Files in `DocStore/` are written only by the ingestion pipeline. Nothing is hand-edited.

### Phase 2: Ingest
Phase 2 is **ingestion, chunking and movement**; extraction is Phase 3. Everything is deterministic; an LLM is called only where the rules give no answer.

**Flow per file** (`docfactory/ingest/pipeline.py`, files in case-insensitive name order):
1. **Stage:** `incoming/<name>` moves to `staging/`. From here a failure leaves the file in staging; nothing is deleted except a verified SAME duplicate. Files left in staging are retried on every run.
2. **Lookup** in `DocStore` by file name and by hash across all scopes: same name and hash with the stored file present on disk with that hash = **SAME** (staged copy discarded); same name and hash but the stored file missing or altered = **REPAIRED** (put back, chunks rewritten, version unchanged); same content under another name = left in staging as a duplicate; same name in exactly one scope with another hash = **CHANGED** (scope inherited, version + 1); same name in several scopes = left in staging; otherwise **NEW**.
3. **Chunk the original** (`ingest/chunking.py`, readers in `ingest/chunkers/`): PDF with `pdfplumber` (body size from paragraph-length lines; headings are clearly larger lines, numbered ones get their level from the numbering; in a numbered document unnumbered large lines such as cover titles and diagram labels stay text; tables read row by row so an identifier stays with its statement, `FR-85. | The system SHALL ...`; table-of-contents lines, page numbers and running headers dropped; symbol-font bullets become '-'), Word with `python-docx` (heading styles, tables), HTML with `BeautifulSoup` (h1-h6, tables, nothing read twice), text/markdown (headings, numbering, markdown tables). A chunk is one section with its heading trail (`3. ... > 3.1. ... > 3.1.1. ...`), never splitting a section's element; a table header row is kept once per section; sections over 4000 chars split into parts; a leading title styled as a heading stays front matter; no headings = 1500-char parts. No text (scanned PDF) or an unsupported type = left in staging.
4. **Tag chunks with entities** (`ingest/tagging.py`) against the **ontology** (below): heading term in the chunk's own heading 4, in a parent heading 3 (inherited), identifier pattern 4, keywords 1 each up to 3; an entity tags at score >= 3 **and** with a strong signal (keywords alone never tag); the longest heading match wins ('non-functional requirements' is not 'functional requirements'); plurals match. A chunk may carry several entities. Chunks no entity reaches are **unmapped**.
5. **LLM fallback for unmapped chunks** (`agents/ingestion_fallback.py`): one call, fresh context, one tool `submit_chunk_tags`; it sees the compact ontology summary and only the unmapped chunks' headings and first 300 chars. Code validates the answer (closed entity list, only the asked chunks, every asked chunk answered) and feeds errors back; accepted tags keep origin `llm/<model>`. A failed or empty call leaves the chunks unmapped.
6. **Scope (NEW only)** (`ingest/scope_rules.py`): only shared entities tagged (Slo, Kpis) = `shared`; else the name from a document-control row (`Title | ...`) or the title line, with document-type wording removed ('Software Requirements Specification for', '(working draft 0.3)', 'on-call runbooks') and line-break hyphens mended; an existing folder matching ignoring case and punctuation is reused; the folder name replaces other characters with '-' (`AI-Driven-Job-Matching-Platform`). An unconfident scope goes to the **scope fallback**: one call, one tool `submit_scope` (application name, `shared`, `general` or null); null leaves the file in staging with both reasons.
7. **Move + commit:** `staging/<name>` -> `DocStore/<scope>/<name>`, then one transaction writes `DocStore` / `DocStoreHistory`, `DocChunks` and `DocChunkTags`. If the write fails the file goes back to staging and a replaced original is restored. On CHANGED the report names the entities whose chunks changed or disappeared (to re-extract).
8. **Report** per file (`IngestReport`): outcome, target, version, chunk count, entity -> chunk count (with how many by the LLM), unmapped chunks, changed entities, reason.

**Ontology:** `docfactory/ontology/signals.json` (edited by people) holds per entity the heading terms, identifier patterns and keywords, validated by `EntitySignals`; a test fails when an entity has no entry, an entry names an unknown entity or appears twice. `docs/ontology.md` is generated (`python -m docfactory.ontology.ontology_render`) from the entity models plus the signals; `ontology_summary()` is the compact form sent to the LLM.

**Tables:** `DocStore` (`FullPath` PK, `Hashcode`, `Version`, `Timestamp`) and `DocStoreHistory` (a row per change); `DocChunks` (`FullPath`, `ChunkNo`, `Heading`, `PageFrom`, `PageTo`, `Text`, `TextHash`) and `DocChunkTags` (`FullPath`, `ChunkNo`, `Entity`, `Origin` = `rule` or `llm/<model>`, `Score`, `Evidence`). The entity map of a file is a query over `DocChunkTags`. Chunks and tags are derived data: `python -m docfactory.ingest.chunk_rebuild` re-chunks and re-tags (rules only) every stored original after the chunkers or signals change. `docstore_reads.read_docstore_text` rebuilds a file's text from its chunks.

**Models:** `DocChunk`, `ChunkTag`, `ChunkTagProposal`, `EntitySignals`, `IngestOutcome`, `IngestReport`. **Entry point:** `python -m docfactory.agents.run_ingestion [--no-llm]`.

**Verified:** on the real 50-page SRS: 76 chunks, 6 of them tagged by the fallback, 3 unmapped, scope `AI-Driven-Job-Matching-Platform` from the document-control title row. Live corpus test (`pytest -m live tests/test_live_ingestion.py`): the fallback tags the informal ReadmeForge SRS, puts the standards PDF in `shared` via its Slo tags, refuses a scope for personal notes; the duplicate PDF stays in staging; the revision comes in as CHANGED v2 naming the entities to re-extract.

### Phase 3: Extract knowledge (OKF)
Extraction turns the tagged chunks of a new or changed `DocStore` file into facts through the entity savers. No LLM writes the database.

**OKF v0.2 metadata in `KnowledgeFacts`** (spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md; a verbatim copy is in `docs/okf/SPEC.md`). OKF describes a fact's metadata only; the content is the structured JSON defined by the entity model and validated by its saver. The metadata columns are all derived by the base saver, none hand-written:

| Column | Meaning |
|---|---|
| `FactType` | OKF `type`: the entity model name in words, e.g. `Application Overview` |
| `Title`, `Description` | OKF `title` and the one-sentence `description` |
| `Tags`, `Sources` | OKF `tags` and `sources[]`, each a JSON list |
| `YmlFrontmatter` | The same OKF metadata rendered as YAML text (derived from the columns above plus trust and lifecycle, with the producer-defined `fact_key`, `version`, `completeness`). `FactKey` is the id and `Value` is the content |
| `GeneratedBy`, `GeneratedAt` | Trust: OKF `generated {by, at}` |
| `Verified` | Trust: OKF `verified [{by, at}]`, stored as a JSON list; empty = unverified |
| `Status` | Lifecycle: `draft` \| `stable` \| `deprecated` |
| `StaleAfter` | Lifecycle & freshness: ISO 8601 instant; stale when now >= `StaleAfter` |

- `sources[]` (`resource` required, `id`, `title`, `last_modified`) point at the `DocStore` files the fact came from; actors follow the convention `<producer>/<version>` (agents), `human:<id>`, `process:<id>`. Bundle files, links, `index.md` and `log.md` are not used.
- **Hash and Version cover `Value` only.** A save with the same `Value` but different metadata is `UNCHANGED`: no version bump, the metadata columns and `YmlFrontmatter` are refreshed in place. `KnowledgeFactsHistory` (`FactKey`, `Hashcode`, `Version`, `Timestamp`, `GeneratedBy`; PK `FactKey, Version`) gets a row on every `UPDATED`.
- **Caller-supplied judgment fields** travel in `FactMeta` (`title`, `description`, `tags`, `sources`, `generated_by`) and `FactSource`; everything else is derived. A new or changed value is always `draft`, unverified, `generated.at` = now; without `meta` the actor is `docfactory/unspecified` and the title is the key. Seeded facts use `SEED_META` (`generated.by` = `seed`).
- **Trust rule:** LLM output is always `draft` with `generated.by` = `okf-extraction-agent/<model>`, set by code. Only a human approval (Phase 5) adds `verified` with a `human:<id>` actor and promotes to `stable`.
- **Fact views:** after every successful entity save (also on `UNCHANGED`, so a deleted file comes back) the JSON value is written to `knowledgefacts/<scope>/.../<Entity>.json`, and next to it `<Entity>.missing.md` lists every scored field still at its default: field path, question, and the default assumed until answered (list item fields once per field, 'missing in k of n items', followed by those items, each named by its mandatory fields, e.g. `FR-01 | Login | The system SHALL ...`, cut at 120 characters). Deterministic (`open_questions.py`, `missing_md.py`), by the same rule as completeness (a test checks the questions account for exactly the unanswered part of every sample's score). A fact with no open question has no file. Open questions are computed on demand and never stored in `KnowledgeFacts`.
- One key is one aggregate per entity (e.g. all SOP procedures in `<App>.Sop`); one key per item would need new key patterns and is not decided.

**Extraction flow** (`extract/extraction_pipeline.py`):
- **Per entity, per batch, one tool.** For each entity tagged in a `DocStore` file, its chunks are packed in document order into batches of up to `BATCH_CHARS` = 3500 characters (chunks never split). Each batch is one fresh `AgentLoop` (`EntityExtractor`) with exactly one tool, `submit_extraction(values, summary)`, that sees only the entity's meaning and that batch. `values` is a **partial object**: the entity model with every top-level field optional (`partial_schema`, built with `create_model`); list items keep their mandatory fields.
- **The tool checks, code decides.** `submit_extraction` refuses, with feedback the model acts on: invalid values (`SaveError`s with field description and question), placeholder text such as `N/A: not mentioned` (leave the field out), two items sharing an identifier, and item identifiers not found in the batch text. It strips trailing punctuation from identifiers (`FR-01.` -> `FR-01`). It writes nothing.
- **A failed batch of several chunks is split in half and retried**; a failed single chunk is reported and the contribution keeps no chunks hash, so the next run retries. One failed batch never stops the others.
- **Facts merge across documents (user decision).** Several documents may contribute to one fact, so extracting one document never wipes what others gave. `FactContributions` (`FactKey`, `Resource` = DocStore path, `Value` = canonical JSON of what that file states, `Hashcode`, `ChunksHash`, `Description`, `GeneratedBy`, `Timestamp`; PK `FactKey, Resource`) is derived extraction data. The fact = deterministic merge of all its contributions (`extract/merge.py`): newest DocStore file first; scalars first non-empty, a different value elsewhere is a reported conflict; string lists unioned (case and spacing ignored); model lists unioned by the item's identity field (its first mandatory field: `id`, `name`, `title`, `role`; a test pins one for every item model), same-identity items merged field by field. Batches of one file merge with the same rules. A CHANGED file replaces only its own contribution, so an item removed from it disappears unless another file states it. A fact stored before any extraction (seeds) is the lowest-precedence contribution `(existing)`.
- **Skips and removals.** Unchanged `ChunksHash` = `SKIPPED_UNCHANGED_CHUNKS`, no LLM call (`--force` overrides); this is how a CHANGED file re-extracts only its changed entities. An entity no longer tagged in a file loses that file's contribution and the fact is re-merged (`REMOVED`). A merged fact the saver rejects (e.g. an overview without `purpose`) is `REJECTED` but the contribution is kept for a later document.
- **Scope rule (user decision).** The key comes from the DocStore folder: `<App>.<Entity>`; `Slo` / `Kpis` (savers with only `Shared.` keys) come only from files in `DocStore/shared/` (an application document never overwrites a common standard); `general/` gives no facts. Component keys are not derived.
- **Metadata.** Code derives `title` ('<scope> <entity in words>'), `tags` ([entity, `extracted`]), `generated_by` and `sources` (every contributing file with its DocStore timestamp); `description` is the newest contribution's one-sentence summary from the model.
- **Priorities from keywords (user decision).** A requirement item whose priority the model left empty gets the one its own statement states: SHALL / MUST / REQUIRED -> MUST, SHOULD / RECOMMENDED -> SHOULD, MAY / OPTIONAL (capitals only) -> COULD, strongest keyword winning; the model's own priority is never changed (`extract/priority_keywords.py`).
- **Report** (`EntityExtractionReport`, outcomes in `ExtractionOutcome`): key, outcome, version, completeness, chunks, batches, failed batches, items, priorities from keywords, contributing files, batch problems, conflicts, values not grounded in the text (identifiers and model-written titles excluded), missing-info questions (`extract/missing_questions.py`, which also covers a merged value the saver rejects), save errors.
- **Prompt:** `.claude/agents/docfactory-entity-extractor-agent.md` (fill only what the chunks state, the document's wording and identifiers, text under a numbered item stays in that item).
- **Entry point:** `python -m docfactory.agents.run_extraction "<DocStore path>" [--entity <Entity> ...] [--force]`.

**Verified** (`gemma4:31b` on Ollama Cloud, default `DOCFACTORY_NUM_CTX`): the real 50-page SRS gives 186 functional requirements (all 172 non-empty FR identifiers plus unnumbered items; FR-47/48 are empty rows in the PDF) and 165 non-functional requirements (all 162 NFR identifiers), plus ApplicationOverview, Architecture, BackupRecovery, Environments and Monitoring; Slo is skipped by scope; the whole file takes about 5.5 minutes with no failed batch, and a second run makes no LLM call. `pytest -m live tests/test_live_extraction.py`: the corpus SRS gives its three requirements; its revision updates `FunctionalRequirements` to v2 and skips unchanged entities.

**Open review points** (Phase 5 territory): near-duplicate list entries that differ in wording are not merged; chunks the ingestion fallback tagged with doubtful entities (real SRS 4.1 User Interfaces, 6.1, 6.3 as FunctionalRequirements) yield unnumbered items; on the real SRS, `Environments` items are named after requirement headings (Technical, Hardware, Software) and `Monitoring` alerts after requirement IDs (NFR-44, NFR-134).

### Phase 4: Generate
Generation **groups the stored fact JSON by the document template, writes the `.md`, maintains the document control and revision history, and writes the needs list for what is missing.** No retrieval and no generating agent: every document field's binding (`<Entity>.<field>`) already says which fact fills it, and copying keeps every value exactly as the facts state it. One small, checked LLM call phrases the needs list.

**Templates.** A template is a document body model in `documentmodels/documents/` composed of `entitybound/` sections; each section field is bound to `<Entity>.<field>`. The four templates are Overview, SMTD, SRS (ApplicationOverview, FunctionalRequirements, NonFunctionalRequirements, `Shared.Slo`) and SOP; `docfactory/generation/doc_types.py` lists each with its body saver and document name.

**Flow per `<App> <DocType>`** (`generation/generate_document.py`):
1. **Group** (code): `build_document` reads `<App>.<Entity>` and `Shared.<Entity>` and copies every answered bound field into the body, in the template's order. Nothing is rewritten, summarised, merged or invented. An absent or incomplete fact still gives a document: its fields render as `_Not provided._` and reach the needs list.
2. **Save the body** through its document saver as `<App>.Outputs.<DocType>` (`UNCHANGED` when the facts did not change).
3. **Document control and revision history** (code, below), saved as `.DocumentControl` and `.RevisionHistory`.
4. **Gaps** (code, below), then the **needs list** (one checked LLM call, below), saved as `.MissingInfo`.
5. **Render** `output/<App>/<DocType>.md` (`render_markdown`) and `output/<App>/<DocType>.missing.md` (`render_needs_markdown`; removed when there is no gap). A file whose bytes are unchanged is not rewritten.

**Document control and revision history (user decisions).** Both are maintained by the generate process; no input comes from `KnowledgeFacts`. Their fields have `binding="caller"`, so `build_document` never fills them.

| Field | Value |
|---|---|
| `document_id` | `<App>-<DocType>` |
| `title` | the application and the template's document name, e.g. `AI-Driven-Job-Matching-Platform Software Requirements Specification` |
| `document_version` | `0.<body Version>` while the document is a draft |
| `status` | `Draft`; a status already in the stored row is kept (the Phase 5 approval sets it) |
| `owner` | always the system: `docFactory` |
| `approvers` | kept from the stored row; empty until the Phase 5 approval adds the person who reviewed it. Not a needs-list question |
| `created_date` | the date of the first generation; kept on later runs |
| `last_updated_date` | the date the body last changed (`CREATED` / `UPDATED`) |

`RevisionHistory` gets one `RevisionEntry` per body save that is `CREATED` or `UPDATED`, or when no history row exists yet; an `UNCHANGED` body adds none. `version` = the new `document_version`, `date` = today, `author` = `docFactory`, and a `summary` written by code: 'Generated from <key> v<n>, ...' (facts not stored yet are named '(not available)'), or 'Changed sections: <section> (from <key> v<n>)'. Existing entries are kept.

**Gaps** (`generation/gaps.py`): the template's fact-bound fields in template order (`build.bound_fields`). A bound field whose fact is absent, or whose source field is unanswered, is one gap. A bound field that is answered and holds a nested model or list of items adds the fact's `open_questions` under it, re-pathed to the document field, with 'missing in k of n' and at most 3 example items. Only fields the template binds count. Gaps are numbered 1..n; `gaps_hash` is the SHA-256 of their canonical JSON.

**The needs list** (`<App>.Outputs.<DocType>.MissingInfo`, saver `MissingInfoSaver`): `gaps` (`DocumentGap`: `number`, `field`, `question`, `expected_source`, `missing_in`, `item_count`, `example_items`), `needs` (`DocumentNeed`: `question`, `audience`, `gaps`, at least one gap number; list order = priority), and the unscored `gaps_hash` and `needs_origin` (`NeedsOrigin`: `llm`, `fallback`, `no_llm`).
- **One LLM call** (`agents/needs_writer.py`, `NeedsWriter`; fresh context, single tool `submit_needs`, package `generation-needs`; prompt `.claude/agents/docfactory-needs-list-agent.md`) sees the application, the document name and the numbered gaps, and turns them into needs: related gaps merged into one question, phrased in the application's terms, grouped by who can answer (e.g. product owner, architect, operations, service owner), most important first.
- **Code checks** the answer and feeds errors back: every gap covered by at least one need, no unknown gap number, every need cites a gap and names an audience. Only gaps reach the list, so no question is invented.
- **Skip and fallback:** unchanged `gaps_hash` and a stored list from the LLM (or from the same mode) = no call. A failed call saves one need per gap (`fallback`) and is retried on the next run; `--no-llm` does the same (`no_llm`). No gaps = no call and no `.missing.md`. Neither the document nor its needs list is ever blocked.
- **Not stored per fact (decided):** a fact's questions are derived data that would go stale when the model's questions change, and the needs list belongs to a document (it merges facts and depends on the template). A fact's own questions stay in `knowledgefacts/.../<Entity>.missing.md`.
- `render_needs_markdown` lists the needs by audience (numbered in priority order across groups), each with the gaps it covers, then every gap with its source and examples.
- Answers re-enter as new or changed source documents in `incoming/` (Phase 2 > 3 > 4 again), never as edits to an output.

**Report** (`GenerationReport`): per document the body action, version and completeness, the document version, the revision entry added, the number of gaps and needs, where the needs came from (and the fallback reason), the files written, and any save errors.

**Entry point:** `python -m docfactory.generate <App> <Overview|SMTD|SRS|SOP|all> [--no-llm]`. An application with no facts is refused with the list of applications that have facts.

**Verified** on the real AI-Driven-Job-Matching-Platform SRS (`gemma4:31b`): Overview 70% (3 gaps -> 2 needs), SMTD 34% (42 -> 14), SRS 66% with all 186 FR and 165 NFR rows (11 -> 8), SOP 48% (12 -> 5), all needs lists from the LLM, about 35 seconds for all four; a rerun changes no row, writes no file and makes no LLM call. `pytest -m live tests/test_live_generate.py` covers the needs call on a small SRS.

### Phase 5: Human in the loop
- The approval gate becomes a workflow: **agents propose, humans approve, tools apply.** It is built with **LangGraph**, used for orchestration and its **checkpointing** (durable state, `interrupt` to pause for a human, resume with the decision). LangGraph is introduced here and only here; it does not replace the tool layer (Principle 9).
- Graph nodes call the registry tools. Proposals (a classification, a fact payload, a generated document) are held in the checkpoint, not written to the database. Only after approval does the node call the saver. Rejection returns feedback to the agent.
- The human approval adds `verified` with a `human:<id>` actor and promotes `draft` to `stable`, and sets a document's status and approvers.
- To design in Phase 5: which steps need approval (classification, facts, documents), the checkpoint store (SQLite, kept apart from `docfactory.sqlite`), the approval interface (CLI first), the timeout and escalation rule for pending approvals, and the review of the open extraction points.

### Phase 6: Automate
- A watcher for `incoming/`, automatic triggering, and the end-to-end workflow: ingest, extract, approve, generate, render. Triggers become automatic; the approval gate from Phase 5 stays.
- To design in Phase 6: the watcher, the trigger rules (new or changed file, stale fact, changed fact -> regenerate the affected documents), failure and retry handling, and monitoring of runs.

## Working rules

- Read this file first. When something is unclear, ask the user.
- One class per file, in the right folder (Principle 1). Create models and savers through the `docfactory-pydantic-developer-agent`.
- Write to the database only through the tools. Never edit generated documents, `knowledgefacts/` files or `DocStore/` files by hand; change the models or documents and regenerate.
- Changing a model changes stored data's meaning: say so and update the tests and golden files in the same change.
- Descriptions on models and fields are part of the product: write them for an LLM reader (meaning, example of a good value, what to ask if missing).
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes.
- The repo has mixed line endings and no conversion (`* -text`): keep each file's existing line endings when editing.
- Keep the repo in git so data-shape changes are diffable; build step by step, with the user's review between steps.
