# docFactory: Current Status

Last updated: 2026-10-03

Living status file. Update it as work progresses. `CLAUDE.md` remains the authoritative spec; this file summarises where we are.

## Purpose

- Keeps application documentation (Overview, SMTD, SRS, SOP) up to date from structured knowledge.
- Knowledge is stored as Pydantic-validated JSON objects in SQLite.
- Documents are composed Pydantic objects, rendered to Markdown by deterministic code.

## Phase status

| Phase | State | Summary |
|---|---|---|
| 1 | **Done** (closed 2026-10-03) | Fully deterministic: seed data, then hard-coded saver calls, then validated facts in SQLite, then composed documents, then `.md` files. No LLM. Four document types (Overview, SMTD, SRS, SOP), one sample app (ReadmeForge). |
| 2 Ingest | **Done, redesigned and verified** (2026-10-03) | `incoming/` -> `staging/` -> lookup (NEW / SAME / CHANGED / REPAIRED) -> deterministic chunking of the raw file (pdfplumber, python-docx, BeautifulSoup) -> entity tags from the ontology (`signals.json`, `docs/ontology.md`), a one-tool LLM fallback for unmapped chunks and unsure scopes -> `DocStore/<scope>/` with `DocChunks` / `DocChunkTags`. No markitdown, no sidecar, no ingestion agent. Verified live on `tests/corpus/` and in a clean end-to-end run on the real SRS (see "Current repo state"). |
| 3 Extract (OKF) | **Pending: redesign** | The first build works on small documents but failed on the real 50-page SRS: one agent with 13 save tools wrote a 37-45 KB fact in one call and stopped silently. To redesign on top of Phase 2's tagged chunks. Kept from the first build:  **3a (deterministic, no LLM):** `KnowledgeFacts` is OKF v0.2 compliant: OKF columns, `KnowledgeFactsHistory`, source index, one bundle file per fact under `bundles/` written by the entity savers (`save(..., meta=FactMeta)`), typed reads, `okf_check`, `bundle_rebuild`, ReadmeForge seeds regenerated (13 conformant files). **3b:** `extraction` tool package (pinned list, 13 typed `save_<entity>` tools, actor and source timestamps set by code), `AgentLoop` / `ExtractionAgent`, runtime prompt, `run_extraction`, key -> saver resolution, bodies in model field order; verified live on the corpus SRS and its revision. To be replaced: the whole-document extraction agent and its 18-tool package. |
| 4 Generate | **Pending: rework** | Built once, but depends on the extraction being redone and has open gaps (only the Overview run live, no MissingInfo for generated bodies, SRS should be the default template, large payloads stop the agent). Kept:  **4a (no LLM):** `FactIndex` vector index (SQLite + numpy) over the frontmatter behind `VectorIndex` / `Embedder` (Ollama `/api/embed`, `DOCFACTORY_EMBED_HOST` because Ollama Cloud has no embedding models), `RetrievalHit`, `DocumentRecord`, `get_document`, document saver resolution. **4b:** `generator` tool package (pinned list: search, read OKF file, reads, `get_document_schema`, `save_document`, 4 typed `save_<document>`), `GeneratorAgent`, runtime prompt, `run_generation`. Verified live: the ReadmeForge Overview came out at 100% with no value the facts do not state. |
| 5 Human in the loop | **Pending** | Outline only: approval workflow on LangGraph (agents propose, humans approve, tools apply); promotes `draft` facts to `stable`. |
| 6 Automate | **Pending** | Outline only: watcher for `incoming/`, automatic triggering, end-to-end workflow. |

- Triggers are manual until Phase 6 (watcher and automatic triggering).
- Phases 1 and 2 are done. Phases 3 and 4 are pending a redesign (code from the first build is in the repo and the suite is green, but it is not the target design). Phases 5 (human in the loop) and 6 (automate) are pending: outlines only, not to be implemented yet. `README.md` explains the process and lists the commands.

## Core principles

- **Single responsibility.** One class per file, named in snake_case after the class, in the right folder. A test enforces this.
- **Facts are the source of truth.** Generated documents, OKF files and `.md` files are views and are never hand-edited.
- **Only valid data is stored.** Every write goes through a Pydantic model. Invalid input returns a structured error.
- **Models are the contract.** Every model and field has a description written for an LLM.
- **Deterministic first.** An LLM only does judgment work: classifying, finding information, constructing calls.
- **Never invent values.** Defaults are placeholders, not knowledge.
- **Errors are feedback.** Rejections tell the caller what to fix or what to find out.
- **Only tools write to the database.**

