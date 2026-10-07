# docFactory: Current Status

Last updated: 2026-10-07

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
| 3 Extract (OKF) | **Done, redesigned and verified** (2026-10-04) | **3a (deterministic, no LLM):** OKF v0.2 metadata in `KnowledgeFacts` columns only (type, title, description, tags, sources, `YmlFrontmatter`, trust, lifecycle); the content is the entity JSON in `Value`. `KnowledgeFactsHistory`, source index, typed reads. (The `bundles/` markdown files were removed on 2026-10-07.) **3b (redesigned):** per entity tagged in a DocStore file, its chunks in 3500-character batches, one fresh single-tool call per batch (`submit_extraction`, a partial object; invalid values, placeholders, shared or unknown identifiers refused); code merges batches, then every contributing file (`FactContributions`, newest first, conflicts reported), fills empty priorities from SHALL/SHOULD/MAY, and saves through the entity saver. Unchanged chunks are skipped without an LLM call; a failed multi-chunk batch is split and retried. Verified on the real 50-page SRS (all 172 non-empty FR and 162 NFR identifiers) and on the corpus SRS and its revision. The first whole-document agent and its 18-tool package were removed. |
| 4 Generate | **Pending: rework decided 2026-10-07, next to build** | No RAG, no agent. Per application and template (SRS first): code groups the facts' JSON by the template's bindings into the body, keeps the document control (owner `docFactory`, status `Draft`, version `0.<body Version>`) and revision history (one entry per body change, summary by code), saves through the document savers and renders `output/<App>/<DocType>.md`. One checked single-tool LLM call (`submit_needs`) turns the gaps (unfilled document fields + open questions of the bound fact fields) into a needs list, saved as a fourth document row `<App>.Outputs.<DocType>.MissingInfo` and rendered to `<DocType>.missing.md`; skipped when the gaps are unchanged, the gaps themselves on failure or `--no-llm`. Entry point `python -m docfactory.generate <App> <DocType|all> [--no-llm]`. Section fields become optional so a missing fact is a gap, not an error. No missing-information column in `KnowledgeFacts`. The first build (vector index, generator agent, `run_generation`) is still in the repo and is removed by the rework. |
| 5 Human in the loop | **Pending** | Outline only: approval workflow on LangGraph (agents propose, humans approve, tools apply); promotes `draft` facts to `stable`. |
| 6 Automate | **Pending** | Outline only: watcher for `incoming/`, automatic triggering, end-to-end workflow. |

- Triggers are manual until Phase 6 (watcher and automatic triggering).
- Phases 1, 2 and 3 are done. Phase 4's rework is decided and documented in `CLAUDE.md` ("Phase 4: Generate"); the first build's code is still in the repo and the suite is green, but it is not the target design. Phases 5 (human in the loop) and 6 (automate) are pending: outlines only, not to be implemented yet. `README.md` explains the process and lists the commands.

## Core principles

- **Single responsibility.** One class per file, named in snake_case after the class, in the right folder. A test enforces this.
- **Facts are the source of truth.** Generated documents, `knowledgefacts/` files and `.md` files are views and are never hand-edited. OKF is only metadata in the `KnowledgeFacts` row; the content is the validated JSON.
- **Only valid data is stored.** Every write goes through a Pydantic model. Invalid input returns a structured error.
- **Models are the contract.** Every model and field has a description written for an LLM.
- **Deterministic first.** An LLM only does judgment work: tagging and scoping what the rules cannot, extracting from small batches of chunks, phrasing a document's gaps as questions. Always one tool per call, checked by code.
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

- Each output document is four rows in `DocumentOutputs`: body, `.DocumentControl`, `.RevisionHistory` and (Phase 4 rework) `.MissingInfo`, the needs list.
- The body comes only from facts (`build_document`); document control and revision history never come from facts: the generate process maintains them (the seeds in Phase 1), approvers come with the Phase 5 approval.
- `render_markdown` assembles the final file deterministically. Same rows give the same bytes, checked against golden files. The needs list renders to `<DocType>.missing.md`.

## Tooling

