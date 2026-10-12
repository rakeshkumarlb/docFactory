# docFactory

Keeps application documentation (Overview, SMTD, SRS, SOP) up to date from structured knowledge.

Knowledge is held as an **OKF bundle**: plain Markdown files with YAML frontmatter, each carrying the **validated JSON of one fact** in its body. Documents are **composed objects rendered to Markdown by deterministic code**. There is no database. An LLM only does judgment work: tagging what the ontology rules cannot, filling small partial facts from a few chunks at a time, and phrasing a document's gaps as a list of questions. Everything else (validation, hashing, versions, files, document composition, rendering) is plain code.

`CLAUDE.md` is the authoritative spec. `STATUS.md` says where the project stands. This file is the map: the process and the commands.

Run every command from the project root (`C:\Users\Thinkpad\sourcecode\docFactory`).

## The process

```
 you drop a file
       |
       v
 incoming/ -> staging/  --(1 ingest: code chunks and tags,      bundle/<scope>/references/<file>   the original
                              LLM only for what rules miss)-->   bundle/<scope>/sources/<file>.md   hash, version, chunk outline, tags
                                                              |
                                                              v
                     (2 extract: per tagged entity, one small LLM call per batch of its chunks;
                      code merges batches and files, then writes the fact)
                           bundle/<scope>/sources/<file>/<Entity>.md   what this file stated (a contribution)
                                                              |
                                                              v
                    bundle/<Scope>/<Entity>.md      one OKF concept file per fact:
                    frontmatter (type, title, description, tags, sources, trust, lifecycle, version, hash, completeness),
                    the validated JSON under "# Value", the unanswered fields under "# Open questions"
                    + bundle/index.md and bundle/log.md
                                                              |
                                                              v
                          (3 generate: code reads the bound facts' JSON from the bundle and groups it by the template;
                           code keeps document control and revision history; one checked LLM call
                           turns the gaps into a needs list)     output/<App>/state/<Doc>.<part>.json (4 files per document)
                                                              |
                                                              v
                    output/<App>/<Doc>.md  +  output/<App>/<Doc>.missing.md (the questions to ask)
```

| Step | Who does it | Status |
|---|---|---|
| 1. Ingest: chunk, tag and store originals | Code stages, chunks, tags against the ontology, decides the scope and stores; a small LLM fallback tags what the rules miss and places files the rules cannot | Built (Phase 2) |
| 1b. Recognize: entities and relationships across all documents | One small LLM call per word-capped window of whole sections, with the entities already known in view; one resolution call per type finds duplicates; code merges everything into the entity graph | Built, verified on the 15 JobMatch documents |
| 2. Extract: turn a stored file's tagged chunks into facts | Code batches each entity's chunks; one small LLM call per batch returns a partial object; code checks it, merges batches and files, fills priorities from keywords and writes the fact | Built (Phase 3), verified on the real 50-page SRS |
| 2c. Entity items: one item per recognized entity | One small LLM call per entity over its chunks in every document and its neighbours' chunks; code sets name, evidence, relations | Built, verified on the 15 JobMatch documents |
| 3. Generate: build documents from the facts | Code copies the facts' JSON into the template (SRS first), writes the document control and revision history and renders the `.md`; one small LLM call, checked by code, turns what is missing into a list of questions | Built (Phase 4), verified on the real SRS of AI-Driven-Job-Matching-Platform |

### Ideas worth remembering

