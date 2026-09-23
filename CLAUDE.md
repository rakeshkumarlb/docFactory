# docFactory

Agent system that keeps application documentation up to date as new information arrives (call transcripts, emails, specs, READMEs, answers). It runs from this folder using Claude Code (or GitHub Copilot) agents plus small deterministic Python scripts. Text-based files only (`.md`, `.txt`, `.eml` as text, transcripts, `.csv`, code docs). Convert Word/PDF to text first.

## Principles

1. **`knowledge/<app>/` is the source of truth.** Generated documents are views of it, never the other way round.
2. **Every fact has provenance.** A fact bullet always links to the store document it came from.
3. **Agents propose, humans approve, scripts apply.** No agent edits `knowledge/` directly. Every merge waits for explicit approval.
4. **Scripts do all deterministic work** (hashing, filing, versioning, SQL, template assembly, completeness %, linting). Scripts are generic and know nothing template- or app-specific. Agents do only judgment work: classify, extract, draft, word questions.
5. **Never silently guess.** Unknown app -> `_unclassified`. Contradiction -> conflict entry. Missing information -> MissingInfo file.
6. **Nothing is destroyed.** Replaced/deleted store files are archived; every change is in the SQLite log.

## Pipeline

```
incoming/  --/ingest-->  store/  --/extract-->  review/ (proposal)  --you approve-->  knowledge/<app>/
                                                                                        |
templates/<TYPE>/  --compose.py-->  output/<app>/<DocID>-*.md  <--/generate--------------+
                                    output/<app>/<DocID>-*-MissingInfo.md --you answer--> incoming/  (loop)
```

Nothing runs in the background: agents run when a command is invoked (`/ingest`, `/extract`, `/approve`, `/generate`, `/new-template`, `/status`). Run `python tools/db.py status` any time.

## Repo layout

```
incoming/                    Drop zone: new facts AND answers to MissingInfo files
store/<app>/<category>/...   Current documents. category = calls | emails | docs | answers
store/_unclassified/         Ingestion could not decide; needs a human
store/_archive/              Superseded/deleted versions (timestamped)
knowledge/<app>/             Source of truth per application (see below)
review/<app>/                Knowledge proposals: P-<app>-<date>-<nn>.json (+ .md rendering)
templates/_shared/           Fragments reused by many templates
templates/<TYPE>/            template.json + sections/ fragments
output/<app>/                Generated documents and their -MissingInfo files
db/docfactory.sqlite         Registry + change log (created by tools/db.py)
tools/                       Deterministic Python scripts (stdlib only)
.claude/agents/              Agent definitions (ingestion, knowledge-extractor, template-designer, doc-generator)
.claude/commands/            Slash commands
.github/copilot-instructions.md   Points Copilot at this file
```

## Knowledge base structure (per application, a group of small files)

```
knowledge/<app>/
  _index.md        Short app description + auto-generated file map (facts/lines per file). ALWAYS read first.
  conflicts.md     Open/resolved contradictions
  history.md       Append-only log of every applied proposal (incl. old text of refined facts)
  overview.md actors.md functional.md nonfunctional.md integrations.md data.md components.md
  decisions.md open-questions.md glossary.md
  operations.md sre.md monitoring.md incidents.md dependencies.md repositories.md
  cicd.md releases.md security.md dr.md                    (all created on demand; names match the templates' `source=`)
  components/<component>/<same topics>.md     for multi-component apps (e.g. KitchenHQ: dbmcp, agents, chatui, shared)
```

- Agents read `_index.md` then only the topic files they need, so context stays small however big the app gets.
- Split rule: a file over 300 lines or 60 active facts is flagged "split suggested" in `_index.md` (`python tools/kb.py stats <app>`). New facts then go to a themed file such as `functional--chat.md`. Fact ids are per app, stable and never reused, so moving facts between files is safe.
- A fact is one bullet: `- [F-0042] Unread badge is shown per chat thread. — src: store/kitchenhq/calls/2026-09-23-chat-review.md; store/...`
- Obsolete facts are struck through with reason and source, not deleted: `- ~~[F-0042] text~~ (obsolete 2026-10-01: reason; src: ...)`.
- Multi-component apps: single-service/whole-app facts go in the top-level topic files; component-specific facts in `components/<name>/`.

