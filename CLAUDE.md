# docFactory (Pydantic approach)

Keeps application documentation (Overview, SMTD, SRS, SOP) up to date from structured knowledge. Knowledge is held as an **OKF bundle**: plain Markdown concept files (OKF v0.2 frontmatter + the Pydantic-validated JSON of the fact in the body). Documents are **composed Pydantic objects** rendered to Markdown by deterministic code. There is no database.

## Status

- **Phase 1 (DONE, closed 2026-10-03): the deterministic core.** Seed data -> validated facts -> composed document objects -> `.md` files. No LLM. Everything is unit-testable.
- **Phase 2 (DONE, closed 2026-10-03): Ingest.** Original files (text, PDF, Word, HTML) arrive in `incoming/`, move to `staging/`, are chunked deterministically from the raw file, tagged with entities against an ontology (rules first, a small LLM fallback for what the rules cannot tag or place) and stored in the bundle as `<scope>/references/<file>` with a Source concept (`<scope>/sources/<file>.md`: hash, version, chunk outline and tags) (see "Phase 2: Ingest").
- **Phase 3 (DONE, closed 2026-10-04): Extract knowledge (OKF).** Per entity tagged in an ingested file, its chunks go in small batches, one fresh single-tool LLM call per batch returns a partial object; code checks, merges (batches, then every contributing file via contribution concepts) and writes the fact's concept file through `BundleStore` (see "Phase 3: Extract knowledge (OKF)").
- **Phase 4 (DONE, closed 2026-10-07): Generate.** For an application and a document template, code groups the stored fact JSON by the template's bindings into the document body, maintains the document control and revision history, keeps them as state files and renders `output/<App>/<DocType>.md`. One small, checked LLM call turns the deterministic gaps into the document's needs list (rendered to `<DocType>.missing.md`) (see "Phase 4: Generate").
- **OKF bundle redesign (DONE, 2026-10-11): the bundle replaces SQLite.** Facts, sources and contributions are OKF concept files; the generated documents' state is JSON files in `output/<App>/state/`. The savers, `db.py` and every table are gone (see "The bundle").
- **Phase 5 (PENDING, outline only): Human in the loop.** The approval gate as a workflow (agents propose, humans approve, tools apply), built on LangGraph checkpointing and interrupts.
- **Phase 6 (PENDING, outline only): Automate.** A watcher for `incoming/`, automatic triggering and the end-to-end workflow.
- **Next activity: optimize the generation flow.** Today generation scans the bundle straightforwardly: for each binding of the template it reads the fact's concept file, extracts the JSON under `# Value`, checks its hash, parses it into the entity model and aligns the bindings with the objects (`build.load_fact`, one read per fact per run through the caller's cache). Measure it on a large bundle first, then optimize (for example an in-memory index of facts by key, parse-once caching across documents, skipping unchanged files by hash).
- **Triggers are manual until Phase 6:** files are moved into `incoming/` and the user runs each step by hand. `README.md` explains the process and lists the commands.

Nothing described here exists until it appears in the repo. If something is unclear, ask the user before coding.

## Principles

1. **Single Responsibility (strongest rule).** Every class lives in its own file, and every module has one reason to change.
   - Every Pydantic class, including small nested item classes, is in its own file. Entity models go in `docfactory/entitymodels/facts/` (facts, registered in the fact registry) or `docfactory/entitymodels/items/` (nested items and enums, not registered), document models in `docfactory/documentmodels/`, common and shared models in `docfactory/models/`.
   - The file is named after its class in snake_case (`ApplicationOverview` -> `application_overview.py`). A module never defines two classes; a function module defines none.
   - A class does one thing: a model describes and validates data, a store writes and reads files of the bundle, the renderer renders. None of them does another's job.
   - Tests enforce the file and naming rule (see "Tests").
2. **The facts in the bundle are the source of truth.** A fact is the concept file `<Scope>/<Entity>.md`; its JSON (under `# Value`) is its content, the frontmatter around it is OKF metadata. Generated documents are views of facts, never the other way round. `.md` files under `output/` are views too (written for visibility), never edited by hand.
3. **Only valid data is stored.** Every write goes through a Pydantic model. Invalid input is rejected with a structured error and nothing is written.
4. **Models are the contract.** Every model and field has a description written for an LLM: what it means, what a good value looks like, what to ask when it is missing. The same model is the validator, the LLM's tool schema and the documentation.
5. **Deterministic code does all the work that can be deterministic:** validation, canonical JSON, hashing, completeness, merging, composition, document control, revision history, rendering, moving files. An LLM only does judgment work: tag what the rules cannot tag, pick a scope the rules cannot pick, find the information in a batch of chunks, and phrase a document's gaps as a needs list. Every LLM call has exactly one tool, and code checks its answer.
6. **Never invent values.** A default is a placeholder, not knowledge. Completeness counts only what was actually answered. Do not fill fields to raise a score.
7. **Errors are feedback.** A rejected call returns errors precise enough for a caller (test or LLM) to fix the payload or go and find the missing information.
8. **Only the stores write.** `BundleStore` (facts), `SourceStore` (sources), `ContributionStore` (contributions) and `DocumentStateStore` (document state) are the only writers of their files, plus the ingestion pipeline's moves of originals. No hand-edited facts, sources, contributions, state files or generated documents: a file whose JSON no longer matches its stored hash is refused on read. New input arrives only as files in `incoming/`.
9. **The tool layer is plain in-process Python function tools.** The tools an LLM call uses are ordinary Python functions with typed arguments, collected in an in-process registry. No MCP server, no framework-specific tool classes. The tool schema is derived from the Pydantic models (Principle 4). Agent loops and any orchestration framework (LangGraph in Phase 5) only call these functions; they never contain business logic, so the tool layer is testable without an LLM and survives a change of runtime.
10. **Least privilege for agents.** Every LLM call is given only the tools it needs, nothing more. Tools are grouped in **tool packages**, one package per kind of call (ingestion tagging, ingestion scope, extraction, generation needs), and a call can reach only the tools of its own package. File operations are deterministic code that no agent controls; no agent gets a shell or a general file system. A test pins each package's exact tool list, so a tool cannot be added unnoticed.

## Data flow

```
incoming/ -> staging/ -> chunk + tag (ontology rules, LLM fallback) (Phase 2) -> bundle/<scope>/references/<file>  (the original)
                                                                                 bundle/<scope>/sources/<file>.md  (Source: hash, version, chunk outline, tags)
                                                                                        |
        one small LLM call per batch of an entity's tagged chunks (Phase 3)  <----------/   (chunks are re-derived from the original)
                                   |
                                   v
            bundle/<scope>/sources/<file>/<Entity>.md   one contribution per file and entity --merge--\
seed data (Phase 1) ---------------------------------------------------------------------------------->-- BundleStore.write_fact --validate-->
                  bundle/<Scope>/<Entity>.md   (OKF frontmatter + JSON value + open questions), bundle/index.md, bundle/log.md
                                                                                        |
            document template (YAML file, bindings <Entity>.<field>)                    |  (Phase 4)
                                                                                        v
        scan the bundle --> read each bound fact's file --> JSON --> entity objects --> build_body --> body;
        code --> DocumentControl, RevisionHistory --> output/<App>/state/<DocType>.<part>.json (DocumentStateStore)
        gaps (unfilled fields + open questions of bound fields) --one checked LLM call--> needs list (state file)
                                                                                        |
              render_document_markdown --> output/<App>/<DocType>.md        needs list --> output/<App>/<DocType>.missing.md
```