- **Facts are the source of truth, and they are plain files.** A fact's content is the JSON its entity model validates; OKF is the frontmatter around it. `output/` is a view. Change the facts (or the models) and regenerate; never edit those files.
- **Only the stores write, and nobody edits by hand.** A fact is written only through `BundleStore`: invalid data is rejected with an error that says which field, what is valid and what to find out, and nothing is written. All new input arrives as files in `incoming/`. A file whose JSON no longer matches its stored hash is refused on read.
- **Whole objects, hashed.** A save sends the complete fact. Same content again = `UNCHANGED`. Different content = `UPDATED`, version + 1, one line in `bundle/log.md`. New title/tags/sources with the same content refresh the metadata but do not bump the version. Keep `bundle/` in its own git repository to keep the old values too.
- **A fact can come from several documents.** Each file's share is stored separately (a contribution file beside its source) and the fact is their merge, newest file first. Re-extracting a changed file replaces only its own share, so an item removed from that file disappears unless another file still states it. Disagreements are reported as conflicts, never silently resolved.
- **Never invented.** A field that is not stated stays at its default and does not count as answered. `completeness` is answered fields / total fields.
- **Documents are views with their own control.** A document's body comes only from the facts; its document control (owner always `docFactory`, status `Draft`) and revision history (one entry per change of the body) are kept by the generate process, never taken from facts. Approvers arrive with the human approval (Phase 5).
- **LLM output is always `draft`.** `generated.by` is `okf-extraction-agent/<model>`, set by code. `verified` stays empty until a human approval exists (Phase 5).
- **Identity of an ingested file = scope folder + file name.** Same name with new bytes replaces the file in place and bumps its version.
- **Chunks are not stored.** Chunking is deterministic, so extraction re-derives them from the original and checks them against the outline in the Source file.

## One-time setup

1. Python 3.11 or newer. Runtime packages: `pydantic`, `pyyaml`, `pdfplumber`, `python-docx`, `beautifulsoup4`. For tests and the corpus: `pytest`, `reportlab`. (All listed in `pyproject.toml`.)
2. Copy `.env.example` to `.env` and fill it in (`.env` is gitignored):

   | Setting | Meaning |
   |---|---|
   | `DOCFACTORY_PROVIDER` | `ollama` (default) or `anthropic` |
   | `OLLAMA_HOST`, `OLLAMA_API_KEY` | `https://ollama.com` plus your key for Ollama Cloud; leave unset for a local Ollama |
   | `DOCFACTORY_MODEL` | model name. `gemma4:31b` (Ollama Cloud) is the model in use and works for every call |
   | `DOCFACTORY_NUM_CTX` | Ollama context window, default 16384. Enough for extraction calls; recognition (a 2000-word window plus the vocabulary and up to 200 catalog entities) wants 65536, the value in use |
   | `DOCFACTORY_WORD_CAP` | words per recognition window and per entity's evidence, default 2000 |
   | `DOCFACTORY_CATALOG_MAX` | entities shown to a recognition call, default 200 (the most relevant first) |
   | `DOCFACTORY_USAGE_LOG` | optional file: every model call appends one JSON line (step, prompt and output tokens); summarise with `python -m docfactory.agents.run_usage <file>` |

3. Shell variables win over `.env`. In PowerShell: `$env:DOCFACTORY_MODEL = "gemma4:31b"`.

## Everyday commands

### Step 1: ingest

```
copy "C:\path\to\My Document.pdf" incoming\
python -m docfactory.agents.run_ingestion
```

Every file in `incoming/` moves to `staging/` and is processed there:

1. **Lookup** by name and hash among the Source files of the bundle: `SAME` (already stored, copy discarded), `REPAIRED` (the Source existed but the stored original was missing), `CHANGED` (new revision of a stored file, version + 1), or `NEW`.
2. **Chunk** the original itself (PDF, Word, HTML, text): one chunk per section with its heading trail; table rows stay whole (`FR-85. | The system SHALL ...`).
3. **Tag** each chunk with the entities it informs, using the ontology (`docs/ontology.md`, signals in `docfactory/ontology/signals.json`). Chunks the rules cannot tag go to one small LLM call.
4. **Scope** (NEW files): from the document's title or document-control row, or `shared` when it only describes shared entities (SLOs, KPIs). If the rules are unsure, one small LLM call decides; if it is unsure too, the file waits in `staging/`.
5. **Move** the file to `bundle/<scope>/references/` and write its Source file `bundle/<scope>/sources/<file>.md` (hash, version, the chunk outline and the tags; no chunk text).

