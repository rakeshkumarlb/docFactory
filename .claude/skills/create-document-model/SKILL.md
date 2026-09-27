---
name: create-document-model
description: Create a document model (a document body, a section or a part) in docfactory/documentmodels/, with bindings, tests and, where needed, its saver (no registry in Phase 1)
argument-hint: <ClassName> <document|section|part> [doctype] [fields and which facts they are built from]
disable-model-invocation: true
context: fork
agent: pydantic-developer-agent
model: sonnet
background: false
---

You are running as the **pydantic-developer-agent**. Follow these steps exactly, in order. Scripts are run from the project root. Read `CLAUDE.md` first.

Request: $ARGUMENTS

## What gets a saver

| Class | Saver | scaffold option |
|---|---|---|
| **document** body (e.g. `SmtdDocument`) | yes | `--doctype <Name>` -> key `{app}.Outputs.<Name>` |
| `DocumentControl` | yes, **once**, shared by every document type | `--pattern "{app}.Outputs.{doctype}.DocumentControl"` |
| `RevisionHistory` | yes, **once**, shared by every document type | `--pattern "{app}.Outputs.{doctype}.RevisionHistory"` |
| any other **section** or **part** (e.g. `SmtdSupportModel`, `RevisionEntry`) | no | none |

If `DocumentControl` or `RevisionHistory` already exists with its saver, do not recreate it: reuse it.

## Steps

1. **Check the skeleton exists** (as in `create-entity-model` step 1). If not, stop: `Gaps: run /create-shared-model skeleton first`.
2. **Resolve the target.**
   `python .claude/scripts/resolve_target.py document-model <ClassName>`
   Exit 1 means stop and report `errors`. If the type is used by both entities and documents it belongs in `models/`: stop and say so (`/create-shared-model`).
3. **Get the inputs.** Role (document, section, part), doc type for a document body, and for each field its meaning and where its content comes from. Take them from the request and `CLAUDE.md`. If missing, **stop and return the questions under `Gaps`; do not invent chapters or bindings**.
4. **Bindings must be real.** Each field's `binding` is `caller` (supplied by the caller: document control, revision history), `composed` (a nested section model) or `Entity.field` (the entity model and field must already exist; if not, report `Gaps: create entity <X> first`). List candidates with `python .claude/scripts/find_usages.py <EntityClass>`.
5. **Rules.** A document body model does **not** contain document control or revision history (separate rows). Reuse existing sections instead of redefining them. Sections and parts are each their own class in their own file: create them first, deepest first, with steps 2-8 per class (no saver for them).
6. **Write the spec** to `<scratchpad>/<ClassName>.spec.json` following `docfactory-field-spec` (every field has a `binding`). If a saver is created, at least one field's `example` must be a plain string.
7. **Dry run.**
   `python .claude/scripts/scaffold_model.py document-model <spec.json> [saver option from the table] --dry-run`
   Fix any `SPEC REJECTED` / `CANNOT SCAFFOLD` (it also checks that every `Entity.field` binding exists).
8. **Scaffold for real:** the same command without `--dry-run`. It writes `docfactory/documentmodels/<snake>.py` and `tests/test_<snake>.py`, plus, when a saver option was given, `docfactory/documentsaver/<snake>_saver.py` and `tests/test_<snake>_saver.py` (rows land in `DocumentOutputs`). There is no registry in Phase 1: nothing else to wire.
9. **Extra tests (hand-written).** If `build_document` exists: a built object with a missing fact marks the field `MISSING` and yields a MissingInfo question. If it does not exist yet, report `Gaps: build/MissingInfo tests pending`.
10. **Quality gate.** Follow the `docfactory-quality-gate` skill.

Build and render code (`build.py`, `render.py`) is not part of this task.
