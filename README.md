# docFactory

Keeps application documentation (Overview, SMTD, SRS, SOP) up to date from structured knowledge.

Knowledge is held as **validated JSON facts in SQLite**. Documents are **composed objects rendered to Markdown by deterministic code**. An LLM only does judgment work: tagging what the ontology rules cannot, and reading documents for facts. Everything else (validation, hashing, versions, files, rendering) is plain code.

`CLAUDE.md` is the authoritative spec. `STATUS.md` says where the project stands. This file is the map: the process and the commands.

Run every command from the project root (`C:\Users\Thinkpad\sourcecode\docFactory`).

## The process

```
 you drop a file
       |
       v
 incoming/ -> staging/  --(1 ingest: code chunks and tags,      DocStore/<scope>/<file>   tables: DocStore, DocStoreHistory,
                              LLM only for what rules miss)-->                              DocChunks, DocChunkTags
                                                              |
                                                              v
                                         (2 extract: LLM reads the text, calls the savers)
                                                              |
                                                              v
                    KnowledgeFacts (SQLite)  --(code)-->  bundles/<scope>/<Fact>.md        OKF v0.2 files
                    validated JSON, hash, version,                                         (views, never edited by hand)
                    completeness, trust, history
                                                              |
                                                              v
                                         (3 generate: index the frontmatter, LLM searches and reads facts,
                                          saves the document body)
                    document body + control + history  --(code)-->  output/<App>/<Doc>.md
```

| Step | Who does it | Status |
|---|---|---|
| 1. Ingest: chunk, tag and store originals | Code stages, chunks, tags against the ontology, decides the scope and stores; a small LLM fallback tags what the rules miss and places files the rules cannot | Built (Phase 2, redesigned) |
| 2. Extract: read a stored file and save facts | LLM reads and builds the call, savers validate and store | Built (Phase 3) |
| 3. Generate: build documents from the facts | LLM searches the knowledge (RAG over the frontmatter), reads the facts and builds the body; the document saver validates it, code renders it. The seed scripts remain the deterministic path | Built (Phase 4) |

### Ideas worth remembering

- **Facts are the source of truth.** `bundles/` and `output/` are views. Change the facts (or the models) and regenerate; never edit those files.
- **Only tools write.** A fact is saved only through a saver: invalid data is rejected with an error that says which field, what is valid and what to find out. Nothing is written on rejection.
- **Whole objects, hashed.** A save sends the complete fact. Same content again = `UNCHANGED`. Different content = `UPDATED`, version + 1, one row in `KnowledgeFactsHistory`. New title/tags/sources with the same content refresh the metadata and the bundle file but do not bump the version.
- **Never invented.** A field that is not stated stays at its default and does not count as answered. `Completeness` is answered fields / total fields.
- **LLM output is always `draft`.** `generated.by` is `okf-extraction-agent/<model>`, set by code. `verified` stays empty until a human approval exists (Phase 5).
- **Identity of a stored file = folder + file name.** Same name with new bytes replaces the file in place and bumps its version.

## One-time setup

1. Python 3.11 or newer. Runtime packages: `pydantic`, `pdfplumber`, `python-docx`, `beautifulsoup4`, `numpy`. For tests and the corpus: `pytest`, `reportlab`, `pyyaml`. (All listed in `pyproject.toml`.)
2. Copy `.env.example` to `.env` and fill it in (`.env` is gitignored):

   | Setting | Meaning |
   |---|---|
   | `DOCFACTORY_PROVIDER` | `ollama` (default) or `anthropic` |
   | `OLLAMA_HOST`, `OLLAMA_API_KEY` | `https://ollama.com` plus your key for Ollama Cloud; leave unset for a local Ollama |
   | `DOCFACTORY_MODEL` | model name. `gemma4:31b` (Ollama Cloud) worked well for both agents |
   | `DOCFACTORY_NUM_CTX` | Ollama context window. **Set `65536`** for extraction: its tool schemas alone are ~18k tokens, and the default 16384 is too small |
   | `DOCFACTORY_EMBED_MODEL` | Embedding model for the Phase 4 index, e.g. `mxbai-embed-large` or `nomic-embed-text` (`ollama pull <name>`) |
   | `DOCFACTORY_EMBED_HOST` | **Needed with Ollama Cloud:** it serves no embedding models, so point this at a local Ollama, e.g. `http://localhost:11434`. Your chat key is not sent there (`DOCFACTORY_EMBED_API_KEY` only if that server needs one) |

3. Shell variables win over `.env`. In PowerShell: `$env:DOCFACTORY_MODEL = "gemma4:31b"`.

## Everyday commands

### Step 1: ingest

```
copy "C:\path\to\My Document.pdf" incoming\
python -m docfactory.agents.run_ingestion
```

Every file in `incoming/` moves to `staging/` and is processed there:

1. **Lookup** by name and hash: `SAME` (already stored, copy discarded), `REPAIRED` (row existed but the stored file was missing), `CHANGED` (new revision of a stored file, version + 1), or `NEW`.
2. **Chunk** the original itself (PDF, Word, HTML, text): one chunk per section with its heading trail; table rows stay whole (`FR-85. | The system SHALL ...`).
3. **Tag** each chunk with the entities it informs, using the ontology (`docs/ontology.md`, signals in `docfactory/ontology/signals.json`). Chunks the rules cannot tag go to one small LLM call.
4. **Scope** (NEW files): from the document's title or document-control row, or `shared` when it only describes shared entities (SLOs, KPIs). If the rules are unsure, one small LLM call decides; if it is unsure too, the file waits in `staging/`.
5. **Move** the file to `DocStore/<scope>/` and store its chunks and tags in the database.

The report gives per file: outcome, scope, version, chunk count, entity -> chunk count (and how many the LLM tagged), unmapped chunks, and for a CHANGED file the entities to re-extract. Anything that needs your decision (unsure scope, duplicate content under another name, no extractable text) stays in `staging/` with the reason and is retried on the next run. `--no-llm` runs the rules only.

After changing the chunkers or the signals, re-chunk and re-tag everything stored (rules only):

```
python -m docfactory.ingest.chunk_rebuild
python -m docfactory.ontology.ontology_render     # regenerate docs/ontology.md after editing signals.json
```

### Step 2: extract

```
python -m docfactory.agents.run_extraction "ReadmeForge/ReadmeForge SRS v0.3.pdf"
```

The argument is the stored path under `DocStore/`, with forward slashes. The path above is an example from the test corpus; with a wrong path the command lists what is stored. The agent reads the text, then saves the facts the document supports under keys such as `ReadmeForge.FunctionalRequirements` or `Shared.Kpis`. Run it again for a new revision of the file: it updates the facts, and `KnowledgeFactsHistory` records who changed what and when. The summary lists what the document did not say.

### Step 3: generate

```
python -m docfactory.agents.run_generation ReadmeForge Overview
```

The arguments are the application name (as in the fact keys) and the document type: `Overview`, `SMTD`, `SRS` or `SOP`. The command first brings the frontmatter index up to date (only changed facts are embedded again), then the agent searches the knowledge, reads the facts it needs, builds the whole document body and saves it as `<App>.Outputs.<Type>`. It prints the saved version and completeness, and the agent's summary names the facts it relied on (flagging any `draft` or stale ones) and the fields no fact could fill. The body is validated by the document saver exactly like seed data. Document control and revision history are supplied by people, not generated: when both rows exist the command renders `output/<App>/<Type>.md`, otherwise it says "not rendered".

Rebuild the index on its own (for example after switching the embedding model, which re-embeds everything):

```
python -m docfactory.retrieval.index_rebuild
```

### Look at the results

| I want to... | Command or place |
|---|---|
| Read a fact | `bundles/<scope>/<Entity>.md` (YAML frontmatter, then the content) |
| See the stored facts | `python -c "from docfactory import facts; [print(f.key, 'v%d' % f.version, f.status.value, '%g%%' % f.completeness, f.generated_by) for f in facts.list_facts()]"` |
| One fact with its raw JSON | `python -c "from docfactory import facts; f = facts.get_fact('ReadmeForge.FunctionalRequirements'); print(f.value)"` |
| Which facts came from a file | `python -c "from docfactory import facts; print([f.key for f in facts.list_facts_by_source('ReadmeForge/ReadmeForge SRS v0.3.pdf')])"` |
| What was stored and when | `python -c "from docfactory import db; [print(r['FullPath'], 'v%d' % r['Version'], r['Timestamp']) for r in db.list_docstore_rows()]"` |
| The chunks of a stored file | `python -c "from docfactory import db; [print(c['ChunkNo'], c['Heading']) for c in db.list_doc_chunks('<scope>/<file>')]"` |
| Its entity tags | `python -c "from docfactory import db; [print(t['ChunkNo'], t['Entity'], t['Origin'], t['Evidence']) for t in db.list_doc_chunk_tags('<scope>/<file>')]"` |
| Change history of a fact | `python -c "from docfactory import db; print(db.list_fact_history('ReadmeForge.FunctionalRequirements'))"` |
| Check the bundle files are OKF v0.2 conformant | `python -m docfactory.okf_check` |
| Rebuild every bundle file from the database | `python -m docfactory.bundle_rebuild` |
| Rebuild the search index of the facts | `python -m docfactory.retrieval.index_rebuild` |
| Read a stored document body | `python -c "from docfactory import documents; d = documents.get_document('ReadmeForge.Outputs.Overview'); print(d.version, d.completeness)"` |

The database is `db/docfactory.sqlite` (gitignored). Any SQLite viewer works for reading it; never edit it by hand.

### The ReadmeForge sample (documents, no LLM)

Hard-coded seed data that builds and renders the four document types. This is the deterministic path; the Phase 4 agent produces the same kind of document body from the stored facts.