The report gives per file: outcome, the bundle path (`<scope>/references/<file>`, which step 2 takes as its argument), version, chunk count, entity -> chunk count (and how many the LLM tagged), unmapped chunks, and for a CHANGED file the entities to re-extract. Anything that needs your decision (unsure scope, duplicate content under another name, no extractable text) stays in `staging/` with the reason and is retried on the next run. `--no-llm` runs the rules only.

After changing the chunkers or the signals, re-chunk and re-tag everything stored (rules only):

```
python -m docfactory.ingest.chunk_rebuild
python -m docfactory.ontology.ontology_render     # regenerate docs/ontology.md after editing signals.json
```

If extraction stops with `no longer chunks as it did at ingestion`, run `chunk_rebuild` (the chunkers changed since the file was ingested).

### Step 1b: recognize entities and relationships

```
python -m docfactory.agents.run_recognition                      # every ingested original, oldest first
python -m docfactory.agents.run_recognition "<bundle path>" --force
python -m docfactory.agents.run_scoring AI-Driven-Job-Matching-Platform   # score against tests/corpus/jobmatch_expectations.json
```

Recognition finds the **things the documents discuss** (components, environments, alerts, procedures, support contacts, runbooks, decisions,
risks, ...) and **how they relate**, across all documents of a scope, before any fact is filled:

1. **Windows**: each original is cut into windows of whole sections in document order, capped by words (`DOCFACTORY_WORD_CAP`, default 2000):
   usually two or three sections; a section too long to share a window gets one of its own.
2. **One call per window** (tool `submit_recognition`) sees the document's outline, the window, the entity type vocabulary (derived from the
   fact registry plus graph-only types such as Runbook, Decision, Risk, Team, Tool, Infrastructure), the entities already known (the whole
   graph, most relevant first, `DOCFACTORY_CATALOG_MAX`, default 200) and the keyword-rule hints. It returns entities (type, canonical name,
   aliases, `same_as` an existing entity), relationships (a verb phrase, optionally a standard kind) and, per chunk, the facts it informs. Code
   refuses types outside the vocabulary, names not in the text, unknown `same_as`, `same_as` across types (except a listed promotion such as a
   Role that is a SupportContact), relationships to unknown entities and chunks outside the window. A thing no type fits is
   `proposed:<Name>`: kept in the graph, and drafted as a type proposal when it recurs (Step 2c).
3. **Entity resolution**: per entity type, one call looks at the whole list for entities that are the same thing under different names
   ("AI Engine", "AI-Driven Matching Engine"); the decisions are stored and applied on every rebuild (`--no-resolve` skips it).
4. **The entity graph** is the deterministic merge of all recognitions: `bundle/<scope>/entities/<Type>/<slug>.md`, one OKF concept per entity
   (aliases, evidence = the chunks that discuss it, relationships as links), with `bundle/<scope>/entities/index.md`. Each original's share is
   `bundle/<scope>/recognition/<file>.md`; unchanged windows are never sent to the model again.

### Step 2: extract

```
python -m docfactory.agents.run_extraction "ReadmeForge/references/ReadmeForge SRS v0.3.pdf"
python -m docfactory.agents.run_extraction "ReadmeForge/references/ReadmeForge SRS v0.3.pdf" --entity FunctionalRequirements
python -m docfactory.agents.run_extraction "ReadmeForge/references/ReadmeForge SRS v0.3.pdf" --entity Architecture --force
```

The argument is the original's bundle path, with forward slashes; with a wrong path the command lists what is ingested. Every entity tagged in the file is extracted (or only the ones named with `--entity`, repeatable):