## Agents

Definitions in `.claude/agents/`; each command invokes one. Read the definition before acting as that agent.

| Agent | Command | Does | Never does |
|---|---|---|---|
| `ingestion` | `/ingest` | Reads `incoming/`, decides app/category/name, files via `store_file.py` | guess unclear files; move files by hand; write SQL |
| `knowledge-extractor` | `/extract` | Reads new/changed store docs, writes a proposal (add/confirm/refine/conflict/obsolete ops) and submits it for review | edit `knowledge/`; apply its own proposal; resolve conflicts |
| (you) | `/approve` | Approve/reject a proposal or resolve a conflict (`kb.py apply/reject/resolve`) | |
| `template-designer` | `/new-template` | Helps design templates as fragments; validates with `compose.py --check` | hard-code template logic into tools |
| `doc-generator` | `/generate` | Composes skeleton, fills from knowledge, produces MissingInfo, scores, lints, registers | invent content to raise completeness |

## Approval gate (knowledge merges)

1. `/extract` writes `review/<app>/<id>.json` and runs `kb.py submit` (validates; refuses unknown facts, bad files, sources not in store).
2. The user reads the rendering (ADD / CONFIRM / REFINE / CONFLICT / OBSOLETE with before/after text).
3. Only on the user's explicit say-so: `python tools/kb.py apply <id> --approved-by <name>`. `apply` refuses if the proposal is not pending or the source document changed since (stale). Conflict ops never touch the existing fact; they land in `conflicts.md` until `kb.py resolve`.
4. Rejecting marks the source as processed with no change. Both outcomes are logged.

## Templates (decoupled, generic)

A template is a folder, not a file:

```
templates/SRS/template.json          {type, title, version, numbering, sections:[fragment paths in order]}
templates/SRS/sections/*.md          fragments (any size: one field or a whole chapter)
templates/SRS/sections/03-specific/  sub-fragments pulled in by a parent fragment
templates/_shared/*.md               document-control, revision-history, glossary, references, sources
```

Fragment syntax (this is the whole "language"; `tools/compose.py` implements only this):
- `<!-- include: path shift=1 -->` include another fragment. Path is relative to the including file; `@/` means `templates/`. `shift` demotes its headings so one fragment can sit at any depth. Cycles/missing files are errors.
- A fillable heading has one directive directly under it and no body text:
  `<!-- field id=srs.purpose required=yes na=no source=overview hint="what a good answer contains" -->`
  - `id` unique per composed document, stable forever (answers/questions are keyed on it)
  - `required` yes|no - only required fields count toward completeness
  - `na` allowed|no - whether "N/A - reason" is a legal answer
  - `source` knowledge topic that normally answers it; `hint` doubles as the question when info is missing
- Headings without a directive are pure structure. `numbering: true` auto-numbers headings (1, 1.1, 1.1.1) at compose time, so fragments are never renumbered by hand.

Field outcomes in a generated document: content, `N/A - <reason>`, `PARTIAL - ...`, `MISSING (see Q-...)`. Completeness % = (filled + 0.5 x partial) / (required fields - required N/A). Optional fields never reduce it.

Managing templates: change fragments, not generated docs; bump `version` in `template.json` for any structural change. A generated doc records `template_version` and `template_hash`, so `lint_doc.py` reports drift. Sample templates: BRD, SRS, SOP, SMTD.