## Models (`docfactory/`)

- `models/`: machinery (`DocFactoryModel` base with `extra="forbid"`, `doc_field`, `NotApplicable`, `SaveResult`, `SaveError`, `SaveAction`).
- `entitymodels/facts/`: facts that have a saver (`ApplicationOverview`, `Architecture`, `Slo`, `Kpis`, ...).
- `entitymodels/items/`: nested items and enums with no saver (`Environment`, `Alert`, `Requirement`, ...).
- `documentmodels/`: three role folders.
  - `documents/`: document bodies.
  - `shared/`: caller-supplied parts (`DocumentControl`, `RevisionHistory`, `MissingInfo`).
  - `entitybound/`: sections over entity facts.
- Document models may import entity models. The reverse never happens, and `models/` imports neither.
- No `dict`, `Any` or untyped lists. Mandatory fields are kept to the minimum.

## Database (`db/docfactory.sqlite`, override with `DOCFACTORY_DB`)

- Two tables with the same shape: `KnowledgeFacts` and `DocumentOutputs`.
- Columns: key, canonical JSON `Value`, SHA-256 `Hashcode`, `AppID`, `Completeness`, `Version`.
- Keys look like `<Scope>.<Name>`, e.g. `ReadmeForge.Architecture`, `Shared.Kpis`. `Shared` means `AppID` is NULL.
- Component keys look like `<App>.Components.<Component>.<Entity>`.
- The whole object is saved. Same hash gives `UNCHANGED`. A different hash gives `UPDATED` and `Version + 1`.
- Completeness is answered fields divided by total fields. Defaults are not answered, and `N/A` with a reason is. Scoring is recursive over list items and nested models.

## Savers

- `BaseSaver` holds all logic: key check, validation, hash, version, completeness, single transaction.
- Concrete savers only declare a model and key patterns.
- Entity savers are in `entitysaver/`. Document savers are in `documentsaver/<role>/`.
- `save()` always returns a `SaveResult` (CREATED, UPDATED, UNCHANGED or REJECTED) and never raises on bad input.

## Documents

- Each output document is three rows in `DocumentOutputs`: body, `.DocumentControl`, `.RevisionHistory`.
- `build_document` fills the document from facts, marks missing fields and generates the MissingInfo list.
- `render_markdown` assembles the final file deterministically. Same rows give the same bytes, checked against golden files.

## Tooling

- `.claude/agents/`: `docfactory-pydantic-developer-agent` (all models and savers go through it), `docfactory-sample-generator-agent`, runtime prompts `docfactory-chunk-tagger-agent` and `docfactory-scope-agent` (Phase 2 fallback), `docfactory-okf-extraction-agent`, `docfactory-document-generator-agent`.
- `.claude/skills/`: entry skills (`docfactory-create-shared-model`, `docfactory-create-entity-model`, `docfactory-create-document-model`, `docfactory-add-field`, `docfactory-review-models`) and reference skills (`docfactory-field-spec`, `docfactory-quality-gate`).
- `.claude/scripts/`: deterministic scaffolding and gate scripts, tested in `tests/scripts/`.
- Other directories: `samples/`, `seed/` (ReadmeForge seed scripts), `tests/` (pytest, golden files), `output/<app>/` (gitignored).

## Working rules

- Read `CLAUDE.md` first. Ask when something is unclear.
- Say so when a model change alters the meaning of stored data, and update tests and golden files in the same change.
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes.

## Current repo state