1. **Key** from the file's folder: `<App>.<Entity>`. `Slo` and `Kpis` (shared facts) come only from files in `bundle/Shared/references/`; files in `general/` give no facts.
2. **Skip** when the entity's chunks are unchanged since its last extraction from this file: no LLM call. `--force` extracts anyway.
3. **Batches** of the entity's chunks (up to 3500 characters each), one fresh LLM call per batch with one tool, `submit_extraction`. The tool refuses invalid items, identifiers that are not in the chunks (the model may not number items), two items with one identifier, and placeholder text such as "N/A: not mentioned"; the model fixes and resubmits. A batch that fails is split in half and retried.
4. **Priorities**: a requirement whose priority is still empty gets the one its own keyword states: SHALL/MUST -> MUST, SHOULD -> SHOULD, MAY -> COULD.
5. **Merge and write**: the batch answers merge into this file's contribution file, all files' contributions merge into the fact, and `BundleStore` validates it and writes the fact's concept file (draft, `generated.by okf-extraction-agent/<model>`, sources = every contributing file).

The report gives per entity: outcome (`SAVED`, `UNCHANGED`, `SKIPPED_UNCHANGED_CHUNKS`, `SKIPPED_SCOPE`, `REMOVED`, `REJECTED`, `FAILED`), version and completeness, chunks, batches, items, priorities filled from keywords, and for review: batch problems, conflicts, values not found in the text, and the questions the fact still leaves open. Run it again after a new revision of the file: only entities whose chunks changed are extracted, and an entity no longer tagged loses this file's contribution (`REMOVED`). A `REJECTED` fact (for example an overview with no purpose yet) keeps the file's contribution, so a later document can complete it.

### Step 2b: what extraction leaves out (notes, new types, relationships)

`run_extraction` (without `--entity`) does three more things after the entities, unless switched off with `--no-notes` / `--no-proposals`:

1. **Notes.** The chunks that are in no knowledge fact (no entity tagged, or the entity gives no fact from this file) are shown to the model in batches (one tool, `submit_discovery`); what is worth keeping becomes a `Note` (`<App>/Note/notes/<title>.md`), the rest is declared worthless. Notes never enter a document.
2. **Type proposals.** The same chunks are shown once more (one tool, `submit_type_proposal`): a recurring kind of knowledge the ontology has no entity for (risks, assumptions, ...) is stored as a pending proposal in `staging/type_proposals/`. Nothing is created yet. Look at them and apply one when you agree:

```
python -m docfactory.agents.apply_type_proposal --list
python -m docfactory.agents.apply_type_proposal Risks            # creates the model, tests, registry entry and tagging signals, runs the quality gate, tags the stored originals; undoes everything if a step fails
python -m docfactory.agents.run_extraction "<bundle path>" --entity Risks
```

   The result is left uncommitted for review (the skill `/docfactory-apply-type-proposal` lets the developer agent review it).
3. **Relationship graph.** `<App>/graph/relationships.md` is rebuilt from the concept files: structure, identifiers an item names in its text (`FR-12`) and the relations the extraction took from the document (`depends_on`, `implements`, ...). `python -m docfactory.agents.run_graph [<scope>]` rebuilds it alone.

Every item of a list (each requirement, component, alert, ...) is its own concept file under its fact, e.g. `<App>/FunctionalRequirements/requirements/FR-01.md`; the fact file itself holds the other fields and links to its items. Saving and reading still use the whole object.

To see what became of every chunk of an original (extracted, noted, not extracted yet, skipped by scope, unmapped) and how well the graph is linked:

```
python -m docfactory.agents.run_coverage
python -m docfactory.agents.run_coverage "<bundle path>"
```

### Step 2c: fill one item per entity

```
python -m docfactory.agents.run_entity_extraction AI-Driven-Job-Matching-Platform
python -m docfactory.agents.run_entity_extraction Shared
```

For every entity whose type is an item type (Component -> `Architecture.components`, Alert -> `Monitoring.alerts`, SupportContact ->
`Support.contacts`, ...), one call fills that item from **every place that discusses it**: its own chunks in every original, then the chunks of
the entities it is related to (its team, its cluster, its runbook), within the word cap. Code sets the item's name (the entity's canonical
name, so no duplicates), its evidence, its relations (from the graph) and adds its "depends on" targets to `dependencies`. Each item is stored
as a contribution `(entity) <id>`; once a fact has entity items, its entity-backed lists come from them alone (Step 2 fills only the fact's own
fields, from the chunks recognition routed to it). Unchanged entities make no call (`--force` redoes them). Recurring `proposed:` types are then
drafted as pending type proposals (`--no-proposals` skips it).

