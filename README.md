# docFactory

Keeps application documentation (Overview, SMTD, SRS, SOP) up to date from structured knowledge.

Knowledge is held as **validated JSON facts in SQLite**. Documents are **composed objects rendered to Markdown by deterministic code**. An LLM only does judgment work: tagging what the ontology rules cannot, filling small partial facts from a few chunks at a time, and phrasing a document's gaps as a list of questions. Everything else (validation, hashing, versions, files, document composition, rendering) is plain code.

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
                     (2 extract: per tagged entity, one small LLM call per batch of its chunks;
                      code merges batches and files, then calls the saver)   table: FactContributions
                                                              |
                                                              v
                    KnowledgeFacts (SQLite)
                    Value = validated entity JSON (the content), hash, version, completeness,
                    OKF v0.2 metadata columns (type, title, description, tags, sources, trust, lifecycle), history
                                                              |
                                                              v
                          (3 generate: code groups the facts' JSON by the template;
                           code keeps document control and revision history; one checked LLM call
                           turns the gaps into a needs list)          table: DocumentOutputs (4 rows per document)
                                                              |
                                                              v
                    output/<App>/<Doc>.md  +  output/<App>/<Doc>.missing.md (the questions to ask)
```

| Step | Who does it | Status |
|---|---|---|
| 1. Ingest: chunk, tag and store originals | Code stages, chunks, tags against the ontology, decides the scope and stores; a small LLM fallback tags what the rules miss and places files the rules cannot | Built (Phase 2, redesigned) |
| 2. Extract: turn a stored file's tagged chunks into facts | Code batches each entity's chunks; one small LLM call per batch returns a partial object; code checks it, merges batches and files, fills priorities from keywords and saves through the entity saver | Built (Phase 3, redesigned), verified on the real 50-page SRS |
| 3. Generate: build documents from the facts | Code copies the facts' JSON into the template (SRS first), writes the document control and revision history and renders the `.md`; one small LLM call, checked by code, turns what is missing into a list of questions | Built (Phase 4, reworked), verified on the real SRS of AI-Driven-Job-Matching-Platform |

### Ideas worth remembering

- **Facts are the source of truth.** A fact's content is the JSON its entity model validates; OKF is only the metadata in the same `KnowledgeFacts` row (there are no knowledge files). `output/` is a view. Change the facts (or the models) and regenerate; never edit those files.
- **Only tools write.** A fact is saved only through a saver: invalid data is rejected with an error that says which field, what is valid and what to find out. Nothing is written on rejection.
- **Whole objects, hashed.** A save sends the complete fact. Same content again = `UNCHANGED`. Different content = `UPDATED`, version + 1, one row in `KnowledgeFactsHistory`. New title/tags/sources with the same content refresh the metadata columns but do not bump the version.
- **A fact can come from several documents.** Each file's share is stored separately (`FactContributions`) and the fact is their merge, newest file first. Re-extracting a changed file replaces only its own share, so an item removed from that file disappears unless another file still states it. Disagreements are reported as conflicts, never silently resolved.
- **Never invented.** A field that is not stated stays at its default and does not count as answered. `Completeness` is answered fields / total fields.
- **Documents are views with their own control.** A document's body comes only from the facts; its document control (owner always `docFactory`, status `Draft`) and revision history (one entry per change of the body) are kept by the generate process, never taken from facts. Approvers arrive with the human approval (Phase 5).
- **LLM output is always `draft`.** `generated.by` is `okf-extraction-agent/<model>`, set by code. `verified` stays empty until a human approval exists (Phase 5).
- **Identity of a stored file = folder + file name.** Same name with new bytes replaces the file in place and bumps its version.

## One-time setup

1. Python 3.11 or newer. Runtime packages: `pydantic`, `pdfplumber`, `python-docx`, `beautifulsoup4`. For tests and the corpus: `pytest`, `reportlab`, `pyyaml`. (All listed in `pyproject.toml`.)
2. Copy `.env.example` to `.env` and fill it in (`.env` is gitignored):

   | Setting | Meaning |
   |---|---|
   | `DOCFACTORY_PROVIDER` | `ollama` (default) or `anthropic` |
   | `OLLAMA_HOST`, `OLLAMA_API_KEY` | `https://ollama.com` plus your key for Ollama Cloud; leave unset for a local Ollama |
   | `DOCFACTORY_MODEL` | model name. `gemma4:31b` (Ollama Cloud) worked well for both agents |
   | `DOCFACTORY_NUM_CTX` | Ollama context window, default 16384. Enough for extraction (one tool of at most ~1.5k tokens plus a 3500-character batch) |

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
python -m docfactory.agents.run_extraction "ReadmeForge/ReadmeForge SRS v0.3.pdf" --entity FunctionalRequirements
python -m docfactory.agents.run_extraction "ReadmeForge/ReadmeForge SRS v0.3.pdf" --entity Architecture --force
```

The argument is the stored path under `DocStore/`, with forward slashes; with a wrong path the command lists what is stored. Every entity tagged in the file is extracted (or only the ones named with `--entity`, repeatable):

1. **Key** from the file's folder: `<App>.<Entity>`. `Slo` and `Kpis` (shared facts) come only from files in `DocStore/shared/`; files in `general/` give no facts.
2. **Skip** when the entity's chunks are unchanged since its last extraction from this file: no LLM call. `--force` extracts anyway.
3. **Batches** of the entity's chunks (up to 3500 characters each), one fresh LLM call per batch with one tool, `submit_extraction`. The tool refuses invalid items, identifiers that are not in the chunks (the model may not number items), two items with one identifier, and placeholder text such as "N/A: not mentioned"; the model fixes and resubmits. A batch that fails is split in half and retried.
4. **Priorities**: a requirement whose priority is still empty gets the one its own keyword states: SHALL/MUST -> MUST, SHOULD -> SHOULD, MAY -> COULD.
5. **Merge and save**: the batch answers merge into this file's contribution, all files' contributions merge into the fact, and the entity saver validates and stores it (draft, `generated.by okf-extraction-agent/<model>`, sources = every contributing file).

The report gives per entity: outcome (`SAVED`, `UNCHANGED`, `SKIPPED_UNCHANGED_CHUNKS`, `SKIPPED_SCOPE`, `REMOVED`, `REJECTED`, `FAILED`), version and completeness, chunks, batches, items, priorities filled from keywords, and for review: batch problems, conflicts, values not found in the text, and the questions the fact still leaves open. Run it again after a new revision of the file: only entities whose chunks changed are extracted, and an entity no longer tagged loses this file's contribution (`REMOVED`). A `REJECTED` fact (for example an overview with no purpose yet) keeps the file's contribution, so a later document can complete it.

### Step 3: generate

```
python -m docfactory.generate AI-Driven-Job-Matching-Platform SRS
python -m docfactory.generate AI-Driven-Job-Matching-Platform all --no-llm
```

The arguments are the application name (as in the fact keys) and the document type: `Overview`, `SMTD`, `SRS`, `SOP` or `all`. Per document:

1. **Group**: the template (the document model) says which fact field fills each section; code copies those values from `<App>.<Entity>` and `Shared.<Entity>`. Nothing is rewritten or invented. A missing fact leaves its section `_Not provided._`; the document is always produced.
2. **Save** the body as `<App>.Outputs.<Type>` through its document saver (same facts = `UNCHANGED`).
3. **Document control and revision history**, written by code, never from facts: id `<App>-<Type>`, title, version `0.<body version>`, status `Draft`, owner `docFactory`, dates; one revision entry each time the body changes, naming the changed sections and the fact versions they came from. Approvers are added by the human approval (Phase 5).
4. **Needs list**: code lists the gaps (document fields no fact fills, and the open questions of the fact fields this template uses); one small LLM call merges and phrases them as questions grouped by who can answer, and code checks that every gap is covered and nothing is added. Unchanged gaps = no call; a failed call (or `--no-llm`) keeps the gaps themselves. Saved as `<App>.Outputs.<Type>.MissingInfo`.
5. **Render** `output/<App>/<Type>.md` and `output/<App>/<Type>.missing.md`.

Answer the questions by adding or revising a source document in `incoming/` and running steps 1-3 again; never edit the output.

The report gives per document: the body's action, version and completeness, the document version, the revision entry added (if any), and the number of gaps and needs with where the needs came from (`llm`, `fallback` with the reason, or `no_llm`; "unchanged gaps, no LLM call" when the stored list was kept). Running it again with unchanged facts changes no row, writes no file and makes no LLM call, so it is safe to run whenever facts may have changed.

On the real 50-page SRS of AI-Driven-Job-Matching-Platform: the body holds all 186 functional and 165 non-functional requirements (66% complete, `Shared.Slo` not stored yet), and the 11 gaps became 8 questions for the product owner, the architect and the service owner.

### Look at the results

| I want to... | Command or place |
|---|---|
| Read a fact | `python -c "from docfactory import facts; f = facts.get_fact('ReadmeForge.Architecture'); print(f.frontmatter); print(f.value)"` (OKF metadata, then the JSON content) |
| See the stored facts | `python -c "from docfactory import facts; [print(f.key, 'v%d' % f.version, f.status.value, '%g%%' % f.completeness, f.generated_by) for f in facts.list_facts()]"` |
| One fact with its raw JSON | `python -c "from docfactory import facts; f = facts.get_fact('ReadmeForge.FunctionalRequirements'); print(f.value)"` |
| Which facts came from a file | `python -c "from docfactory import facts; print([f.key for f in facts.list_facts_by_source('ReadmeForge/ReadmeForge SRS v0.3.pdf')])"` |
| What was stored and when | `python -c "from docfactory import db; [print(r['FullPath'], 'v%d' % r['Version'], r['Timestamp']) for r in db.list_docstore_rows()]"` |
| The chunks of a stored file | `python -c "from docfactory import db; [print(c['ChunkNo'], c['Heading']) for c in db.list_doc_chunks('<scope>/<file>')]"` |
| Its entity tags | `python -c "from docfactory import db; [print(t['ChunkNo'], t['Entity'], t['Origin'], t['Evidence']) for t in db.list_doc_chunk_tags('<scope>/<file>')]"` |
| What each file contributed to a fact | `python -c "from docfactory import contributions; [print(c.resource, c.generated_by, c.timestamp) for c in contributions.list_contributions('ReadmeForge.FunctionalRequirements')]"` |
| Change history of a fact | `python -c "from docfactory import db; print(db.list_fact_history('ReadmeForge.FunctionalRequirements'))"` |
| Rewrite every fact's JSON and open-questions file from the database | `python -m docfactory.fact_files` |
| Read a stored document body | `python -c "from docfactory import documents; d = documents.get_document('ReadmeForge.Outputs.Overview'); print(d.version, d.completeness)"` |

The database is `db/docfactory.sqlite` (gitignored). Any SQLite viewer works for reading it; never edit it by hand.

### The ReadmeForge sample (documents, no LLM)

Hard-coded seed data that builds and renders the four document types. The seeds supply their own document control and revision history; the golden files in `tests/golden/` are these outputs.

```
python -m seed.seed_readmeforge
python -m seed.seed_readmeforge_requirements
python -m seed.seed_readmeforge_smtd
python -m seed.seed_readmeforge_srs_sop
```

Results: facts in the database, documents in `output/ReadmeForge/` (`Overview.md`, `SMTD.md`, `SOP.md`, plus `*.missing.json`, the questions about what is still unanswered).

### Tests

```
python -m pytest -q                                               # everything offline (about 2010 tests, about a minute)
python -m pytest -q tests/test_extraction_pipeline.py             # one file
python -m pytest -q -m live tests/test_live_ingestion.py          # real LLM, opt-in
python -m pytest -q -m live tests/test_live_extraction.py         # real LLM, opt-in: corpus SRS, then its revision
python -m pytest -q -m live tests/test_live_generate.py           # real LLM, opt-in: the needs list of a small SRS
python .claude/scripts/check_structure.py                         # one-class-per-file and naming rules
```

Every test uses a temporary database and DocStore, so none touches your real data. The live tests skip themselves when the LLM server is unreachable. `tests/corpus/` holds deliberately messy sample originals (regenerate with `python tests/corpus/build_corpus.py`).

## Where things are

| Path | What it is |
|---|---|
| `incoming/` | Drop zone for new originals (gitignored) |
| `staging/` | Files being ingested, and files waiting for your decision (gitignored) |
| `DocStore/<scope>/` | Classified originals (gitignored); their chunks and tags are in the database |
| `docs/ontology.md` | The entities, their facts and the tagging signals (generated; edit `docfactory/ontology/signals.json`) |
| `db/docfactory.sqlite` | The database (gitignored) |
| `output/<app>/` | Rendered documents and their needs lists (`<Type>.missing.md`). Views; gitignored |
| `knowledgefacts/<scope>/` | One JSON file per fact (`ReadmeForge/Sop.json`, `Shared/Kpis.json`): the validated value, plus `<Entity>.missing.md` with the questions its unanswered fields ask and the default assumed meanwhile (no file when nothing is open). Views, written by the savers only; gitignored |
| `samples/json/<entity>/` | Example JSON payloads, one folder per entity |
| `docs/okf/SPEC.md` | The OKF v0.2 specification (verbatim copy) |
| `docfactory/models/` | Machinery models (base model, `SaveResult`, `FactMeta`, ...) |
| `docfactory/entitymodels/` | What is known about an application: `facts/` (have a saver) and `items/` (nested types) |
| `docfactory/documentmodels/` | Documents, their sections and parts |
| `docfactory/entitysaver/`, `documentsaver/` | The savers: the only code that writes facts and documents |
| `docfactory/tools/`, `docfactory/agents/` | The tool packages (least privilege: one per agent or call) and the thin agent loops |
| `docfactory/extract/` | Extraction code: batching, fact keys, partial models, merge, grounding checks, keyword priorities, missing-info questions, the pipeline |
| `docfactory/generation/`, `docfactory/generate.py` | Generation code: the document types, gaps, document control, revision history, the fallback needs list, the per-document flow; and its entry point |
| `.claude/agents/` | Agent prompts. `docfactory-chunk-tagger-agent.md`, `docfactory-scope-agent.md` (ingestion fallback), `docfactory-entity-extractor-agent.md` (extraction) and `docfactory-needs-list-agent.md` (generation) are the runtime prompts; edit them to tune behaviour |

Folders you can relocate with environment variables: `DOCFACTORY_DB`, `DOCFACTORY_INCOMING`, `DOCFACTORY_STAGING`, `DOCFACTORY_DOCSTORE`, `DOCFACTORY_KNOWLEDGEFACTS`, `DOCFACTORY_OUTPUT`.

## Changing the models

Entity and document models are created and changed through the project's skills so they come out uniform (one class per file, descriptions written for an LLM, tests with every class). In Claude Code:

- `/docfactory-create-entity-model`, `/docfactory-create-document-model`, `/docfactory-add-field`, `/docfactory-review-models`
- `/docfactory-create-shared-model` for machinery models

A model change changes what stored data means: update the tests and re-save the affected facts (re-run the seeds; `run_extraction --force` for extracted facts).

## When something goes wrong

| Symptom | Cause and fix |
|---|---|
| `model response was cut off (context or output limit, num_ctx=...)` | The context window is too small. Raise `DOCFACTORY_NUM_CTX` (e.g. `65536`) |
| Extraction report: `batch problems ... split and retried` | A batch's answer was too long for one reply; the halves were retried. Only a single chunk that still fails is a real failure, retried on the next run |
| `'...' is not in the DocStore` | Wrong path for `run_extraction`. Use the path printed in the list, forward slashes, relative to `DocStore/` |
| A file stays in `staging/` | The report says why: unsure scope, same content under another name, the name stored in several scopes, or no extractable text (a scanned PDF). Fix the cause and run ingestion again |
| Many chunks are unmapped | The ontology lacks this document's vocabulary: add heading terms or identifier patterns to `docfactory/ontology/signals.json`, then `python -m docfactory.ingest.chunk_rebuild` |
| An entity came back `REJECTED` | The merged fact misses a mandatory field (the report's save errors name it and the question). No document states it yet; the file's contribution is kept and the fact is saved once another document supplies it |
| Odd items in a fact (UI or training items as requirements) | Usually a wrong entity tag on a chunk. Check the tags (`db.list_doc_chunk_tags`) and the signals in `signals.json` |
| Generate report: `needs fallback: ...` | The needs-list call failed (the reason follows); the needs list holds one question per gap and the call is retried on the next run |
| `'<App>' has no knowledge facts` | Generate needs at least one fact for the application; the message lists the applications that have facts. Use the name exactly as in the fact keys |
| A document is mostly `_Not provided._` | Its facts are missing or empty; the `<Type>.missing.md` next to it says what to find out. Facts for that application must exist first (`list_facts`); run step 2 or the seeds |

## What comes next

- **Phase 5: Human in the loop. Pending.** Approval workflow (agents propose, humans approve, tools apply); this is what turns `draft` facts into `stable`, and where near-duplicate items and conflicts between documents get reviewed.
- **Phase 6: Automate. Pending.** Watch `incoming/` and run the whole chain.
