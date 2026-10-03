# docFactory

Keeps application documentation (Overview, SMTD, SRS, SOP) up to date from structured knowledge.

Knowledge is held as **validated JSON facts in SQLite**. Documents are **composed objects rendered to Markdown by deterministic code**. An LLM only does judgment work: sorting incoming files and reading them for facts. Everything else (validation, hashing, versions, files, rendering) is plain code.

`CLAUDE.md` is the authoritative spec. `STATUS.md` says where the project stands. This file is the map: the process and the commands.

Run every command from the project root (`C:\Users\Thinkpad\sourcecode\docFactory`).

## The process

```
 you drop a file
       |
       v
 incoming/  --(1 ingest: LLM classifies, code moves)-->  DocStore/<scope>/<file>      tables: DocStore, DocStoreHistory
                                                              |  (+ a .md text sidecar for PDF/Word/HTML)
                                                              v
                                         (2 extract: LLM reads the text, calls the savers)
                                                              |
                                                              v
                    KnowledgeFacts (SQLite)  --(code)-->  bundles/<scope>/<Fact>.md        OKF v0.2 files
                    validated JSON, hash, version,                                         (views, never edited by hand)
                    completeness, trust, history
                                                              |
                                                              v
                                         (3 generate: Phase 4, not built yet)
                    documents built from facts  --(code)-->  output/<App>/<Doc>.md
```

| Step | Who does it | Status |
|---|---|---|
| 1. Ingest: sort originals into `DocStore/` | LLM classifies, code moves, hashes and records | Built (Phase 2) |
| 2. Extract: read a stored file and save facts | LLM reads and builds the call, savers validate and store | Built (Phase 3) |
| 3. Generate: build documents from the facts | Today only for the ReadmeForge sample, by seed scripts. The agent that does this for any application is Phase 4 | Phase 1 sample only |

### Ideas worth remembering

- **Facts are the source of truth.** `bundles/` and `output/` are views. Change the facts (or the models) and regenerate; never edit those files.
- **Only tools write.** A fact is saved only through a saver: invalid data is rejected with an error that says which field, what is valid and what to find out. Nothing is written on rejection.
- **Whole objects, hashed.** A save sends the complete fact. Same content again = `UNCHANGED`. Different content = `UPDATED`, version + 1, one row in `KnowledgeFactsHistory`. New title/tags/sources with the same content refresh the metadata and the bundle file but do not bump the version.
- **Never invented.** A field that is not stated stays at its default and does not count as answered. `Completeness` is answered fields / total fields.
- **LLM output is always `draft`.** `generated.by` is `okf-extraction-agent/<model>`, set by code. `verified` stays empty until a human approval exists (Phase 5).
- **Identity of a stored file = folder + file name.** Same name with new bytes replaces the file in place and bumps its version.

## One-time setup

1. Python 3.11 or newer. Runtime packages: `pydantic`, `markitdown[pdf,docx]`. For tests and the corpus: `pytest`, `reportlab`, `python-docx`, `pyyaml`. (All listed in `pyproject.toml`.)
2. Copy `.env.example` to `.env` and fill it in (`.env` is gitignored):

   | Setting | Meaning |
   |---|---|
   | `DOCFACTORY_PROVIDER` | `ollama` (default) or `anthropic` |
   | `OLLAMA_HOST`, `OLLAMA_API_KEY` | `https://ollama.com` plus your key for Ollama Cloud; leave unset for a local Ollama |
   | `DOCFACTORY_MODEL` | model name. `gemma4:31b` (Ollama Cloud) worked well for both agents |
   | `DOCFACTORY_NUM_CTX` | Ollama context window. **Set `65536`** for extraction: its tool schemas alone are ~18k tokens, and the default 16384 is too small |

3. Shell variables win over `.env`. In PowerShell: `$env:DOCFACTORY_MODEL = "gemma4:31b"`.

## Everyday commands

### Step 1: ingest

```
copy "C:\path\to\My Document.pdf" incoming\
python -m docfactory.agents.run_ingestion
```

The agent lists `incoming/`, reads each file, picks a scope folder (an application name, `shared` or `general`), compares with what is stored (`NEW`, `SAME`, `CHANGED`) and stores it. A file it cannot place confidently stays in `incoming/` with a stated reason: you decide. The summary at the end gives scope, outcome and version per file.

Regenerate all text sidecars from the stored originals (for example after a converter upgrade):

```
python -m docfactory.ingest.sidecar_rebuild
```

### Step 2: extract

```
python -m docfactory.agents.run_extraction "ReadmeForge/ReadmeForge SRS v0.3.pdf"
```

The argument is the stored path under `DocStore/`, with forward slashes. The path above is an example from the test corpus; with a wrong path the command lists what is stored. The agent reads the text, then saves the facts the document supports under keys such as `ReadmeForge.FunctionalRequirements` or `Shared.Kpis`. Run it again for a new revision of the file: it updates the facts, and `KnowledgeFactsHistory` records who changed what and when. The summary lists what the document did not say.

### Look at the results