### Step 3: generate

```
python -m docfactory.generate AI-Driven-Job-Matching-Platform SRS
python -m docfactory.generate AI-Driven-Job-Matching-Platform all --no-llm
```

The arguments are the application name (as in the fact keys) and the document type: `Overview`, `SMTD`, `SRS`, `SOP` or `all`. Per document:

1. **Group**: the template (a YAML file in `docfactory/generation/templates/`; add a file to add a document type) says which fact field fills each section; code reads those facts from `bundle/<App>/` and `bundle/Shared/`, takes the JSON under `# Value` (checking its hash) and copies the values in. Nothing is rewritten or invented. A missing fact leaves its section `_Not provided._`; the document is always produced.
2. **Save** the body as `output/<App>/state/<Type>.body.json` (same facts = `UNCHANGED`).
3. **Document control and revision history**, written by code, never from facts: id `<App>-<Type>`, title, version `0.<body version>`, status `Draft`, owner `docFactory`, dates; one revision entry each time the body changes, naming the changed sections and the fact versions they came from. Approvers are added by the human approval (Phase 5). Saved as `<Type>.control.json` and `<Type>.history.json` in the same folder.
4. **Needs list**: code lists the gaps (document fields no fact fills, and the open questions of the fact fields this template uses); one small LLM call merges and phrases them as questions grouped by who can answer, and code checks that every gap is covered and nothing is added. Unchanged gaps = no call; a failed call (or `--no-llm`) keeps the gaps themselves. Saved as `<Type>.needs.json`.
5. **Render** `output/<App>/<Type>.md` and `output/<App>/<Type>.missing.md`.

Answer the questions by adding or revising a source document in `incoming/` and running steps 1-3 again; never edit the output.

The report gives per document: the body's action, version and completeness, the document version, the revision entry added (if any), and the number of gaps and needs with where the needs came from (`llm`, `fallback` with the reason, or `no_llm`; "unchanged gaps, no LLM call" when the stored list was kept). Running it again with unchanged facts writes no file and makes no LLM call, so it is safe to run whenever facts may have changed.

On the real 50-page SRS of AI-Driven-Job-Matching-Platform: the body holds all 186 functional and 165 non-functional requirements (60% complete, `Shared.Slo` not stored yet), and the 11 gaps became 8 questions for the product owner, the architect and the service owner. The other three: Overview 70% (3 gaps -> 2 needs), SMTD 45% (42 -> 14), SOP 55% (12 -> 5); all four in about 35 seconds. The documents of this run are in `samples/output/`, the bundle behind them in `samples/bundle/`.

### Look at the results

Everything is a file: open it, `cat` it, `git diff` it.

| I want to... | Command or place |
|---|---|
| Read a fact | `bundle/ReadmeForge/Architecture.md` (OKF frontmatter, the JSON, the open questions) |
| See the stored facts | `python -c "from docfactory.bundle.bundle_store import BundleStore; [print(f.key, 'v%d' % f.version, f.status.value, '%g%%' % f.completeness, f.generated_by) for f in BundleStore().list_facts()]"` |
| Which facts came from a file | `python -c "from docfactory.bundle.bundle_store import BundleStore; print([f.key for f in BundleStore().list_facts_by_source('ReadmeForge/references/ReadmeForge SRS v0.3.pdf')])"` |
| What is ingested, and when | `python -c "from docfactory.bundle.source_store import SourceStore; [print(r.path, 'v%d' % r.version, r.timestamp) for r in SourceStore().list()]"` |
| The chunks and tags of an ingested file | `bundle/<scope>/sources/<file>.md` (outline and tags); the text: `python -c "from docfactory.ingest import source_reads; print(source_reads.read_source_text('<scope>/references/<file>'))"` |
| What each file contributed to a fact | `bundle/<scope>/sources/<file>/<Entity>.md`, or `python -c "from docfactory.bundle.contribution_store import ContributionStore; [print(c.resource, c.generated_by, c.timestamp) for c in ContributionStore().list('ReadmeForge.FunctionalRequirements')]"` |
| Change history | `bundle/log.md` (one line per change); old values via `git log -p` if `bundle/` is a git repository |
| A stored document part | `output/<App>/state/<Type>.<body\|control\|history\|needs>.json` |

