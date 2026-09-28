---
name: create-document-model
description: Create a document model (a document body, a shared part or an entity-bound section) in docfactory/documentmodels/<role>/, with bindings, tests and, where needed, its saver (no registry in Phase 1)
argument-hint: <ClassName> <documents|shared|entitybound> [doctype] [fields and which facts they are built from]
disable-model-invocation: true
context: fork
agent: pydantic-developer-agent
model: sonnet
background: false
---

You are running as the **pydantic-developer-agent**. Follow these steps exactly, in order. Scripts are run from the project root. Read `CLAUDE.md` first.

Request: $ARGUMENTS

## Roles: the folder, the binding and the saver

The `role` in the spec picks the sub-folder of `documentmodels/` (and of `documentsaver/`). Decide it by what the class depends on:

| Role | Holds | Fields bind to | Saver | scaffold option |
|---|---|---|---|---|
| `documents` | a **document body** (e.g. `SmtdDocument`), composed of sections | `composed` | yes | `--doctype <Name>` -> key `{app}.Outputs.<Name>` |
| `shared` | parts reused by every document type, supplied by the caller: `DocumentControl`, `RevisionHistory` (saver **once** each), and their parts `RevisionEntry`, `MissingInfo` (no saver) | `caller` | `DocumentControl`, `RevisionHistory` only | `--pattern "{app}.Outputs.{doctype}.DocumentControl"` / `"...RevisionHistory"` |
| `entitybound` | a **section** in a specific format over entity facts (e.g. `ApplicationSummarySection`) and its nested parts | `Entity.field` | never (stored inside the document body) | none |

Import rules, checked by `check_structure.py`: `documents` may import `entitybound` and `shared`; `entitybound` and `shared` import nothing else from `documentmodels/`. A document saver sits in the same role folder as its model. If the class is needed by entities as well, it is not a document model: it belongs in `models/`.

If `DocumentControl` or `RevisionHistory` already exists with its saver, do not recreate it: reuse it.

## Steps

1. **Check the skeleton exists** (as in `create-entity-model` step 1). If not, stop: `Gaps: run /create-shared-model skeleton first`.
2. **Resolve the target.**
   `python .claude/scripts/resolve_target.py document-model <ClassName> <role>`
   Exit 1 means stop and report `errors`. If the type is used by both entities and documents it belongs in `models/`: stop and say so (`/create-shared-model`).
3. **Get the inputs.** Role (`documents`, `shared`, `entitybound`), doc type for a document body, and for each field its meaning and where its content comes from. Take them from the request and `CLAUDE.md`. If missing, **stop and return the questions under `Gaps`; do not invent chapters or bindings**.
4. **Bindings must be real.** Each field's `binding` is `caller` (supplied by the caller: document control, revision history), `composed` (a nested section model) or `Entity.field` (the entity model and field must already exist; if not, report `Gaps: create entity <X> first`). List candidates with `python .claude/scripts/find_usages.py <EntityClass>`.
5. **Rules.** A document body model does **not** contain document control or revision history (separate rows). Reuse existing sections instead of redefining them. Sections and parts are each their own class in their own file: create them first, deepest first, with steps 2-8 per class (no saver for them).
6. **Write the spec** to `<scratchpad>/<ClassName>.spec.json` following `docfactory-field-spec` (a top-level `role`, and every field has a `binding`). If a saver is created, at least one field's `example` must be a plain string.
7. **Dry run.**
   `python .claude/scripts/scaffold_model.py document-model <spec.json> [saver option from the table] --dry-run`
   Fix any `SPEC REJECTED` / `CANNOT SCAFFOLD` (it also checks that every `Entity.field` binding exists).
8. **Scaffold for real:** the same command without `--dry-run`. It writes `docfactory/documentmodels/<role>/<snake>.py` and `tests/test_<snake>.py`, plus, when a saver option was given, `docfactory/documentsaver/<role>/<snake>_saver.py` and `tests/test_<snake>_saver.py` (rows land in `DocumentOutputs`). There is no registry in Phase 1: nothing else to wire.
9. **Extra tests (hand-written).** If `build_document` exists: a built object with a missing fact marks the field `MISSING` and yields a MissingInfo question. If it does not exist yet, report `Gaps: build/MissingInfo tests pending`.
10. **Quality gate.** Follow the `docfactory-quality-gate` skill.

Build and render code (`build.py`, `render.py`) is not part of this task.