## Models

One Pydantic v2 model per file, in three folders. `models/` and `documentmodels/` are flat; `entitymodels/` has two sub-folders, `facts/` and `items/`:

| Folder | Holds | Examples |
|---|---|---|
| `docfactory/entitymodels/facts/` | **EntityModels that are knowledge facts**: every entity model registered in `docfactory/bundle/fact_registry.py` | `ApplicationOverview`, `Architecture`, `Environments`, `FunctionalRequirements`, `NonFunctionalRequirements`, `Slo`, `Kpis` |
| `docfactory/entitymodels/items/` | **EntityModels that are nested items and enums**: every entity model that is not a fact | `Environment`, `Requirement`, `Alert`, `Component`, `RequirementPriority` |
| `docfactory/documentmodels/` | **DocumentModels**: the parts every generated document has (the body `DocumentBody`, document control, revision history, the needs list) | `DocumentBody`, `DocumentControl`, `RevisionHistory`, `MissingInfo` |
| `docfactory/models/` | **Machinery models**: reusable building blocks of the system itself, independent of any application knowledge. They make the code work; they hold no information about an application | the base model, `doc_field`, `NotApplicable`, `SaveAction`, `SaveResult`, `SaveError`, `FactMeta`, `SourceRecord`, `FactContribution`, the run reports |

**The dividing line:** `models/` is for machinery (how the system validates, stores and reports). Anything that describes information about an application or its environment, including a small nested item type such as `Alert`, `Component`, `Environment` or `Integration`, is an entity model and lives in `entitymodels/` (`facts/` when it is registered, else `items/`; nothing sits directly in `entitymodels/`), even when it is never stored on its own and even when a document section also uses it. Document models import entity models where they need them (today none does); the reverse never happens. `models/` never imports `entitymodels/` or `documentmodels/`.

**Document models.** The parts every generated document has, written by the generate process: `DocumentBody` (the generic body filled from a template), `DocumentControl`, `RevisionHistory` and its `RevisionEntry`, `MissingInfo` (the needs list) and its `DocumentGap`, `DocumentNeed`, `NeedsOrigin`. A document type is not a model but a YAML template over entity facts (see "Documents"), so there is no body model or section class per document type.

- An entity is an **aggregate**: list-like content (requirements, environments, components, SLOs) is a list of typed item models inside one object.
- All models derive from one base model (`docfactory/models/`, its own file) that sets `extra="forbid"` (a hallucinated field is an error) and requires a description on every field (enforced by a test).
- **Mandatory fields are the absolutely necessary ones only** (what identifies the object or makes it meaningless). Everything else has a default where a default is legitimate (`None`, empty list, empty string). If no honest default exists, the field is mandatory. **Fields of a document template's bound facts are never required by the document**: a fact that is not there yet is a gap, not an invalid document.
- Field metadata beyond the type (`doc_field`): `description` (meaning and what a good answer contains), `question` (asked when the field is missing; defaults to the description), whether `N/A` is a legal answer (`na_allowed`), `scored` (default true), `render_as` (`list`, `numbered`, `table`), and the constraints `min_length`, `max_length`, `ge`, `pattern`.
- Two kinds of knowledge fact, distinguished only by scope in the key:
  - **Common** to all applications: `Shared.Kpis`, `Shared.Slo` (AppID NULL).
  - **Application-specific:** `ReadmeForge.ApplicationOverview`, `ReadmeForge.Architecture` (AppID = `ReadmeForge`).
- **Output-specific** content (document control, revision history, needs list) is not a knowledge fact. It belongs to one generated document and lives in its state files (see "Documents").
- Models are Python code, versioned by git. There is no schema-version in the files: a fact file whose JSON no longer validates against its model is reported when read, never loaded silently.

## The bundle (`bundle/`, override with `DOCFACTORY_BUNDLE`)

The bundle is an OKF v0.2 bundle (spec: `docs/okf/SPEC.md`): a directory of Markdown concept files with YAML frontmatter, readable with `cat` and diffable in git. `bundle/` is gitignored runtime data in this repo; put it in its own git repository to keep the history of old values (the bundle itself keeps only the current value; `log.md` records each change).

```
bundle/
  index.md                          okf_version "0.2"; the facts listed by scope (generated)
  log.md                            one dated line per creation, update, removal (OKF section 9)
  Shared/Kpis.md  Slo.md            common facts
  <App>/ApplicationOverview.md ...  application facts, one concept file each
  <App>/Components/<c>/<Entity>.md  component facts
  <App>/references/<file>           the ingested originals (OKF "references/")
  <App>/sources/<file>.md           Source concept of an original
  <App>/sources/<file>/<Entity>.md  Contribution concept: what that original stated about the entity
  <App>/sources/(existing)/<Entity>.md   a fact value stored before any extraction (e.g. seed data): lowest-precedence contribution
```

**Fact concept file** (`BundleStore`, `docfactory/bundle/`): frontmatter with the OKF fields (`type` = the entity name in words, `title`, `description`, `tags`, `sources[]`, `generated {by, at}`, `verified[]`, `status`, `stale_after`) and the producer keys `fact_key`, `version`, `completeness`, `hashcode`; then `# Value` with a fenced `json` block (the validated object in model field order); then `# Open questions` (the fields still at their default, with the question and the assumed default; absent when none). The JSON block is the truth.

Rules enforced by code:
- `AppID` is NULL exactly when the key scope is `Shared`; otherwise it equals the key's first segment, case-sensitive. The key must match one of the key patterns of its entity (`fact_registry.key_patterns_of`: `<App>.<Entity>` and `<App>.Components.<Component>.<Entity>`, or `Shared.<Entity>` for `Slo` and `Kpis`). Key segments become folder and file names, so an unsafe segment is rejected (`key_unsafe_path`).
- **The whole object is saved, and only when its hash differs.** Identical `hashcode` (SHA-256 of the canonical JSON: sorted keys, no extra whitespace, UTF-8) = `UNCHANGED`: value, version and completeness are untouched (a save with `meta` refreshes title, description, tags, sources and `stale_after` in place, still without a version bump). A different hash replaces the value, recomputes `completeness` and sets `version + 1`. First write is version 1. A deleted file is a deleted fact: saving again creates it at version 1. There are no partial updates: a caller sends the complete object.
- **Reading re-validates.** `read_fact` parses the JSON block into the entity model and compares its hash with `hashcode`; a mismatch (the file was edited outside the system) or invalid JSON is a `BundleError`, and a save over such a file is rejected (`bundle_file_untrusted`).
- Writes are atomic (temporary file + replace) and skipped when the bytes are unchanged. `index.md` and `log.md` are updated by the stores.
- **Trust:** a new or changed value is always `draft`, unverified, `generated.at` = now; `generated.by` is the caller's actor (`<producer>/<version>`, `human:<id>`, `process:<id>`), without `meta` it is `docfactory/unspecified`. LLM output is `okf-extraction-agent/<model>`, set by code. Only a human approval (Phase 5) adds `verified` with a `human:<id>` actor and promotes to `stable`.
- **Multi-component applications:** each component has its own keys, `<App>.Components.<Component>.<Entity>`, e.g. `ReadmeForge.Components.api.Architecture`. `AppID` is still the application. Component keys reuse the same models; the component name is free text. Extraction works at application level and does not derive component keys.
- Key examples: `ReadmeForge.ApplicationOverview`, `ReadmeForge.Architecture`, `Shared.Kpis`.

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