- `.claude/agents/`: `docfactory-pydantic-developer-agent` (all models and savers go through it), `docfactory-sample-generator-agent`, runtime prompts `docfactory-chunk-tagger-agent` and `docfactory-scope-agent` (Phase 2 fallback), `docfactory-entity-extractor-agent` (Phase 3), `docfactory-document-generator-agent` (first Phase 4 build, removed by the rework; the rework adds `docfactory-needs-list-agent`).
- `.claude/skills/`: entry skills (`docfactory-create-shared-model`, `docfactory-create-entity-model`, `docfactory-create-document-model`, `docfactory-add-field`, `docfactory-review-models`) and reference skills (`docfactory-field-spec`, `docfactory-quality-gate`).
- `.claude/scripts/`: deterministic scaffolding and gate scripts, tested in `tests/scripts/`.
- Other directories: `samples/`, `seed/` (ReadmeForge seed scripts), `tests/` (pytest, golden files), `knowledgefacts/<scope>/` (each fact's JSON and open questions, gitignored), `output/<app>/` (gitignored).

## Working rules

- Read `CLAUDE.md` first. Ask when something is unclear.
- Say so when a model change alters the meaning of stored data, and update tests and golden files in the same change.
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes.

## Current repo state

- Branch: `PydanticApproach` (main branch: `main`).
- All work through the Phase 3 redesign, the OKF-in-the-table change and the `knowledgefacts/` views (2026-10-07) is committed on `PydanticApproach`.
- **Runtime state at the end of 2026-10-04:** `DocStore/AI-Driven-Job-Matching-Platform/Annex-A-Detailed-Software-Requirements-Specification-SRS.pdf` v1 with 76 chunks and their tags (as on 2026-10-03). Extracted facts (draft, `okf-extraction-agent/gemma4:31b`, one contributing file each): `ApplicationOverview` v1 (83%), `FunctionalRequirements` v3 (186 items, 66%), `NonFunctionalRequirements` v2 (165 items, 67%), `Architecture` v2 (20%), `BackupRecovery` v1 (86%), `Environments` v1 (32%), `Monitoring` v1 (36%); their JSON and open questions under `knowledgefacts/AI-Driven-Job-Matching-Platform/`. Review candidates: the ingestion fallback's tags on 4.1 User Interfaces, 6.1 Data Migration and 6.3 Training Requirements (FunctionalRequirements) give 14 unnumbered FR items; near-duplicate list entries in `ApplicationOverview` (capabilities, related systems). No documents generated yet for this application. `output/` is a gitignored working folder; the ReadmeForge sample outputs are in `samples/output/`.

## Next up

Next session (continue from here):

1. **Phase 4 rework: build it** in the order in `CLAUDE.md` ("Phase 4: Generate", build order): section fields optional; the needs-list model and saver (`MissingInfo` row); deterministic `docfactory.generate` with `--no-llm`, verified on the AI-Driven-Job-Matching-Platform SRS; the `submit_needs` call with its coverage checks, then a live run; remove the first build (retrieval, generator agent, `run_generation`, numpy, embedding settings); README and STATUS to as-built. The `DocumentControl` / `RevisionHistory` docstrings already state the new ownership; the `owner` and `approvers` field descriptions follow in the build.
2. **Review the extraction open points** when convenient: the doubtful fallback tags (4.1, 6.1, 6.3), near-duplicate list entries, conflicts between documents once a second document contributes.
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
- 2026-10-04: Phase 3 redesigned, built and closed. `extract/` (batching, fact keys, partial models, merge, grounding, keyword priorities, missing-info questions, pipeline), `FactContributions` table and `contributions.py`, models `ExtractionOutcome`, `FactContribution`, `EntityExtractionReport`, single-tool `submit_extraction` package, `EntityExtractor`, prompt `docfactory-entity-extractor-agent.md`, `run_extraction --entity/--force`; `ExtractionAgent`, its 18-tool package and prompt removed. Decisions: facts merge across documents; Slo/Kpis only from `shared/`; code writes title/tags, the model a one-sentence description; empty priorities from SHALL/SHOULD/MAY. Live fixes: split-and-retry of failed batches, refusal of shared identifiers and placeholders, 3500-character batches.
- 2026-10-07: Phase 4 rework decided (user) and documented in `CLAUDE.md`, `README.md` and here: deterministic grouping of the facts' JSON by template (SRS standard), no RAG, no agent; document control and revision history created and maintained by `docfactory.generate`, never from facts (owner always `docFactory`, approvers from the Phase 5 approval); a fourth document row `.MissingInfo` holds the needs list, built by one checked LLM call from the gaps; no missing-information column in `KnowledgeFacts`; section fields become optional; entry point `python -m docfactory.generate`. `DocumentControl` and `RevisionHistory` docstrings updated.
- 2026-10-07: OKF kept to the table (user). The content of a fact is the JSON its entity model validates; OKF is only metadata in `KnowledgeFacts`. Removed the `bundles/` files and `samples/bundles/`, `bundle.py`, `okf_body.py`, `bundle_rebuild`, `okf_check`, `okf_links`, `frontmatter_values`, the `FilePath` column (dropped on migration), the `key_unsafe_path` check and the generator tool `read_okf_file`. Added columns `FactType`, `Title`, `Description`, `Tags`, `Sources` and the matching `FactRecord` fields; `RetrievalHit.file_path` removed. The vector index embeds `YmlFrontmatter` plus the value in model field order; the generator reads facts with `get_fact`.