`bundle/` and `output/` are gitignored here. Never edit their files by hand: a fact, source, contribution or state file whose JSON no longer matches its hash is refused.

### The ReadmeForge sample (documents, no LLM)

Hard-coded seed data that stores and renders the four document types (through the YAML templates). The seeds supply their own document control and revision history; the golden files in `tests/golden/` are these outputs.

```
python -m seed.seed_readmeforge
python -m seed.seed_readmeforge_requirements
python -m seed.seed_readmeforge_smtd
python -m seed.seed_readmeforge_srs_sop
```

Results: facts in `bundle/ReadmeForge/`, documents in `output/ReadmeForge/` (`Overview.md`, `SMTD.md`, `SRS.md`, `SOP.md`, plus `*.missing.json`, the questions about what is still unanswered) and their state in `output/ReadmeForge/state/`.

### Tests

```
python -m pytest -q                                               # everything offline (about 1800 tests, under a minute)
python -m pytest -q tests/test_extraction_pipeline.py             # one file
python -m pytest -q -m live tests/test_live_ingestion.py          # real LLM, opt-in
python -m pytest -q -m live tests/test_live_extraction.py         # real LLM, opt-in: corpus SRS, then its revision
python -m pytest -q -m live tests/test_live_generate.py           # real LLM, opt-in: the needs list of a small SRS
python .claude/scripts/check_structure.py                         # one-class-per-file and naming rules
```

Every test uses a temporary bundle and output folder, so none touches your real data. The live tests skip themselves when the LLM server is unreachable. `tests/corpus/` holds deliberately messy sample originals (regenerate with `python tests/corpus/build_corpus.py`).

## Where things are

| Path | What it is |
|---|---|
| `incoming/` | Drop zone for new originals (gitignored) |
| `staging/` | Files being ingested, and files waiting for your decision (gitignored) |
| `bundle/` | The OKF bundle (gitignored here): `index.md`, `log.md`, one folder per scope (application, `Shared`, `general`) with the facts (`<Entity>.md`), `references/` (the originals), `sources/` (a Source file per original and a folder of its contributions) |
| `docs/ontology.md` | The entities, their facts and the tagging signals (generated; edit `docfactory/ontology/signals.json`) |
| `output/<app>/` | Rendered documents and their needs lists (`<Type>.missing.md`); `state/` holds the documents' state files. Gitignored |
| `samples/json/<entity>/` | Example JSON payloads, one folder per entity (used by the seeds and tests) |
| `samples/bundle/`, `samples/output/` | A committed snapshot of one end-to-end run on the AI-Driven-Job-Matching-Platform SRS: the bundle (the PDF, its Source, seven facts and their contributions) and the four generated documents with their needs lists. Copies, never read by the code |
| `docs/okf/SPEC.md` | The OKF v0.2 specification (verbatim copy) |
| `docfactory/models/` | Machinery models (base model, `SaveResult`, `FactMeta`, `SourceRecord`, ...) |
| `docfactory/entitymodels/` | What is known about an application: `facts/` (registered in the fact registry) and `items/` (nested types) |
| `docfactory/documentmodels/` | The parts every document has: body, document control, revision history, needs list |
| `docfactory/bundle/` | The bundle code: the fact registry, `BundleStore`, `SourceStore`, `ContributionStore` and the concept-file readers and writers |
| `docfactory/tools/`, `docfactory/agents/` | The tool packages (least privilege: one single-tool package per kind of LLM call) and the thin agent loops |
| `docfactory/extract/` | Extraction code: batching, fact keys, partial models, merge, grounding checks, keyword priorities, missing-info questions, the pipeline |
| `docfactory/generation/`, `docfactory/generate.py` | Generation code: gaps, document control, revision history, the fallback needs list, `DocumentStateStore` and shared steps; the YAML templates and the per-document flow; and its entry point |
| `.claude/agents/` | Agent prompts. `docfactory-chunk-tagger-agent.md`, `docfactory-scope-agent.md` (ingestion fallback), `docfactory-entity-extractor-agent.md` (extraction) and `docfactory-needs-list-agent.md` (generation) are the runtime prompts; edit them to tune behaviour |