## Stores

Plain Python, no framework. Everything is deterministic and callable from tests, seed scripts and pipelines; no LLM calls a store directly (see "Tool layer"). Each store is one class in its own file.

- **`BundleStore`** (`docfactory/bundle/bundle_store.py`): `write_fact(key, payload, meta=None) -> SaveResult` does, in order: check the key against the fact registry (`key_check`), validate with the entity model, canonical JSON + SHA-256, read the existing file (same hash -> `UNCHANGED`; none -> `CREATED`; else `UPDATED`), completeness, write the concept file, append `log.md`, refresh `index.md`. `read_fact(key)`, `list_facts(app_id=None)`, `list_facts_by_source(resource)`. `meta` (`FactMeta`: `generated_by`, `title`, `description`, `tags`, `sources`, `stale_after`) carries the judgment fields; everything else is derived.
- **`fact_registry.py`** (`FACT_SPECS`): the facts a bundle can hold, entity name -> model and whether it is shared. Adding a fact means adding an entry (done by the `scaffold_model.py --scope` script). `fact_keys.py` and the ontology read it too.
- **`SourceStore`**: the Source concepts. `write(resource, hashcode, timestamp, chunks, tags)` returns `(version, the record before)`: no earlier Source = version 1, same hash = the version stays (a repair or re-tag), another hash = +1. `read`, `list(scope=None)`, `find(file_name=, hashcode=)`.
- **`ContributionStore`**: the Contribution concepts. `save(key, resource, value, chunks_hash, description, generated_by, timestamp)`, `get`, `list(key=, resource=)`, `remove`. Reading checks the JSON against its `hashcode`.
- **`DocumentStateStore`** (`docfactory/generation/`): the state files of the generated documents (see "Documents"), the same save rules as a fact.
- Return value of a save is always a `SaveResult` model, never an exception for bad input:

```
SaveResult { ok, key, action: CREATED|UPDATED|UNCHANGED|REJECTED, version, hashcode, completeness,
             errors: [ SaveError { path, message, error_type, received, expected, field_description, question } ] }
```

- On `REJECTED` nothing is written. Each error carries the Pydantic message plus the field's description and question (`validation_errors.py`), so the caller knows what to fix or what to find out.
- Corrupt or tampered files raise `BundleError` on read (a fact, source, contribution or state file edited outside the system).

## Documents

