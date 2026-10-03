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
| 2 Ingest | **Done** (closed 2026-10-03) | Files arrive in `incoming/`, a live LLM agent (Ollama, default `gemma4:31b` on Ollama Cloud) classifies them into `DocStore/`. `DocStore` / `DocStoreHistory` track them (NEW / SAME / CHANGED, versions). Non-text files get a markitdown text sidecar. Verified live on `tests/corpus/`. |
| 3 Extract (OKF) | Planned (outline only) | Agent reads `DocStore` text and calls entity savers. `KnowledgeFacts` becomes OKF v0.2 compliant, with YAML-frontmatter files under `bundles/`. |
| 4 Generate | Planned (outline only) | Frontmatter indexed in a vector store, RAG finds relevant knowledge, a generator agent calls document savers. Rendering stays deterministic. |

- Triggers are manual for now. A watcher and automatic triggering are decided at the end of Phase 4 (or a Phase 5).
- Phases 3-4 are not designed in detail and must not be implemented yet.

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

- `.claude/agents/`: `docfactory-pydantic-developer-agent` (all models and savers go through it), `docfactory-sample-generator-agent`, `docfactory-ingestion-agent` (runtime prompt of the Phase 2 agent).
- `.claude/skills/`: entry skills (`docfactory-create-shared-model`, `docfactory-create-entity-model`, `docfactory-create-document-model`, `docfactory-add-field`, `docfactory-review-models`) and reference skills (`docfactory-field-spec`, `docfactory-quality-gate`).
- `.claude/scripts/`: deterministic scaffolding and gate scripts, tested in `tests/scripts/`.
- Other directories: `samples/`, `seed/` (ReadmeForge seed scripts), `tests/` (pytest, golden files), `output/<app>/`.

## Working rules

- Read `CLAUDE.md` first. Ask when something is unclear.
- Say so when a model change alters the meaning of stored data, and update tests and golden files in the same change.
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes.

## Current repo state

- Branch: `PydanticApproach` (main branch: `main`).
- Uncommitted: all Phase 2 work (see git status).

## Next up

- Phase 3 (Extract knowledge, OKF) design: not started. The Phase 2 corpus in `tests/corpus/` is the intended input.
- Before running the live test: put the key in `.env` (copy `.env.example`); no key is needed for a local Ollama.

## Change log

- 2026-10-03: Created from the project summary.
- 2026-10-03: Phase 2 closed. Added `ingest/`, `tools/` (registry, packages, ingestion package), `agents/` (provider-neutral model client, Ollama default, ingestion loop), `DocStore` tables, `.env` loading, test corpus and an opt-in live test.
