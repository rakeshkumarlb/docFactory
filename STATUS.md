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
| 4 Generate | **Done, reworked and verified** (2026-10-07) | No RAG, no agent. `python -m docfactory.generate <App> <DocType or all> [--no-llm]`: code groups the facts' JSON by the template's bindings into the body, derives the document control (`<App>-<DocType>`, owner `docFactory`, status `Draft` unless the stored row says otherwise, version `0.<body Version>`, approvers kept for Phase 5) and appends a code-written revision entry when the body changed (changed sections and their fact versions). Gaps = unfilled bound fields + the open questions of the bound fact fields (`missing in k of n`, up to 3 examples). One checked single-tool LLM call (`submit_needs`, package `generation-needs`) turns them into needs grouped by who can answer; the tool refuses uncovered gaps, unknown gap numbers and needs without a gap or audience. Saved as the fourth row `<App>.Outputs.<DocType>.MissingInfo` (`DocumentGap`, `DocumentNeed`, `NeedsOrigin`) and rendered to `<DocType>.missing.md`; unchanged gaps = no call, a failed call or `--no-llm` = one need per gap. Section fields are optional, so a missing fact is a gap, never an error. Verified on the real AI-Driven-Job-Matching-Platform SRS (186 FR, 165 NFR, 66%; 11 gaps -> 8 needs) and live on a small SRS. The first build (vector index, `FactIndex`, generator agent, `run_generation`, numpy, embedding settings) was removed. |
| 5 Human in the loop | **Pending** | Outline only: approval workflow on LangGraph (agents propose, humans approve, tools apply); promotes `draft` facts to `stable`. |
| 6 Automate | **Pending** | Outline only: watcher for `incoming/`, automatic triggering, end-to-end workflow. |

- Triggers are manual until Phase 6 (watcher and automatic triggering).
- Phases 1 to 4 are done. Phases 5 (human in the loop) and 6 (automate) are pending: outlines only, not to be implemented yet. `README.md` explains the process and lists the commands.

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
  - `shared/`: caller-supplied parts (`DocumentControl`, `RevisionHistory`, `RevisionEntry`, `MissingInfo` with `DocumentGap`, `DocumentNeed`, `NeedsOrigin`).
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

- Each output document is four rows in `DocumentOutputs`: body, `.DocumentControl`, `.RevisionHistory` and `.MissingInfo`, the needs list.
- The body comes only from facts (`build_document`); document control and revision history never come from facts: `docfactory.generate` maintains them (the seeds supply their own for the golden files), approvers come with the Phase 5 approval.
- `render_markdown` assembles the final file deterministically. Same rows give the same bytes, checked against golden files. The needs list renders to `<DocType>.missing.md`.

## Tooling