- A document type (Overview, SMTD, SRS, SOP) is a **YAML template**, `docfactory/generation/templates/<DocType>.yaml` (relocatable with `DOCFACTORY_TEMPLATES`), validated by one generic model (`DocumentTemplate` > `TemplateSection` > `TemplateField`). A document is a view of facts: every value in it was already validated by its entity model, so the document layer only chooses which fact fields appear, in which order and format. A new document type is a new YAML file; no model, store or generation code.
- Each template field declares its **binding** `<Entity>.<field>` (which fact field supplies it) and optionally a `label`, a `render_as` (`list`, `numbered`, `table`) and a `question` (asked when the field is missing; defaults to the entity field's question). A wrongly wired template (unknown entity or field, duplicate id or binding, bad `render_as`) raises `TemplateError` when it is loaded.
- `build_body.build_body` is deterministic: it reads the app's facts and the shared facts through `build.load_fact` (the one seam between generation and the bundle) and copies every answered bound field (as canonical JSON in `DocumentField.value`, status `answered`, else `missing`) into a `DocumentBody`. It does not invent content and never fails on a missing fact.
- **Every output document is four state files** in `output/<App>/state/`, each a validated Pydantic object with its own hash, completeness and version (`DocumentStateStore`, file `<DocType>.<part>.json`, key `<App>.Outputs.<DocType>[.<Part>]`):
  - `body` (`<App>.Outputs.<DocType>`) - the document body (all sections), **without** document control and revision history. Built from the knowledge facts. Its completeness = answered bound fields / all bound fields.
  - `control` (`.DocumentControl`) - document id, title, version, status, owner, approvers, dates. Never from knowledge facts: maintained by the generate process (the ReadmeForge seeds supply their own).
  - `history` (`.RevisionHistory`) - the list of revisions (version, date, author, change summary). Never from knowledge facts: maintained by the generate process (the seeds supply their own).
  - `needs` (`.MissingInfo`) - the needs list: the document's gaps and the questions to ask for them (see "Phase 4: Generate").
  Each file holds `key`, `version`, `hashcode`, `completeness` and the `value`; they are system-written, never hand-edited (a mismatching hash is refused on read).
- `render_document_markdown` assembles the final `.md` from the body, document control and revision history (order: document control, revision history, body); it refuses with a clear `RenderError` when a part is missing. `render_document_needs` renders the needs list to `<DocType>.missing.md`. Same state in, same bytes out. The `.md` files under `output/<App>/` are views and never truth.

## The `docfactory-pydantic-developer-agent`

All models and fact registrations are produced through a specialized agent, `.claude/agents/docfactory-pydantic-developer-agent.md`, built around the principles above, so they come out uniform.

- **The agent** knows and enforces: single responsibility (one class per file, file name = snake_case of the class, correct folder), the base model, descriptions and questions on every field, honest defaults and minimal mandatory fields, typed lists and no `dict`/`Any`, `NotApplicable` only where `na_allowed`, scoring rules, and that a fact is registered in `fact_registry.py` and gets its tagging signals. It writes a test with every class it creates and runs the suite before it reports done.
- **Entry skills** (in `.claude/skills/`, invoked as `/docfactory-<task>`; **every skill and custom agent in this project is named with the `docfactory-` prefix**, enforced by a test), one per repeatable task, each pinning the agent and model (`context: fork`, `agent: docfactory-pydantic-developer-agent`, `model: sonnet`) and defining the exact step-by-step procedure: `docfactory-create-shared-model` (base classes and package skeleton, or one shared model), `docfactory-create-entity-model` (a fact or an item), `docfactory-add-field`, `docfactory-review-models`. Two reference skills (`docfactory-field-spec`, `docfactory-quality-gate`) are preloaded into the agent. Skills cannot be `.claude/commands/` files: only skills support `agent` and `context: fork`.
- **Deterministic scripts** (`.claude/scripts/`, tested in `tests/scripts/`): the agent supplies judgment as a JSON spec; scripts resolve names and paths, generate models and their tests, register facts in the fact registry (`registry_edit.py`) and write the fact's `BundleStore` test (`render_fact_test.py`), add fields, check structure and run the quality gate. Conventions the generated code relies on (base model `DocFactoryModel`, field helper `doc_field`, the registry file, key-pattern placeholders) are in `.claude/scripts/conventions.py`. The spec scripts do not yet emit the `ge` and `max_length` constraints of `doc_field`; write those by hand. They scaffold entity and shared (`models/`) models; there is no document-model kind, because a document body is a YAML template.
- The agent never edits the bundle or generated documents by hand, and never invents field content.

## Sample data

- **ReadmeForge** (the Phase 1 sample application): hard-coded seed scripts in `seed/` save its facts from `samples/json/<entity>/` through `BundleStore` and store and render its four documents (to `output/ReadmeForge/`, state in `output/ReadmeForge/state/`) with their own document control and revision history. The golden files in `tests/golden/` are rendered from small TestApp facts by `tests/test_golden_documents.py`.
- **AI-Driven-Job-Matching-Platform** (a real 50-page SRS): a committed snapshot of one end-to-end run in `samples/bundle/` (the bundle: the PDF, its Source, seven facts, their contributions, `index.md`, `log.md`) and `samples/output/` (the four generated documents and their needs lists). Copies for reading; the code never reads them.

## Tests (pytest, every test uses a temporary bundle and temporary folders)

- **Structure:** every module in `models/`, `entitymodels/<facts|items>/` and `documentmodels/` defines exactly one class, named after the file (snake_case); only `entitymodels/` has sub-folders, a class in `entitymodels/facts/` is registered in the fact registry and one in `entitymodels/items/` is not, and `models/` and `entitymodels/` never import `documentmodels/`; every Pydantic class is under `models/`, `entitymodels/` or `documentmodels/`; every field of every registered model has a description; no model contains `dict`, `Any` or untyped list items. In `tools/`, `agents/`, `ingest/`, `ontology/`, `extract/`, `generation/` and `bundle/`, a class module defines one class named after the file and a function module defines none (`tests/test_phase2_structure.py`).
- Facts (`tests/test_bundle_store.py` and one generated `tests/test_<fact>_fact.py` per fact): valid payload -> `CREATED` with canonical JSON, SHA-256, AppID, completeness and `Version = 1`; same payload -> `UNCHANGED` and nothing written; changed payload -> `UPDATED`, `Version = 2`; changing back is a new change (`Version = 3`); key order does not change the hash; component keys store the application's AppID; `Shared.*` stores NULL AppID; a key matching no fact pattern or an unsafe key is rejected; missing mandatory field, wrong type, bad enum, extra field -> `REJECTED`, nothing written, errors with path, description and question (`tests/test_validation_errors.py`); a hand-edited file is refused on read and on write; the files are OKF-conformant (frontmatter parses, `type` present, `index.md` and `log.md` shaped as the spec says).
- Sources, contributions and document state files have their own round-trip, versioning, tamper and listing tests (`test_source_store.py`, `test_contribution_store.py`, `test_document_state_store.py`).
- Completeness: defaults are not answered (even when passed explicitly); a legal `NotApplicable(reason)` is; `N/A` on a field without `na_allowed`, or with an empty reason, is rejected; item-level scoring as above.
- Every JSON file under `samples/json/` validates against the model of its folder, round-trips through a fact file with an identical hash, and every sample folder has a model (`tests/test_samples.py`).
- Build + render of the four documents match the golden files; rendering twice gives identical bytes; a missing fact leaves its field missing and listed as a gap; rendering with a missing control or history part fails with a clear error; the four shipped templates generate with all, some or no facts; a wrongly wired template is refused; a second generation changes no file.
- Ingestion, extraction and generation pipelines are tested with a fake model client; the tool packages' exact tool lists are pinned. Live tests (`-m live`) call the configured LLM and skip themselves when it is unreachable.

## Repo layout

```
.claude/agents/        docfactory-pydantic-developer-agent.md, docfactory-sample-generator-agent.md (development agents); docfactory-chunk-tagger-agent.md, docfactory-scope-agent.md, docfactory-entity-extractor-agent.md, docfactory-needs-list-agent.md (runtime prompts of the LLM calls)
.claude/skills/        Entry skills (docfactory-create-shared-model, docfactory-create-entity-model, docfactory-add-field, docfactory-review-models) and reference skills (docfactory-field-spec, docfactory-quality-gate)
.claude/scripts/       Deterministic scripts the skills call (scaffold, registry edit, add field, check structure, gate)
docfactory/            Python package
  models/              Machinery models, one class per file: base model, doc_field, NotApplicable, SaveAction, SaveResult, SaveError, FactMeta, FactSource, FactVerification, FactRecord, FactStatus, FactQuestion, FactContribution, DocumentRecord, SourceRecord, SourceChunk, DocChunk, ChunkTag, the ingestion, extraction and generation models and reports, the model-client messages
  entitymodels/        EntityModels, one class per file, in two sub-folders:
    facts/             the facts, each registered in the fact registry: ApplicationOverview, Architecture, Environments, Deployment, Monitoring, BackupRecovery, KnownErrors, Sop, Support, Slo, Kpis, FunctionalRequirements, NonFunctionalRequirements
    items/             nested item types and enums: Environment, Requirement, Alert, Component, RequirementPriority, ...
  documentmodels/      DocumentModels, one class per file: DocumentBody, DocumentControl, RevisionHistory, RevisionEntry, MissingInfo, DocumentGap, DocumentNeed, NeedsOrigin
  bundle/              The OKF bundle: fact_registry (FACT_SPECS, key patterns), paths, file_io, key_check, frontmatter_yaml, fact_file_render/parse, source_file_render/parse, contribution_file_render/parse, bundle_log, bundle_index, BundleStore, SourceStore, ContributionStore, BundleError
  canonical.py         canonical JSON + SHA-256
  completeness.py      completeness scoring
  clock.py             now_iso() (tests replace it)
  project_root.py      PROJECT_ROOT
  key_patterns.py validation_errors.py   key-pattern matching; Pydantic errors as SaveErrors with description and question
  build.py             load_fact (the generation seam to the bundle), fact_key, is_answered
  render.py            the Markdown building blocks: field_lines, render_document_control, render_revision_history, needs_markdown, title_of, RenderError
  okf_frontmatter.py   the OKF frontmatter of a fact (type name in words, trust, lifecycle)
  open_questions.py missing_md.py   a fact's open questions (the `# Open questions` section of its file)
  env_file.py          Loads .env into the environment (shell variables win); used only by entry points and live tests
  ingest/              Phase 2 function modules: pipeline (stage, lookup, commit, report), chunking + chunkers/ (pdf, word, html, text), tagging, scope_rules, chunk_rebuild, source_reads (+ ChunksOutOfDateError), paths, file_hash, target_rules. No LLM
  ontology/            signals.json (tagging signals per entity, edited by people), signals.py (validated load), ontology_render.py (docs/ontology.md and the compact LLM summary)
  extract/             Phase 3 function modules: batching (BATCH_CHARS, chunks_hash), fact_keys, partial_schema, model_shapes, grounding, merge, priority_keywords, missing_questions, extraction_pipeline (extract_file, format_reports)
  generation/          Phase 4 (generate a document): the YAML `templates/` (one file per document type), template_loader/check/error, bindings, build_body, generate_document (the flow), template_gaps, gaps, revision_sources, revision_history, document_control, fallback_needs, document_parts (the four parts and their keys), DocumentStateStore, render_document, generation_steps (save_part, choose_needs, write_if_changed, output_dir, format_reports)
  generate.py          Entry point `python -m docfactory.generate <App> <DocType|all> [--no-llm]`
  tools/               Tool, ToolRegistry, ToolPackage (one class per file); the single-tool packages ingestion_tools (submit_chunk_tags, submit_scope), extraction_tools (submit_extraction), needs_tools (submit_needs); schema_slim (inline_refs for tool schemas)
  agents/              ModelClient (abstract), OllamaModelClient (default), AnthropicModelClient (optional), FakeModelClient (tests), model_client_factory, AgentLoop (the shared thin loop), prompt_file, IngestionFallback, EntityExtractor, NeedsWriter; entry points run_ingestion, run_extraction
samples/json/<entity>/ Example JSON payloads per entity (ReadmeForge, plus shared Kpis and Slo), used by the seeds and tests
samples/bundle/ samples/output/   Committed snapshot of the AI-Driven-Job-Matching-Platform end-to-end run
seed/                  Hard-coded seed scripts for ReadmeForge (overview, requirements, SMTD, SRS and SOP); seed_meta.py: SEED_META, the FactMeta (generated_by `seed`) every seeded fact is saved with
tests/                 pytest; tests/golden/ holds the golden .md files, tests/scripts/ tests the .claude/scripts; tests/corpus/ (build_corpus.py, messy originals, a revised SRS, corpus_expectations.json); tests/live_support.py: the live tests' server check
docs/ontology.md       Generated view of the ontology (entities, facts, tagging signals)
docs/okf/SPEC.md       Verbatim copy of the OKF v0.2 spec
README.md              The process end to end and every command to run (keep it in step with the entry points)
STATUS.md              Where the work stands: phase states, runtime state, next steps
.env / .env.example    Local LLM settings (.env is gitignored)
--- runtime data, gitignored ---
bundle/                The OKF bundle (facts, sources, contributions, originals, index.md, log.md)
incoming/              Drop zone for new original files
staging/               Files being ingested, and files waiting for a human decision
output/<App>/          Rendered documents (<DocType>.md), their needs lists (<DocType>.missing.md) and state/ (the documents' state files)
--- planned, do not create until the phase starts ---
docfactory/agents/     Phase 5 adds the LangGraph graph, checkpointer and approval nodes
```

Env `DOCFACTORY_BUNDLE` points the code at another bundle folder (tests use a temporary one). `DOCFACTORY_INCOMING`, `DOCFACTORY_STAGING` and `DOCFACTORY_OUTPUT` relocate `incoming/`, `staging/` and `output/` (tests use temporary folders). LLM settings (from `.env`): `DOCFACTORY_PROVIDER` (`ollama` default, or `anthropic`), `DOCFACTORY_MODEL`, `OLLAMA_HOST`, `OLLAMA_API_KEY`, `DOCFACTORY_NUM_CTX` (Ollama context window, default 16384; enough for every call, whose one tool schema is at most ~1.5k tokens). The model in use is `gemma4:31b` on Ollama Cloud.

Runtime dependencies: pydantic, pyyaml (frontmatter and templates), pdfplumber, python-docx and beautifulsoup4 (the chunkers); `anthropic` is an optional extra; the Ollama client uses only the standard library. LangGraph arrives in Phase 5. Dev only: pytest, reportlab (corpus generation). A dependency is added only in the phase that needs it.

The repo has mixed line endings and no conversion (`* -text`): keep each file's existing line endings when editing.

## Pipeline (Phases 2-6)

**Ingest (move to the bundle) > Extract knowledge (OKF) > Generate documents.** Phases 5 and 6 wrap this pipeline in a human approval gate and then automate it. Each phase is built, tested and closed before the next starts. All steps are run manually until Phase 6.

### Tool layer (Principles 9 and 10)
- **Function tools:** every capability an LLM call may use is a plain Python function with typed arguments and a typed return. All tools today are **answer tools**: they validate the model's answer against a model, return feedback the model can act on, and hand an accepted answer back to the calling code. They write nothing and move nothing; the pipelines write through the stores and move the files.
- **Registry and tool packages:** an in-process registry (`ToolRegistry`) holds tools by name, each with a description written for an LLM and a schema derived from its typed signature. A **tool package** (`ToolPackage`) is a named, fixed list of registry tools; a call is constructed with exactly one package and the loop can only call tools in it (any other call is refused). Each package is built per call, so its tool closes over that call's input (the batch text, the gaps).
- **The packages** (each pinned by a test):
  - `ingestion-tagging` = [`submit_chunk_tags`] and `ingestion-scope` = [`submit_scope`] (Phase 2 fallback calls).
  - `extraction` = [`submit_extraction`] (Phase 3, one entity and one batch of its chunks).
  - `generation-needs` = [`submit_needs`] (Phase 4, one document's gaps).
  - **Phase 5:** LangGraph nodes call the registry tools unchanged and respect the same packages.
- `AgentLoop` is thin: call the model, run the requested tool, return its result to the model, stop when the model answers in text or at a turn cap; it nudges once on an empty reply and then fails loudly. It is tested with a fake model.
- **Provider-neutral model interface:** `ModelClient.complete(system, messages, tools)` over neutral machinery models; default provider Ollama (local, or Ollama Cloud with `OLLAMA_HOST=https://ollama.com` and `OLLAMA_API_KEY`), Anthropic optional; cut-off responses raise; connection and 5xx errors are retried; tested with `FakeModelClient`.

### Decisions
- The facts in the bundle are the source of truth. Entity facts are written by `BundleStore`, document state by `DocumentStateStore`. There is no database and no separate knowledge-store table (the SQLite design was replaced on 2026-10-11: knowledge as plain OKF files, user decision).
- LLMs only tag, scope, extract and phrase; everything else is deterministic (Principle 5). Validation errors (`REJECTED`) and tool refusals are the feedback loop.
- No hand edits (user decision): all input arrives as files in `incoming/`; facts, sources, contributions and state files are written and maintained by the system only.
- Originals in `<scope>/references/` are written only by the ingestion pipeline. Nothing is hand-edited.
- Chunk text is not stored: chunking is deterministic from the original, so extraction re-derives the chunks and checks them against the Source's outline. LLM-fallback tags are stored in the Source (they cost a call).
- Generated documents (configuration-driven, deterministic) go to `output/`; their state files sit in `output/<App>/state/`.

### Phase 2: Ingest
Phase 2 is **ingestion, chunking and movement**; extraction is Phase 3. Everything is deterministic; an LLM is called only where the rules give no answer.

**Flow per file** (`docfactory/ingest/pipeline.py`, files in case-insensitive name order):
1. **Stage:** `incoming/<name>` moves to `staging/`. From here a failure leaves the file in staging; nothing is deleted except a verified SAME duplicate. Files left in staging are retried on every run.
2. **Lookup** among the Sources of the bundle by file name and by hash across all scopes: same name and hash with the stored original present on disk with that hash = **SAME** (staged copy discarded); same name and hash but the original missing or altered = **REPAIRED** (put back, Source rewritten, version unchanged); same content under another name = left in staging as a duplicate; same name in exactly one scope with another hash = **CHANGED** (scope inherited, version + 1); same name in several scopes = left in staging; otherwise **NEW**.
3. **Chunk the original** (`ingest/chunking.py`, readers in `ingest/chunkers/`): PDF with `pdfplumber` (body size from paragraph-length lines; headings are clearly larger lines, numbered ones get their level from the numbering; in a numbered document unnumbered large lines such as cover titles and diagram labels stay text; tables read row by row so an identifier stays with its statement, `FR-85. | The system SHALL ...`; table-of-contents lines, page numbers and running headers dropped; symbol-font bullets become '-'), Word with `python-docx` (heading styles, tables), HTML with `BeautifulSoup` (h1-h6, tables, nothing read twice), text/markdown (headings, numbering, markdown tables). A chunk is one section with its heading trail (`3. ... > 3.1. ... > 3.1.1. ...`), never splitting a section's element; a table header row is kept once per section; sections over 4000 chars split into parts; a leading title styled as a heading stays front matter; no headings = 1500-char parts. No text (scanned PDF) or an unsupported type = left in staging.
4. **Tag chunks with entities** (`ingest/tagging.py`) against the **ontology** (below): heading term in the chunk's own heading 4, in a parent heading 3 (inherited), identifier pattern 4, keywords 1 each up to 3; an entity tags at score >= 3 **and** with a strong signal (keywords alone never tag); the longest heading match wins ('non-functional requirements' is not 'functional requirements'); plurals match. A chunk may carry several entities. Chunks no entity reaches are **unmapped**.
5. **LLM fallback for unmapped chunks** (`agents/ingestion_fallback.py`): one call, fresh context, one tool `submit_chunk_tags`; it sees the compact ontology summary and only the unmapped chunks' headings and first 300 chars. Code validates the answer (closed entity list, only the asked chunks, every asked chunk answered) and feeds errors back; accepted tags keep origin `llm/<model>`. A failed or empty call leaves the chunks unmapped.
6. **Scope (NEW only)** (`ingest/scope_rules.py`): only shared entities tagged (Slo, Kpis) = `shared` (the bundle folder `Shared/`); else the name from a document-control row (`Title | ...`) or the title line, with document-type wording removed ('Software Requirements Specification for', '(working draft 0.3)', 'on-call runbooks') and line-break hyphens mended; an existing folder of the bundle matching ignoring case and punctuation is reused; the folder name replaces other characters with '-' (`AI-Driven-Job-Matching-Platform`). An unconfident scope goes to the **scope fallback**: one call, one tool `submit_scope` (application name, `shared`, `general` or null); null leaves the file in staging with both reasons.
7. **Move + commit:** `staging/<name>` -> `bundle/<scope>/references/<name>`, then the Source concept `<scope>/sources/<name>.md` is written last (it marks a complete ingestion). If that write fails the file goes back to staging and a replaced original is restored. The **resource** of an original everywhere (reports, contributions, fact sources) is its bundle path `<scope>/references/<name>`. On CHANGED the report names the entities whose chunks changed or disappeared (to re-extract).
8. **Report** per file (`IngestReport`): outcome, target, version, chunk count, entity -> chunk count (with how many by the LLM), unmapped chunks, changed entities, reason.

**Source concept:** frontmatter only: `type: "Source"`, `title`, `resource`, `generated {by: docfactory/ingestion, at}`, `hashcode` (SHA-256 of the original's bytes), `version`, `chunks` (number, text hash, heading) and `chunk_tags` (chunk, entity, origin `rule` or `llm/<model>`, score, evidence). No chunk text.

**Ontology:** `docfactory/ontology/signals.json` (edited by people) holds per entity the heading terms, identifier patterns and keywords, validated by `EntitySignals`; a test fails when an entity has no entry, an entry names an unknown entity or appears twice. `docs/ontology.md` is generated (`python -m docfactory.ontology.ontology_render`) from the entity models plus the signals; `ontology_summary()` is the compact form sent to the LLM.

**Rebuild and reads:** chunks and tags are derived data: `python -m docfactory.ingest.chunk_rebuild` re-chunks and re-tags (rules only) every stored original after the chunkers or signals change (it rewrites each Source's outline and tags; LLM tags are not reproduced). `source_reads.read_chunks(path)` returns a Source and its chunks re-derived from the original, and raises `ChunksOutOfDateError` when they no longer match the outline (the fix is `chunk_rebuild`); `read_source_text` rebuilds a file's text.

**Models:** `DocChunk`, `ChunkTag`, `ChunkTagProposal`, `SourceChunk`, `SourceRecord`, `EntitySignals`, `IngestOutcome`, `IngestReport`. **Entry point:** `python -m docfactory.agents.run_ingestion [--no-llm]`.

**Verified:** on the real 50-page SRS: 76 chunks, 6 of them tagged by the fallback, 3 unmapped, scope `AI-Driven-Job-Matching-Platform` from the document-control title row. Live corpus test (`pytest -m live tests/test_live_ingestion.py`): the fallback tags the informal ReadmeForge SRS, puts the standards PDF in `Shared` via its Slo tags, refuses a scope for personal notes; the duplicate PDF stays in staging; the revision comes in as CHANGED v2 naming the entities to re-extract. The real run migrated from the SQLite design re-derives the same 76 chunks, extracts with no LLM call (all unchanged) and generates a byte-identical SRS.

### Phase 3: Extract knowledge (OKF)
Extraction turns the tagged chunks of a new or changed ingested file into facts through `BundleStore`. No LLM writes a file.

**OKF v0.2 metadata** (spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md; a verbatim copy is in `docs/okf/SPEC.md`) lives in the frontmatter of the concept file; the content is the structured JSON defined by the entity model and validated on write and read. The metadata is all derived by the store, none hand-written:

| Frontmatter | Meaning |
|---|---|
| `type`, `title`, `description` | OKF `type`: the entity model name in words, e.g. `Application Overview`; the display name and the one-sentence description |
| `tags`, `sources` | OKF `tags` and `sources[]` (`resource` required, `id`, `title`, `last_modified`) |
| `generated {by, at}` | Trust: OKF `generated`; actors follow the convention `<producer>/<version>` (agents), `human:<id>`, `process:<id>` |
| `verified` | Trust: OKF `verified [{by, at}]`; empty = unverified |
| `status` | Lifecycle: `draft` \| `stable` \| `deprecated` |
| `stale_after` | Lifecycle & freshness: ISO 8601 instant; stale when now >= `stale_after` |
| `fact_key`, `version`, `completeness`, `hashcode` | Producer-defined keys |

- `sources[]` point at the ingested originals the fact came from (their bundle paths). The bundle's `index.md` and `log.md` follow OKF sections 8 and 9.
- **Hash and version cover the value only.** A save with the same value but different metadata is `UNCHANGED`: no version bump, the metadata is refreshed in place. Old values and who changed them are in `log.md` and, if the bundle is a git repository, in its history.
- **Caller-supplied judgment fields** travel in `FactMeta` (`generated_by`, `title`, `description`, `tags`, `sources`, `stale_after`) and `FactSource`; everything else is derived. Seeded facts use `SEED_META` (`generated.by` = `seed`).
- **Trust rule:** LLM output is always `draft` with `generated.by` = `okf-extraction-agent/<model>`, set by code. Only a human approval (Phase 5) adds `verified` with a `human:<id>` actor and promotes to `stable`.
- **Open questions:** below its JSON, a fact file lists every scored field still at its default: field path, question, and the default assumed until answered (list item fields once per field, 'missing in k of n items', followed by those items, each named by its mandatory fields, e.g. `FR-01 | Login | The system SHALL ...`, cut at 120 characters). Deterministic (`open_questions.py`, `missing_md.py`), by the same rule as completeness (a test checks the questions account for exactly the unanswered part of every sample's score). A fact with no open question has no such section. They are rewritten with the file and never stored elsewhere.
- One key is one aggregate per entity (e.g. all SOP procedures in `<App>.Sop`); one key per item would need new key patterns and is not decided.

**Extraction flow** (`extract/extraction_pipeline.py`):
- **Per entity, per batch, one tool.** For each entity tagged in a Source, its chunks (re-derived from the original, in document order) are packed into batches of up to `BATCH_CHARS` = 3500 characters (chunks never split). Each batch is one fresh `AgentLoop` (`EntityExtractor`) with exactly one tool, `submit_extraction(values, summary)`, that sees only the entity's meaning and that batch. `values` is a **partial object**: the entity model with every top-level field optional (`partial_schema`, built with `create_model`); list items keep their mandatory fields.
- **The tool checks, code decides.** `submit_extraction` refuses, with feedback the model acts on: invalid values (`SaveError`s with field description and question), placeholder text such as `N/A: not mentioned` (leave the field out), two items sharing an identifier, and item identifiers not found in the batch text. It strips trailing punctuation from identifiers (`FR-01.` -> `FR-01`). It writes nothing.
- **A failed batch of several chunks is split in half and retried**; a failed single chunk is reported and the contribution keeps no chunks hash, so the next run retries. One failed batch never stops the others.
- **Facts merge across documents (user decision).** Several documents may contribute to one fact, so extracting one document never wipes what others gave. Each file's contribution is a Contribution concept (`<scope>/sources/<file>/<Entity>.md`: the partial JSON it states, its `chunks_hash`, summary, actor, time). The fact = deterministic merge of all its contributions (`extract/merge.py`): newest ingested file first; scalars first non-empty, a different value elsewhere is a reported conflict; string lists unioned (case and spacing ignored); model lists unioned by the item's identity field (its first mandatory field: `id`, `name`, `title`, `role`; a test pins one for every item model), same-identity items merged field by field. Batches of one file merge with the same rules. A CHANGED file replaces only its own contribution, so an item removed from it disappears unless another file states it. A fact stored before any extraction (seeds) is the lowest-precedence contribution `(existing)`.
- **Skips and removals.** Unchanged `chunks_hash` = `SKIPPED_UNCHANGED_CHUNKS`, no LLM call (`--force` overrides); this is how a CHANGED file re-extracts only its changed entities. An entity no longer tagged in a file loses that file's contribution and the fact is re-merged (`REMOVED`). A merged fact the store rejects (e.g. an overview without `purpose`) is `REJECTED` but the contribution is kept for a later document.
- **Scope rule (user decision).** The key comes from the bundle folder of the original: `<App>.<Entity>`; `Slo` / `Kpis` (shared-only facts) come only from files in `Shared/`; an application document never overwrites a common standard; `general/` gives no facts. Component keys are not derived.
- **Metadata.** Code derives `title` ('<scope> <entity in words>'), `tags` ([entity, `extracted`]), `generated_by` and `sources` (every contributing file with its Source timestamp); `description` is the newest contribution's one-sentence summary from the model.
- **Priorities from keywords (user decision).** A requirement item whose priority the model left empty gets the one its own statement states: SHALL / MUST / REQUIRED -> MUST, SHOULD / RECOMMENDED -> SHOULD, MAY / OPTIONAL (capitals only) -> COULD, strongest keyword winning; the model's own priority is never changed (`extract/priority_keywords.py`).
- **Report** (`EntityExtractionReport`, outcomes in `ExtractionOutcome`): key, outcome, version, completeness, chunks, batches, failed batches, items, priorities from keywords, contributing files, batch problems, conflicts, values not grounded in the text (identifiers and model-written titles excluded), missing-info questions (`extract/missing_questions.py`, which also covers a merged value the store rejects), save errors.
- **Prompt:** `.claude/agents/docfactory-entity-extractor-agent.md` (fill only what the chunks state, the document's wording and identifiers, text under a numbered item stays in that item).
- **Entry point:** `python -m docfactory.agents.run_extraction "<bundle path of the original>" [--entity <Entity> ...] [--force]`, e.g. `"ReadmeForge/references/ReadmeForge SRS v0.3.pdf"`.

**Verified** (`gemma4:31b` on Ollama Cloud, default `DOCFACTORY_NUM_CTX`): the real 50-page SRS gives 186 functional requirements (all 172 non-empty FR identifiers plus unnumbered items; FR-47/48 are empty rows in the PDF) and 165 non-functional requirements (all 162 NFR identifiers), plus ApplicationOverview, Architecture, BackupRecovery, Environments and Monitoring; Slo is skipped by scope; the whole file takes about 5.5 minutes with no failed batch, and a second run makes no LLM call. `pytest -m live tests/test_live_extraction.py`: the corpus SRS gives its three requirements; its revision updates `FunctionalRequirements` to v2 and skips unchanged entities.

**Open review points** (Phase 5 territory): near-duplicate list entries that differ in wording are not merged; chunks the ingestion fallback tagged with doubtful entities (real SRS 4.1 User Interfaces, 6.1, 6.3 as FunctionalRequirements) yield unnumbered items; on the real SRS, `Environments` items are named after requirement headings (Technical, Hardware, Software) and `Monitoring` alerts after requirement IDs (NFR-44, NFR-134).

### Phase 4: Generate
Generation **groups the stored fact JSON by the document template, writes the `.md`, maintains the document control and revision history, and writes the needs list for what is missing.** No retrieval and no generating agent: every document field's binding (`<Entity>.<field>`) already says which fact fills it, and copying keeps every value exactly as the facts state it. One small, checked LLM call phrases the needs list.

**Templates.** A template is a YAML file in `generation/templates/` (see "Documents"); each field is bound to `<Entity>.<field>`. The four templates are Overview, SMTD, SRS (ApplicationOverview, FunctionalRequirements, NonFunctionalRequirements, `Shared.Slo`) and SOP; each file names its document (used in the title).

**Flow per `<App> <DocType>`** (`generation/generate_document.py`, with the shared steps in `generation/generation_steps.py`):
1. **Group** (code): `build_body` reads `<App>.<Entity>` and `Shared.<Entity>` from the bundle (scan the concept files the bindings name, extract the JSON under `# Value`, check its hash, parse it into the entity objects, align the bindings) and copies every answered bound field into the body, in the template's order. Nothing is rewritten, summarised, merged or invented. An absent or incomplete fact still gives a document: its fields render as `_Not provided._` and reach the needs list.
2. **Save the body** through `DocumentStateStore` (`UNCHANGED` when the facts did not change).
3. **Document control and revision history** (code, below), saved as their state files.
4. **Gaps** (code, below), then the **needs list** (one checked LLM call, below), saved as the needs state file.
5. **Render** `output/<App>/<DocType>.md` (`render_document_markdown`) and `output/<App>/<DocType>.missing.md` (`render_document_needs`; removed when there is no gap). A file whose bytes are unchanged is not rewritten.

**Document control and revision history (user decisions).** Both are maintained by the generate process; no input comes from facts. `build_body` never fills them.

| Field | Value |
|---|---|
| `document_id` | `<App>-<DocType>` |
| `title` | the application and the template's document name, e.g. `AI-Driven-Job-Matching-Platform Software Requirements Specification` |
| `document_version` | `0.<body version>` while the document is a draft |
| `status` | `Draft`; a status already in the stored control is kept (the Phase 5 approval sets it) |
| `owner` | always the system: `docFactory` |
| `approvers` | kept from the stored control; empty until the Phase 5 approval adds the person who reviewed it. Not a needs-list question |
| `created_date` | the date of the first generation; kept on later runs |
| `last_updated_date` | the date the body last changed (`CREATED` / `UPDATED`) |

`RevisionHistory` gets one `RevisionEntry` per body save that is `CREATED` or `UPDATED`, or when no history exists yet; an `UNCHANGED` body adds none, unless the history is behind the body (its latest entry is not the body's document version, because an earlier run stopped between saving the body and saving the history): then one entry, 'Revision recorded late...', catches it up and the control's last-updated date moves. `version` = the new `document_version`, `date` = today, `author` = `docFactory`, and a `summary` written by code: 'Generated from <key> v<n>, ...' (facts not stored yet are named '(not available)'), or 'Changed sections: <section> (from <key> v<n>)'. Existing entries are kept.

**Gaps** (`generation/gaps.py`): the template's fact-bound fields in template order (`template_gaps`). A bound field whose fact is absent, or whose source field is unanswered, is one gap. A bound field that is answered and holds a nested model or list of items adds the fact's `open_questions` under it, re-pathed to the document field, with 'missing in k of n' and at most 3 example items. Only fields the template binds count. Gaps are numbered 1..n; `gaps_hash` is the SHA-256 of their canonical JSON.

**The needs list** (the `needs` state file, model `MissingInfo`): `gaps` (`DocumentGap`: `number`, `field`, `question`, `expected_source`, `missing_in`, `item_count`, `example_items`), `needs` (`DocumentNeed`: `question`, `audience`, `gaps`, at least one gap number; list order = priority), and the unscored `gaps_hash` and `needs_origin` (`NeedsOrigin`: `llm`, `fallback`, `no_llm`).
- **One LLM call** (`agents/needs_writer.py`, `NeedsWriter`; fresh context, single tool `submit_needs`, package `generation-needs`; prompt `.claude/agents/docfactory-needs-list-agent.md`) sees the application, the document name and the numbered gaps, and turns them into needs: related gaps merged into one question, phrased in the application's terms, grouped by who can answer (e.g. product owner, architect, operations, service owner), most important first.
- **Code checks** the answer and feeds errors back: every gap covered by at least one need, no unknown gap number, every need cites a gap and names an audience. Only gaps reach the list, so no question is invented.
- **Skip and fallback:** unchanged `gaps_hash` and a stored list from the LLM (or from the same mode) = no call. A failed call saves one need per gap (`fallback`) and is retried on the next run; `--no-llm` does the same (`no_llm`). No gaps = no call and no `.missing.md`. Neither the document nor its needs list is ever blocked.
- **Not stored per fact (decided):** a fact's questions are derived data that would go stale when the model's questions change, and the needs list belongs to a document (it merges facts and depends on the template). A fact's own questions stay in its concept file.
- `render_needs_markdown` lists the needs by audience (numbered in priority order across groups), each with the gaps it covers, then every gap with its source and examples.
- Answers re-enter as new or changed source documents in `incoming/` (Phase 2 > 3 > 4 again), never as edits to an output.

**Report** (`GenerationReport`): per document the body action, version and completeness, the document version, the revision entry added, the number of gaps and needs, where the needs came from (and the fallback reason), the files written, and any save errors.

**Entry point:** `python -m docfactory.generate <App> <Overview|SMTD|SRS|SOP|all> [--no-llm]`. An application with no facts is refused with the list of applications that have facts.

**Verified** on the real AI-Driven-Job-Matching-Platform SRS (`gemma4:31b`): Overview 70% (3 gaps -> 2 needs), SMTD 34% (42 -> 14), SRS 66% with all 186 FR and 165 NFR rows (11 -> 8), SOP 48% (12 -> 5), all needs lists from the LLM, about 35 seconds for all four; a rerun changes no file and makes no LLM call. `pytest -m live tests/test_live_generate.py` covers the needs call on a small SRS.

### Phase 5: Human in the loop
- The approval gate becomes a workflow: **agents propose, humans approve, tools apply.** It is built with **LangGraph**, used for orchestration and its **checkpointing** (durable state, `interrupt` to pause for a human, resume with the decision). LangGraph is introduced here and only here; it does not replace the tool layer (Principle 9).
- Graph nodes call the registry tools. Proposals (a classification, a fact payload, a generated document) are held in the checkpoint, not written to the bundle. Only after approval does the node call the store. Rejection returns feedback to the agent.
- The human approval adds `verified` with a `human:<id>` actor and promotes `draft` to `stable` in the fact's frontmatter, and sets a document's status and approvers.
- To design in Phase 5: which steps need approval (classification, facts, documents), the checkpoint store (a file or SQLite kept apart from the bundle), the approval interface (CLI first), the timeout and escalation rule for pending approvals, and the review of the open extraction points.

### Phase 6: Automate
- A watcher for `incoming/`, automatic triggering, and the end-to-end workflow: ingest, extract, approve, generate, render. Triggers become automatic; the approval gate from Phase 5 stays.
- To design in Phase 6: the watcher, the trigger rules (new or changed file, stale fact, changed fact -> regenerate the affected documents), failure and retry handling, and monitoring of runs.

## Working rules

- Read this file first. When something is unclear, ask the user.
- One class per file, in the right folder (Principle 1). Create models and fact registrations through the `docfactory-pydantic-developer-agent`.
- Write to the bundle and to `output/<App>/state/` only through the stores. Never edit generated documents, bundle files or state files by hand; change the models or documents and regenerate.
- Changing a model changes stored data's meaning: say so and update the tests and golden files in the same change.
- Descriptions on models and fields are part of the product: write them for an LLM reader (meaning, example of a good value, what to ask if missing).
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes.
- Keep the repo in git so data-shape changes are diffable; build step by step, with the user's review between steps.