**SMTD = Software Maintenance Technical Document**: everything a maintenance/support team needs to run an application in production. 12 chapters / 65 fields: support model and escalation; SLA/SLIs/SLOs, error budget, MTTD/MTTA/MTTR/MTBF, severity definitions; architecture and environments; upstream/downstream dependencies and failure impact; code/artifact/config repositories; CI/CD pipelines, releases, deployment strategy, rollback; monitoring, logging and configured alerts; incident SOPs, known errors, diagnostics; routine operations and scheduled jobs; security; backup, RTO/RPO and DR; risks and roadmap. Most of this rarely appears in READMEs, so expect low completeness and a long MissingInfo file the first time; that file is the checklist for gathering it from the ops/SRE team.

## Tools (`tools/`, Python 3, stdlib only; run from repo root as `python tools/<x>.py`)

| Script | Purpose |
|---|---|
| `store_file.py` | File a doc into `store/`: SHA-256 dedupe, ADD/UPDATE(archive old, version+1)/DUPLICATE/DELETE, DB log |
| `db.py` | Schema, `status`, `pending-extraction`, `find`, `history`, `next-id`, `register-output`, `stale-outputs` |
| `kb.py` | `submit/show/apply/reject/resolve` proposals, `facts`, `stats`, `reindex`, `new-app` |
| `compose.py` | Assemble a template into a document skeleton; `--check` validates a template; `--list` |
| `completeness.py` | Field statuses and % from a generated doc; `--write` stores it in front matter |
| `missing_info.py` | Mark gaps in the doc and write `<doc>-MissingInfo.md` with stable `Q-<DocID>-<nn>` ids |
| `lint_doc.py` | Doc still matches its template exactly; Sources links resolve; no invalid N/A |

SQLite tables: `documents` (path, sha256, version, is_answer, extracted_sha), `changes` (append-only log: ADD/UPDATE/DUPLICATE/DELETE/KNOWLEDGE/REJECT/RESOLVE/OUTPUT), `proposals`, `counters` (fact/conflict/doc ids), `outputs`, `output_sources` (sha of each source at generation time -> `stale-outputs` lists generated docs whose sources have since changed, i.e. what needs regenerating).

Env `DOCFACTORY_ROOT` points every script at another root (used for testing without touching real data).

## Formats

Generated doc front matter: `doc_id, title, app, template, template_version, template_hash, generated, status, completeness, completeness_detail`. The last section is always **Sources**: relative links to the store documents used.

MissingInfo file: one `## Q-<DocID>-<nn>  (field: <id> - <heading>)` entry each with Status/Hint/Question/Suggested source/`Answer:`. To answer: fill `Answer:` lines, save into `incoming/` with first line `MissingInfo-Ref: <DocID>`. Ingestion files it as an answer; extraction turns answers into facts (proposal, approval), and the next `/generate` fills the fields.

## Working rules

- Read this file, then `knowledge/<app>/_index.md`, before doing anything for an app.
- Never edit `store/` by hand (use `store_file.py`) or `knowledge/` by hand (use proposals). Never edit generated docs' headings/directives.
- If uncertain (app identity, classification, conflict), stop and ask or park it.
- Dates are ISO `YYYY-MM-DD`. Paths in documents are relative with forward slashes. IDs: `F-nnnn` facts, `C-nnnn` conflicts, `P-...` proposals, `<PREFIX><n>` documents.
- Keep the repo in git once initialised so knowledge changes are diffable and revertible.

## Copilot compatibility

`.github/copilot-instructions.md` tells Copilot to follow this file and the role files in `.claude/agents/`. Mirror them as `.github/agents/*.agent.md` / `.github/prompts/*.prompt.md` if you want Copilot slash prompts. All logic lives in `tools/`, so both assistants behave the same.

## Limits

- Manual trigger: "arrives in incoming" means "processed at next `/ingest`". A scheduled `claude -p "/ingest"` can automate ingestion and proposal drafting; approval stays human.
- Text only; scanned PDFs, audio and Office files need conversion outside this system.
- LLM extraction is fallible; provenance, the approval gate, `history.md` and the change log exist so anything can be audited and reverted.