- `.claude/agents/`: `docfactory-pydantic-developer-agent` (all models and savers go through it), `docfactory-sample-generator-agent`, runtime prompts `docfactory-chunk-tagger-agent` and `docfactory-scope-agent` (Phase 2 fallback), `docfactory-entity-extractor-agent` (Phase 3), `docfactory-needs-list-agent` (Phase 4).
- `.claude/skills/`: entry skills (`docfactory-create-shared-model`, `docfactory-create-entity-model`, `docfactory-create-document-model`, `docfactory-add-field`, `docfactory-review-models`) and reference skills (`docfactory-field-spec`, `docfactory-quality-gate`).
- `.claude/scripts/`: deterministic scaffolding and gate scripts, tested in `tests/scripts/`.
- Other directories: `samples/` (`json/`: example payloads used by seeds and tests; `DocStore/`, `knowledgefacts/`, `output/`: a committed snapshot of the AI-Driven-Job-Matching-Platform end-to-end run), `seed/` (ReadmeForge seed scripts), `tests/` (pytest, golden files), `knowledgefacts/<scope>/` (each fact's JSON and open questions, gitignored), `output/<app>/` (gitignored).

## Working rules

- Read `CLAUDE.md` first. Ask when something is unclear.
- Say so when a model change alters the meaning of stored data, and update tests and golden files in the same change.
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes.

## Current repo state

- Branch: `PydanticApproach` (main branch: `main`).
- All work through the Phase 4 rework (2026-10-07) is committed on `PydanticApproach`.
- **Runtime state (fresh end-to-end run, 2026-10-07):** the database, `DocStore/`, `knowledgefacts/` and `output/` were cleared and the SRS PDF went through all three steps from `incoming/`. Ingest: NEW v1, 76 chunks (6 tagged by the LLM fallback, chunks 1, 75, 76 unmapped). Extract (5m34, no failed batch): `ApplicationOverview` 75%, `Architecture` 30%, `BackupRecovery` 86%, `Environments` 32%, `FunctionalRequirements` 186 items 66%, `Monitoring` 50%, `NonFunctionalRequirements` 165 items 67%, all v1; `Slo` skipped (shared only). Generate with LLM needs lists (34s): Overview 70% (3 gaps -> 2 needs), SMTD 34% (42 -> 14), SRS 66% (11 -> 8), SOP 48% (12 -> 5). A rerun of all three steps changed nothing and made no LLM call. **A snapshot of this run is committed under `samples/`**: `samples/DocStore/` (the stored PDF), `samples/knowledgefacts/` (fact JSON and open questions) and `samples/output/` (the four documents and their `.missing.md`); the ReadmeForge sample outputs were removed from `samples/output/` (the seeds still regenerate them into `output/ReadmeForge/`). Review candidates: the ingestion fallback's tags on 4.1 User Interfaces, 6.1 Data Migration and 6.3 Training Requirements (FunctionalRequirements) give unnumbered FR items; near-duplicate list entries in `ApplicationOverview`; `Environments` items named after requirement headings (Technical, Hardware, Software) and `Monitoring` alerts named NFR-44 and NFR-134.

## Next up

Next session (continue from here):

1. **Store `Shared.Slo`**: ingest a standards document into `DocStore/shared/` and extract it, so the SRS service levels fill. (All four document types of AI-Driven-Job-Matching-Platform are generated; see `samples/output/`.)
2. **Review the needs lists** of the four generated documents and the **extraction open points**: the doubtful fallback tags (4.1, 6.1, 6.3), near-duplicate list entries, `Environments` items named after requirement headings, `Monitoring` alerts named after NFR identifiers, conflicts between documents once a second document contributes.
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
- 2026-10-07: Phase 4 rework built and closed (steps 1-6). Section fields optional (`build_document` never fails on a missing fact); needs-list row `MissingInfo` with `DocumentGap` (the old item, renamed), `DocumentNeed`, `NeedsOrigin` and `MissingInfoSaver`; `doc_field` gains `ge` and `max_length`; `docfactory/generation/` (doc types, gaps, document control, revision history, fallback needs, per-document flow), `GenerationReport`, `render_needs_markdown`, entry point `docfactory.generate`, env `DOCFACTORY_OUTPUT`; `submit_needs` package `generation-needs`, `NeedsWriter`, prompt `docfactory-needs-list-agent.md`, live test `test_live_generate.py`. Removed the first build: `retrieval/`, `FactIndex` (dropped on connect), `RetrievalHit`, generator package and agent, `run_generation`, its prompt and tests, numpy, `DOCFACTORY_EMBED_*`.
- 2026-10-07: OKF kept to the table (user). The content of a fact is the JSON its entity model validates; OKF is only metadata in `KnowledgeFacts`. Removed the `bundles/` files and `samples/bundles/`, `bundle.py`, `okf_body.py`, `bundle_rebuild`, `okf_check`, `okf_links`, `frontmatter_values`, the `FilePath` column (dropped on migration), the `key_unsafe_path` check and the generator tool `read_okf_file`. Added columns `FactType`, `Title`, `Description`, `Tags`, `Sources` and the matching `FactRecord` fields; `RetrievalHit.file_path` removed. The vector index embeds `YmlFrontmatter` plus the value in model field order; the generator reads facts with `get_fact`.
- 2026-10-07: `CLAUDE.md` tightened to describe the system as built (status lines shortened; Principles 5, 9 and 10 describe single-tool checked LLM calls; `MissingInfo` in the model examples). `README.md` brought in step (settings for every call, the four generated documents of the real SRS, ReadmeForge seed outputs include `SRS.md`); "Next up" updated.