Folders you can relocate with environment variables: `DOCFACTORY_BUNDLE`, `DOCFACTORY_INCOMING`, `DOCFACTORY_STAGING`, `DOCFACTORY_OUTPUT`.

## Changing the models

Entity models are created and changed through the project's skills so they come out uniform (one class per file, descriptions written for an LLM, tests with every class). In Claude Code:

- `/docfactory-create-entity-model` (a fact is registered in `docfactory/bundle/fact_registry.py` and gets its tagging signals in `signals.json`; an item is a nested type), `/docfactory-add-field`, `/docfactory-review-models`
- `/docfactory-create-shared-model` for machinery models

A model change changes what stored data means: update the tests; a stored fact that no longer validates is reported when read (re-extract it with `run_extraction --force`, or re-run the seeds).

## When something goes wrong

| Symptom | Cause and fix |
|---|---|
| `model response was cut off (context or output limit, num_ctx=...)` | The context window is too small. Raise `DOCFACTORY_NUM_CTX` (e.g. `65536`) |
| Extraction report: `batch problems ... split and retried` | A batch's answer was too long for one reply; the halves were retried. Only a single chunk that still fails is a real failure, retried on the next run |
| `... is not an ingested original` | Wrong path for `run_extraction`. Use a path printed in the list, forward slashes, like `<scope>/references/<file>` |
| `... no longer chunks as it did at ingestion` | The chunkers changed (or the original was altered) since ingestion. Run `python -m docfactory.ingest.chunk_rebuild` |
| `BundleError: ... edited outside the system` | A fact, source, contribution or state file was changed by hand (its JSON no longer matches its hash). Restore it from git, or delete it and re-run the step that wrote it |
| A file stays in `staging/` | The report says why: unsure scope, same content under another name, the name stored in several scopes, or no extractable text (a scanned PDF). Fix the cause and run ingestion again |
| Many chunks are unmapped | The ontology lacks this document's vocabulary: add heading terms or identifier patterns to `docfactory/ontology/signals.json`, then `python -m docfactory.ingest.chunk_rebuild` |
| An entity came back `REJECTED` | The merged fact misses a mandatory field (the report's save errors name it and the question). No document states it yet; the file's contribution is kept and the fact is written once another document supplies it |
| Odd items in a fact (UI or training items as requirements) | Usually a wrong entity tag on a chunk. Check the tags in the Source file and the signals in `signals.json` |
| Generate report: `needs fallback: ...` | The needs-list call failed (the reason follows); the needs list holds one question per gap and the call is retried on the next run |
| `'<App>' has no knowledge facts` | Generate needs at least one fact for the application; the message lists the applications that have facts. Use the name exactly as the folder in `bundle/` |
| A document is mostly `_Not provided._` | Its facts are missing or empty; the `<Type>.missing.md` next to it says what to find out. Facts for that application must exist first (`list_facts`); run step 2 or the seeds |

## What comes next

- **Next activity: optimize generation.** The generation flow reads the bound facts straight from the bundle files (scan, read, parse, align). Measure it on a large bundle, then optimize (an in-memory index, parse-once caching, hash-based skips).
- **Phase 5: Human in the loop. Pending.** Approval workflow (agents propose, humans approve, tools apply); this is what turns `draft` facts into `stable`, and where near-duplicate items and conflicts between documents get reviewed.
- **Phase 6: Automate. Pending.** Watch `incoming/` and run the whole chain.