- Branch: `PydanticApproach` (main branch: `main`).
- Phases 1-3 (first build) committed and pushed; Phase 4 and the Phase 2 redesign committed locally, not yet pushed.
- **Runtime state at the end of 2026-10-03** (clean end-to-end run of `python -m docfactory.agents.run_ingestion` on the real SRS, `gemma4:31b` on Ollama Cloud): `DocStore/AI-Driven-Job-Matching-Platform/Annex-A-Detailed-Software-Requirements-Specification-SRS.pdf` v1; `db/docfactory.sqlite` holds its `DocStore` row, 76 chunks and their tags (rules: ApplicationOverview 12, FunctionalRequirements 25, NonFunctionalRequirements 29, Architecture 5, Monitoring 3, BackupRecovery 2, Environments 1, Slo 1; LLM fallback tagged 6 of the 9 unmapped chunks: 4.1 and 6.1 and 6.3 -> FunctionalRequirements, 4.2 and 4.4 -> Architecture, 6.2 -> NonFunctionalRequirements; front matter and the two appendices stay unmapped). No facts, bundles or documents exist yet. Review candidates: 6.3 Training Requirements and 4.1 User Interfaces tagged FunctionalRequirements by the LLM. `bundles/` and `output/` are now gitignored working folders; the earlier contents were moved to `samples/bundles/` and `samples/output/` (including `AI-Driven-Job-Matching-Platform/`).

## Next up

Next session (continue from here):

1. **Phase 3 redesign: extract knowledge from the tagged chunks.** Per entity in `DocChunkTags`, one fresh small LLM call that sees only that entity's chunks (batched) and submits a partial object through one tool; code merges the partials (lists concatenated and de-duplicated by id, scalars first-non-empty), builds the complete object, calls the entity saver once (bundle `.md` written as today), and reports per entity: chunks used, items, version, completeness, missing-info questions, values not found verbatim in the chunks. A CHANGED file re-extracts only the entities in its `changed_entities`. Replaces the whole-document `ExtractionAgent` and its 18-tool package. Design first (plan mode), then build step by step.
2. **Phase 4 rework: generation.** SRS as the standard template, a MissingInfo list even when information is incomplete (never skip the document), no silent stop on large payloads, then live runs for SMTD, SRS and SOP. The vector index needs an embedding provider: Ollama Cloud has none, and the user does not want local models (decide: a cloud embedding API, or lexical search over the frontmatter).
3. **Phase 5 and 6:** pending; outlines only.

Notes for the live tests: the key goes in `.env` (copy `.env.example`); `gemma4:31b` on Ollama Cloud is the model in use.

## Change log

- 2026-10-03: Created from the project summary.
- 2026-10-03: Phase 2 closed. Added `ingest/`, `tools/` (registry, packages, ingestion package), `agents/` (provider-neutral model client, Ollama default, ingestion loop), `DocStore` tables, `.env` loading, test corpus and an opt-in live test.
- 2026-10-03: Phase 3 designed; 3a built. OKF columns, `KnowledgeFactsHistory`, `KnowledgeFactSources`, `FactMeta` / `FactSource` / `FactVerification` / `FactRecord` / `FactStatus`, bundle writer and checker, typed reads, seeds regenerated with `SEED_META`. `docfactory-create-shared-model` is now invocable by the model.
- 2026-10-03: Phase 3b built. Extraction package and agent, `AgentLoop` refactor, saver resolution, `read_docstore_text`, `DOCFACTORY_NUM_CTX`, live test; bundle bodies in model field order.
- 2026-10-03: Phase 3 closed. Added `README.md` (process explainer and commands).
- 2026-10-03 (end of day): clean end-to-end ingestion of the real SRS; Phases 3 and 4 marked pending a redesign, 5 and 6 pending.
- 2026-10-03: Phase 2 redesigned after extraction failed on a real 50-page SRS: ontology (`EntitySignals`, `signals.json`, `docs/ontology.md`), format-aware chunkers, rule tagging, scope rules, staging pipeline with REPAIRED (fixes the stale-row data loss), `DocChunks` / `DocChunkTags`, single-tool LLM fallback, empty-reply check in `AgentLoop`; old ingestion agent, tools, markitdown and sidecars removed. Phase 3 extraction is redesigned next on top of the chunks.
- 2026-10-03: Phase 4 built. `retrieval/` (embedders, vector index, frontmatter and link helpers, `index_rebuild`), `FactIndex` table, `documents.py`, document saver resolution, generator package and agent, `run_generation`, live test; `OllamaModelClient._post` is now public `post_json`; new dependency numpy; new settings `DOCFACTORY_EMBED_MODEL`, `DOCFACTORY_EMBED_HOST`, `DOCFACTORY_EMBED_API_KEY`.