```
python -m seed.seed_readmeforge
python -m seed.seed_readmeforge_requirements
python -m seed.seed_readmeforge_smtd
python -m seed.seed_readmeforge_srs_sop
```

Results: facts in the database, bundle files under `bundles/ReadmeForge/` and `bundles/Shared/`, documents in `output/ReadmeForge/` (`Overview.md`, `SMTD.md`, `SOP.md`, plus `*.missing.json`, the questions about what is still unanswered).

### Tests

```
python -m pytest -q                                               # everything offline (about 1680 tests, under a minute)
python -m pytest -q tests/test_extraction_tools.py                # one file
python -m pytest -q -m live tests/test_live_ingestion.py          # real LLM, opt-in
python -m pytest -q -m live tests/test_live_extraction.py         # real LLM, opt-in (needs DOCFACTORY_NUM_CTX=65536)
python -m pytest -q -m live tests/test_live_generation.py         # real LLM and embedding model, opt-in (needs DOCFACTORY_EMBED_HOST on Ollama Cloud)
python .claude/scripts/check_structure.py                         # one-class-per-file and naming rules
```

Every test uses a temporary database, DocStore and bundle folder, so none touches your real data. The live tests skip themselves when the LLM server is unreachable. `tests/corpus/` holds deliberately messy sample originals (regenerate with `python tests/corpus/build_corpus.py`).

## Where things are

| Path | What it is |
|---|---|
| `incoming/` | Drop zone for new originals (gitignored) |
| `staging/` | Files being ingested, and files waiting for your decision (gitignored) |
| `DocStore/<scope>/` | Classified originals (gitignored); their chunks and tags are in the database |
| `docs/ontology.md` | The entities, their facts and the tagging signals (generated; edit `docfactory/ontology/signals.json`) |
| `db/docfactory.sqlite` | The database (gitignored) |
| `bundles/<scope>/` | One OKF markdown file per fact. Views, written by the savers only; gitignored |
| `output/<app>/` | Rendered documents. Views; gitignored |
| `samples/json/<entity>/` | Example JSON payloads, one folder per entity |
| `docs/okf/SPEC.md` | The OKF v0.2 specification (verbatim copy) |
| `docfactory/models/` | Machinery models (base model, `SaveResult`, `FactMeta`, ...) |
| `docfactory/entitymodels/` | What is known about an application: `facts/` (have a saver) and `items/` (nested types) |
| `docfactory/documentmodels/` | Documents, their sections and parts |
| `docfactory/entitysaver/`, `documentsaver/` | The savers: the only code that writes facts and documents |
| `docfactory/tools/`, `docfactory/agents/` | The tool packages (least privilege: one per agent) and the thin agent loops |
| `docfactory/retrieval/` | The search index over the facts' frontmatter: embedder and vector index (derived data, rebuildable) |
| `.claude/agents/` | Agent prompts. `docfactory-chunk-tagger-agent.md`, `docfactory-scope-agent.md` (ingestion fallback), `docfactory-okf-extraction-agent.md` and `docfactory-document-generator-agent.md` are the runtime prompts; edit them to tune behaviour |

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
| A file stays in `staging/` | The report says why: unsure scope, same content under another name, the name stored in several scopes, or no extractable text (a scanned PDF). Fix the cause and run ingestion again |
| Many chunks are unmapped | The ontology lacks this document's vocabulary: add heading terms or identifier patterns to `docfactory/ontology/signals.json`, then `python -m docfactory.ingest.chunk_rebuild` |
| A fact came back `REJECTED` | Read the errors: `path` is the field, `expected` what is valid, `question` what is missing. The extraction agent retries on its own; a persistent rejection means the document lacks the information |
| A bundle file is missing or stale | `python -m docfactory.bundle_rebuild` |
| `Ollama rejected the request (401)` from the index rebuild | Ollama Cloud has no embedding models. Set `DOCFACTORY_EMBED_HOST=http://localhost:11434` and a model you have pulled in `DOCFACTORY_EMBED_MODEL` |
| `Ollama returned 0 embeddings` / `is it an embedding model?` | `DOCFACTORY_EMBED_MODEL` is not an embedding model, or is not pulled on that host (`ollama list`) |
| The generator found no knowledge | Facts for that application must exist first (`list_facts`); run step 2 or the seeds |
| `okf_check` needs PyYAML | `pip install pyyaml` |

## What comes next

- **Phase 4: Generate. Built.** Known gaps: no MissingInfo list for agent-generated bodies (the summary names the gaps), and only the Overview has been run live.
- **Phase 5: Human in the loop.** Approval workflow (agents propose, humans approve, tools apply); this is what turns `draft` facts into `stable`.
- **Phase 3 (redesign next):** extraction will read the tagged chunks per entity (one fresh, small call per entity), instead of the whole document with every save tool at once.
- **Phase 6: Automate.** Watch `incoming/` and run the whole chain.
