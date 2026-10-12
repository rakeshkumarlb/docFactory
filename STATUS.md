# docFactory: Current Status

Last updated: 2026-10-11

Living status file. Update it as work progresses. `CLAUDE.md` remains the authoritative spec; this file summarises where we are.

## Purpose

- Keeps application documentation (Overview, SMTD, SRS, SOP) up to date from structured knowledge.
- Knowledge is stored as an OKF bundle: Markdown concept files whose body holds the Pydantic-validated JSON of one fact (no database).
- Documents are composed Pydantic objects, rendered to Markdown by deterministic code; their state is JSON files in `output/<App>/state/`.

## Phase status

| Phase | State | Summary |
|---|---|---|
| 1 | **Done** (closed 2026-10-03) | Fully deterministic: seed data, then hard-coded saver calls, then validated facts in SQLite, then composed documents, then `.md` files. No LLM. Four document types (Overview, SMTD, SRS, SOP), one sample app (ReadmeForge). |
| 2 Ingest | **Done, redesigned and verified** (2026-10-03) | `incoming/` -> `staging/` -> lookup (NEW / SAME / CHANGED / REPAIRED) -> deterministic chunking of the raw file (pdfplumber, python-docx, BeautifulSoup) -> entity tags from the ontology (`signals.json`, `docs/ontology.md`), a one-tool LLM fallback for unmapped chunks and unsure scopes -> the bundle (`<scope>/references/` + a Source concept; since 2026-10-11, formerly `DocStore/` and tables). No markitdown, no sidecar, no ingestion agent. Verified live on `tests/corpus/` and in a clean end-to-end run on the real SRS (see "Current repo state"). |
| 3 Extract (OKF) | **Done, redesigned and verified** (2026-10-04) | **3a (deterministic, no LLM):** OKF v0.2 metadata in the fact file's frontmatter (type, title, description, tags, sources, trust, lifecycle); the content is the entity JSON under `# Value`. (Formerly `KnowledgeFacts` columns; moved to files on 2026-10-11.) **3b (redesigned):** per entity tagged in a DocStore file, its chunks in 3500-character batches, one fresh single-tool call per batch (`submit_extraction`, a partial object; invalid values, placeholders, shared or unknown identifiers refused); code merges batches, then every contributing file (contribution concepts, newest first, conflicts reported), fills empty priorities from SHALL/SHOULD/MAY, and writes through `BundleStore`. Unchanged chunks are skipped without an LLM call; a failed multi-chunk batch is split and retried. Verified on the real 50-page SRS (all 172 non-empty FR and 162 NFR identifiers) and on the corpus SRS and its revision. The first whole-document agent and its 18-tool package were removed. |
| 4 Generate | **Done, reworked and verified** (2026-10-07) | No RAG, no agent. `python -m docfactory.generate <App> <DocType or all> [--no-llm]`: code groups the facts' JSON by the YAML template's bindings into the body, derives the document control (`<App>-<DocType>`, owner `docFactory`, status `Draft` unless the stored row says otherwise, version `0.<body Version>`, approvers kept for Phase 5) and appends a code-written revision entry when the body changed (changed sections and their fact versions). Gaps = unfilled bound fields + the open questions of the bound fact fields (`missing in k of n`, up to 3 examples). One checked single-tool LLM call (`submit_needs`, package `generation-needs`) turns them into needs grouped by who can answer; the tool refuses uncovered gaps, unknown gap numbers and needs without a gap or audience. Saved as the fourth part (state file `<DocType>.needs.json`, key `<App>.Outputs.<DocType>.MissingInfo`) (`DocumentGap`, `DocumentNeed`, `NeedsOrigin`) and rendered to `<DocType>.missing.md`; unchanged gaps = no call, a failed call or `--no-llm` = one need per gap. Section fields are optional, so a missing fact is a gap, never an error. Verified on the real AI-Driven-Job-Matching-Platform SRS (186 FR, 165 NFR, 66%; 11 gaps -> 8 needs) and live on a small SRS. The first build (vector index, `FactIndex`, generator agent, `run_generation`, numpy, embedding settings) was removed. |
| OKF bundle redesign | **Done and verified** (2026-10-11, branch `OkfBundleStore`) | SQLite and the savers are gone. Facts are OKF concept files (`bundle/<Scope>/<Entity>.md`: frontmatter + JSON under `# Value` + `# Open questions`) written by `BundleStore`; ingestion writes the original to `<scope>/references/` and a Source concept (hash, version, chunk outline, tags; no chunk text) to `<scope>/sources/`; extraction keeps each file's share as a contribution concept (`<scope>/sources/<file>/<Entity>.md`); generation reads the bound facts from the bundle (`build.load_fact`) and keeps the documents' state as `output/<App>/state/<DocType>.<part>.json` (`DocumentStateStore`). `index.md` and `log.md` follow OKF sections 8 and 9. Tamper check: a file whose JSON no longer matches its hash is refused. The real run was migrated from the old database with a one-off script: same 76 chunks, extraction skips with no LLM call, the SRS regenerates byte-identical. |
| OKF alignment redesign | **Built** (2026-10-11, awaiting the user's review) | Coverage report; one concept per list item (the fact is a view assembled by `BundleStore`); `Note` fact for chunks no entity claims; type proposals with a gated apply step; relationship graph (`relations`, mentioned identifiers, `<scope>/graph/relationships.md`); source labels, authors, per-scope indexes. Details in `CLAUDE.md`, section "OKF alignment redesign". |
| 5 Human in the loop | **Pending** | Outline only: approval workflow on LangGraph (agents propose, humans approve, tools apply); promotes `draft` facts to `stable`. |
| 6 Automate | **Pending** | Outline only: watcher for `incoming/`, automatic triggering, end-to-end workflow. |

- Triggers are manual until Phase 6 (watcher and automatic triggering).
- Phases 1 to 4 are done. Phases 5 (human in the loop) and 6 (automate) are pending: outlines only, not to be implemented yet. `README.md` explains the process and lists the commands.

## Core principles

- **Single responsibility.** One class per file, named in snake_case after the class, in the right folder. A test enforces this.
- **Facts are the source of truth.** A fact is a concept file of the bundle; generated documents and their `.md` files are views and are never hand-edited. OKF is the frontmatter; the content is the validated JSON in the body.
- **Only valid data is stored.** Every write goes through a Pydantic model. Invalid input returns a structured error.
- **Models are the contract.** Every model and field has a description written for an LLM.
- **Deterministic first.** An LLM only does judgment work: tagging and scoping what the rules cannot, extracting from small batches of chunks, phrasing a document's gaps as questions. Always one tool per call, checked by code.
- **Never invent values.** Defaults are placeholders, not knowledge.
- **Errors are feedback.** Rejections tell the caller what to fix or what to find out.
- **Only the stores write** (`BundleStore`, `SourceStore`, `ContributionStore`, `DocumentStateStore`); no hand edits, and a tampered file is refused on read.

## Models (`docfactory/`)

- `models/`: machinery (`DocFactoryModel` base with `extra="forbid"`, `doc_field`, `NotApplicable`, `SaveResult`, `SaveError`, `SaveAction`).
- `entitymodels/facts/`: facts, registered in `bundle/fact_registry.py` (`ApplicationOverview`, `Architecture`, `Slo`, `Kpis`, ...).
- `entitymodels/items/`: nested items and enums that are not registered (`Environment`, `Alert`, `Requirement`, ...).
- `documentmodels/`: the parts every document has (`DocumentBody`, `DocumentControl`, `RevisionHistory`, `RevisionEntry`, `MissingInfo` with `DocumentGap`, `DocumentNeed`, `NeedsOrigin`). A document body is a YAML template in `generation/templates/`, not a model.
- Document models may import entity models. The reverse never happens, and `models/` imports neither.
- No `dict`, `Any` or untyped lists. Mandatory fields are kept to the minimum.

## The bundle (`bundle/`, override with `DOCFACTORY_BUNDLE`)

- Facts: `<Scope>/<Entity>.md` (`Shared/Kpis.md`, `ReadmeForge/Architecture.md`, `ReadmeForge/Components/api/Architecture.md`). Frontmatter: OKF fields plus `fact_key`, `version`, `completeness`, `hashcode`; body: `# Value` (the JSON) and `# Open questions`.
- Keys look like `<Scope>.<Name>`, e.g. `ReadmeForge.Architecture`, `Shared.Kpis`. `Shared` means `AppID` is NULL. Component keys look like `<App>.Components.<Component>.<Entity>`.
- The whole object is saved. Same hash gives `UNCHANGED`. A different hash gives `UPDATED` and `version + 1`; writes are atomic and skipped when the bytes are the same. A deleted file is a deleted fact.
- Completeness is answered fields divided by total fields. Defaults are not answered, and `N/A` with a reason is. Scoring is recursive over list items and nested models.
- Also in the bundle: the originals (`<scope>/references/`), their Source concepts (`<scope>/sources/<file>.md`), contributions (`<scope>/sources/<file>/<Entity>.md`), `index.md` and `log.md`.

## Stores

- `BundleStore` holds the fact logic: key check against the fact registry, validation, hash, version, completeness, write, log, index. `SourceStore`, `ContributionStore` and `DocumentStateStore` do the same for sources, contributions and document state.
- A save always returns a `SaveResult` (CREATED, UPDATED, UNCHANGED or REJECTED) and never raises on bad input; a corrupt or tampered file raises `BundleError` when read.

## Documents

- Each output document is four state files in `output/<App>/state/` (`<DocType>.body.json`, `.control.json`, `.history.json`, `.needs.json`; keys `<App>.Outputs.<DocType>[.DocumentControl|.RevisionHistory|.MissingInfo]`).
- The body comes only from facts (`build_body`, driven by the template); document control and revision history never come from facts: `docfactory.generate` maintains them (the seeds supply their own for the golden files), approvers come with the Phase 5 approval.
- `render_document_markdown` assembles the final file deterministically. Same state gives the same bytes, checked against golden files. The needs list renders to `<DocType>.missing.md`.

## Tooling

- `.claude/agents/`: `docfactory-pydantic-developer-agent` (all models and fact registrations go through it), `docfactory-sample-generator-agent`, runtime prompts `docfactory-chunk-tagger-agent` and `docfactory-scope-agent` (Phase 2 fallback), `docfactory-entity-extractor-agent` (Phase 3), `docfactory-needs-list-agent` (Phase 4).
- `.claude/skills/`: entry skills (`docfactory-create-shared-model`, `docfactory-create-entity-model`, `docfactory-add-field`, `docfactory-review-models`) and reference skills (`docfactory-field-spec`, `docfactory-quality-gate`).
- `.claude/scripts/`: deterministic scaffolding and gate scripts, tested in `tests/scripts/`.
- Other directories: `samples/` (`json/`: example payloads used by seeds and tests; `bundle/`, `output/`: a committed snapshot of the AI-Driven-Job-Matching-Platform end-to-end run), `seed/` (ReadmeForge seed scripts), `tests/` (pytest, golden files), `bundle/` and `output/<app>/` (runtime data, gitignored).

## Working rules

- Read `CLAUDE.md` first. Ask when something is unclear.
- Say so when a model change alters the meaning of stored data, and update tests and golden files in the same change.
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes.

## Current repo state

- Branch: `OkfBundleStore` (off `ConfigurationBasedExtraction`; main branch: `main`). The six steps of the redesign are built and tested; nothing is committed yet.
- Tests: about 1800 offline tests pass; the structure check passes. The live LLM tests were updated for the new paths but not run since the redesign.
- **Runtime data:** the real run (AI-Driven-Job-Matching-Platform: 7 facts, their contributions, the PDF and its Source, the SRS state files) was migrated from the old `db/docfactory.sqlite` and `DocStore/` into `bundle/` and `output/AI-Driven-Job-Matching-Platform/state/` by a one-off script (not kept in the repo). The old `db/` and `DocStore/` folders are untouched, no longer read by any code, and can be deleted. A snapshot is committed as `samples/bundle/` and `samples/output/`. Review candidates from the extraction (unchanged by the redesign): the ingestion fallback's tags on 4.1 User Interfaces, 6.1 Data Migration and 6.3 Training Requirements (FunctionalRequirements) give unnumbered FR items; near-duplicate list entries in `ApplicationOverview`; `Environments` items named after requirement headings and `Monitoring` alerts named NFR-44 and NFR-134.

## Next up

1. **Review the redesign and commit it** (the branch is uncommitted).
2. **Optimize the generation flow** (next activity, noted in `CLAUDE.md`): generation reads each bound fact's concept file, extracts the JSON, checks the hash, parses it and aligns the bindings. Measure on a large bundle, then optimize (in-memory index, parse-once caching across documents, hash-based skips).
3. **Run the live tests** (`pytest -m live`) against the new storage, and re-run extraction on a changed file to see the contributions and `log.md` in practice.
4. **Store `Shared.Slo`**: ingest a standards document, so the SRS service levels fill.
5. **Review the needs lists** of the generated documents and the extraction open points listed above.
6. **Phase 5 and 6:** pending; outlines only.

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
- 2026-10-10: Added Configuration-based rendering as a parallel option (branch ConfigurationBasedExtraction): YAML templates, generic models and renderer, `ConfiguredDocuments` table, `python -m docfactory.generate_configured`; output byte-identical to Phase 4 for the same facts. `pyyaml` is now a runtime dependency.
- 2026-10-10: Class-based document generation removed (user decision, after a real-data comparison on the AI-Driven-Job-Matching-Platform SRS: identical `.md` files apart from stored dates, identical gap lists). Deleted `documentmodels/documents/` and `entitybound/`, `documentsaver/documents/`, `generation/doc_types.py`, `docfactory.generate`, `build_document` and `render_markdown`, and their tests; `generation/generate_document.py` became `generation_steps.py` (the steps both flows shared). The golden files are now rendered from the templates (`tests/test_golden_documents.py`); the seeds store their documents through the templates. Same day, second step (user decision): one document table. The parallel `ConfiguredDocuments` table, the `<App>.Configured.*` keys, `configrender/savers/` and `output/configured/` were folded into `DocumentOutputs`, `<App>.Outputs.*`, `documentsaver/` and `output/<App>/`; `documentmodels/` and `documentsaver/` are flat (no role folders); `doc_field` lost `binding`; the dev scripts and skills lost the document-model kind (`docfactory-create-document-model` removed). Then the real database was emptied and its migration code removed (`db.py` only creates the current schema; a database from an older build is not upgraded: delete it); `samples/output/` refreshed.
- 2026-10-10: Renamed the only generation approach (user decision): `configrender/` folded into `generation/` (template_loader, build_body, generate_document, render_document, document_store, template_gaps, revision_sources, `templates/`), `generate_configured` is `python -m docfactory.generate` again, `ConfiguredBody/Section/Field/BodySaver` are `DocumentBody/Section/Field/BodySaver`. Fixed the revision-history gap: a run that stopped between saving the body and its history now catches up on the next run (`history_is_behind`). The original SRS PDF was moved back to `incoming/` and `staging/`, `DocStore/`, `knowledgefacts/` and `output/` emptied; the database is empty.
- 2026-10-11: OKF bundle redesign (user decision: knowledge as plain OKF `.md` files, no SQLite, no savers; no hand edits, all input via `incoming/`; generated documents stay in `output/`; generation flow kept straightforward, optimization is the next activity). Built in six reviewed steps on branch `OkfBundleStore`: (1) `docfactory/bundle/` (fact registry, `BundleStore`, concept-file readers and writers, `index.md`, `log.md`); (2) facts and generation on the bundle (`build.load_fact`), seeds through `BundleStore`; (3) ingestion writes `<scope>/references/` and a Source concept (`SourceStore`, `SourceRecord`, `SourceChunk`), chunks re-derived on read (`source_reads`, `ChunksOutOfDateError`), `docstore_reads` replaced; (4) contributions as concepts (`ContributionStore`); (5) document state as JSON files (`DocumentStateStore`, `document_parts`), `DocumentOutputs` and the document savers removed; (6) `db.py`, `base_saver.py`, the 13 entity savers, `saver_resolution`, `fact_writer`, `fact_files` and `facts` removed; dev scripts and skills now register facts in `fact_registry.py` and generate `BundleStore` tests; tests, `CLAUDE.md`, `README.md` and this file rewritten; the real run migrated; `samples/` re-snapshotted as a bundle. Env `DOCFACTORY_DB`, `DOCFACTORY_DOCSTORE` and `DOCFACTORY_KNOWLEDGEFACTS` are gone, `DOCFACTORY_BUNDLE` is new; `pyyaml` is a runtime dependency; `run_extraction` takes the bundle path of the original (`<scope>/references/<file>`).