| I want to... | Command or place |
|---|---|
| Read a fact | `bundles/<scope>/<Entity>.md` (YAML frontmatter, then the content) |
| See the stored facts | `python -c "from docfactory import facts; [print(f.key, 'v%d' % f.version, f.status.value, '%g%%' % f.completeness, f.generated_by) for f in facts.list_facts()]"` |
| One fact with its raw JSON | `python -c "from docfactory import facts; f = facts.get_fact('ReadmeForge.FunctionalRequirements'); print(f.value)"` |
| Which facts came from a file | `python -c "from docfactory import facts; print([f.key for f in facts.list_facts_by_source('ReadmeForge/ReadmeForge SRS v0.3.pdf')])"` |
| What was stored and when | `python -c "from docfactory import db; [print(r['FullPath'], 'v%d' % r['Version'], r['Timestamp']) for r in db.list_docstore_rows()]"` |
| Change history of a fact | `python -c "from docfactory import db; print(db.list_fact_history('ReadmeForge.FunctionalRequirements'))"` |
| Check the bundle files are OKF v0.2 conformant | `python -m docfactory.okf_check` |
| Rebuild every bundle file from the database | `python -m docfactory.bundle_rebuild` |

The database is `db/docfactory.sqlite` (gitignored). Any SQLite viewer works for reading it; never edit it by hand.

### The ReadmeForge sample (documents, no LLM)

Hard-coded seed data that builds and renders the four document types. This is the deterministic path the Phase 4 agent will later feed.

```
python -m seed.seed_readmeforge
python -m seed.seed_readmeforge_requirements
python -m seed.seed_readmeforge_smtd
python -m seed.seed_readmeforge_srs_sop
```

Results: facts in the database, bundle files under `bundles/ReadmeForge/` and `bundles/Shared/`, documents in `output/ReadmeForge/` (`Overview.md`, `SMTD.md`, `SOP.md`, plus `*.missing.json`, the questions about what is still unanswered).

### Tests

```
python -m pytest -q                                               # everything offline (about 1580 tests, under a minute)
python -m pytest -q tests/test_extraction_tools.py                # one file
python -m pytest -q -m live tests/test_live_ingestion.py          # real LLM, opt-in
python -m pytest -q -m live tests/test_live_extraction.py         # real LLM, opt-in (needs DOCFACTORY_NUM_CTX=65536)
python .claude/scripts/check_structure.py                         # one-class-per-file and naming rules
```

Every test uses a temporary database, DocStore and bundle folder, so none touches your real data. The live tests skip themselves when the LLM server is unreachable. `tests/corpus/` holds deliberately messy sample originals (regenerate with `python tests/corpus/build_corpus.py`).

## Where things are

| Path | What it is |
|---|---|
| `incoming/` | Drop zone for new originals (gitignored) |
| `DocStore/<scope>/` | Classified originals plus text sidecars (gitignored) |
| `db/docfactory.sqlite` | The database (gitignored) |
| `bundles/<scope>/` | One OKF markdown file per fact. Views, written by the savers only |
| `output/<app>/` | Rendered documents. Views |
| `samples/<entity>/` | Example JSON payloads, one folder per entity |
| `docs/okf/SPEC.md` | The OKF v0.2 specification (verbatim copy) |
| `docfactory/models/` | Machinery models (base model, `SaveResult`, `FactMeta`, ...) |
| `docfactory/entitymodels/` | What is known about an application: `facts/` (have a saver) and `items/` (nested types) |
| `docfactory/documentmodels/` | Documents, their sections and parts |
| `docfactory/entitysaver/`, `documentsaver/` | The savers: the only code that writes facts and documents |
| `docfactory/tools/`, `docfactory/agents/` | The tool packages (least privilege: one per agent) and the thin agent loops |
| `.claude/agents/` | Agent prompts. `docfactory-ingestion-agent.md` and `docfactory-okf-extraction-agent.md` are the runtime prompts; edit them to tune behaviour |

Folders you can relocate with environment variables: `DOCFACTORY_DB`, `DOCFACTORY_INCOMING`, `DOCFACTORY_DOCSTORE`, `DOCFACTORY_BUNDLES`.

## Changing the models

Entity and document models are created and changed through the project's skills so they come out uniform (one class per file, descriptions written for an LLM, tests with every class). In Claude Code:

- `/docfactory-create-entity-model`, `/docfactory-create-document-model`, `/docfactory-add-field`, `/docfactory-review-models`
- `/docfactory-create-shared-model` for machinery models

A model change changes what stored data means: update the tests and regenerate the bundles (`python -m docfactory.bundle_rebuild`).

## When something goes wrong

| Symptom | Cause and fix |
|---|---|
| `model response was cut off (context or output limit, num_ctx=...)` | The context window is too small. Set `DOCFACTORY_NUM_CTX=65536` |
| `'...' is not in the DocStore` | Wrong path for `run_extraction`. Use the path printed in the list, forward slashes, relative to `DocStore/` |
| The agent deferred a file | It could not classify it confidently, and the file stays in `incoming/` with the reason in the summary. Fix the cause (for example a clearer file name) and run ingestion again, or decide the scope yourself |
| A fact came back `REJECTED` | Read the errors: `path` is the field, `expected` what is valid, `question` what is missing. The extraction agent retries on its own; a persistent rejection means the document lacks the information |
| A bundle file is missing or stale | `python -m docfactory.bundle_rebuild` |
| `okf_check` needs PyYAML | `pip install pyyaml` |

## What comes next

- **Phase 4: Generate.** Index the fact frontmatter for retrieval, let an agent assemble documents from the facts, then render them deterministically.
- **Phase 5: Human in the loop.** Approval workflow (agents propose, humans approve, tools apply); this is what turns `draft` facts into `stable`.
- **Phase 6: Automate.** Watch `incoming/` and run the whole chain.
