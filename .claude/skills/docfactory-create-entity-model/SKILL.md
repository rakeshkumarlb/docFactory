---
name: docfactory-create-entity-model
description: Create an entity model (a knowledge fact, or a nested item type) in docfactory/entitymodels/facts/ (fact, has a saver) or docfactory/entitymodels/items/ (item, no saver), with its saver and tests (no registry in Phase 1, nothing else to wire)
argument-hint: <ClassName> <fact|item> [app|shared] [fields and what it holds]
disable-model-invocation: true
context: fork
agent: docfactory-pydantic-developer-agent
model: sonnet
background: false
---

You are running as the **docfactory-pydantic-developer-agent**. Follow these steps exactly, in order. Scripts are run from the project root. Read `CLAUDE.md` first.

Request: $ARGUMENTS

## What gets a saver

- **fact** (a top-level knowledge fact stored under a key, e.g. `ApplicationOverview`, `Kpis`): model **and** saver, plus both test files.
- **item** (a nested type used inside a fact, e.g. `Environment` in `Environments`): model and its test only. Never a saver.

## Steps

1. **Check the skeleton exists.** `docfactory/base_saver.py`, `docfactory/db.py`, `docfactory/models/doc_field.py` and `tests/conftest.py` (with `tmp_db`). If not, stop: `Gaps: run /docfactory-create-shared-model skeleton first`.
2. **Resolve the target.**
   `python .claude/scripts/resolve_target.py entity-model <ClassName>`
   Exit 1 (`errors`) means stop and report them (bad name, class already defined elsewhere).
3. **Get the inputs.** Fact or item; for a fact: `app` (application-specific, keys `{app}.<Class>` and component keys) or `shared` (common to all applications, key `Shared.<Class>`); the field list (name, meaning, mandatory or optional, N/A allowed?). Take them from the request and `CLAUDE.md`. If missing or ambiguous, **stop and return your questions under `Gaps`; do not invent fields or scope**.
4. **Item types first.** Every nested type (the `X` in `list[X]`, or a nested single model) is its own item class in its own file. Run steps 2-7 for each, deepest first, without a saver.
5. **Write the spec** to `<scratchpad>/<ClassName>.spec.json` following `docfactory-field-spec`. For a fact with a saver at least one field's `example` must be a plain string (the saver test uses it as the changed value).
6. **Dry run.**
   - item: `python .claude/scripts/scaffold_model.py entity-model <spec.json> --dry-run`
   - fact: `python .claude/scripts/scaffold_model.py entity-model <spec.json> --scope app|shared --dry-run`
   An item is written to `docfactory/entitymodels/items/<snake>.py`. The folder follows from the saver option: with `--scope`/`--pattern` the model is a fact and goes to `facts/`; without one it is an item and goes to `items/` (`resolve_target.py entity-model <Class> facts|items` shows the path). `check_structure.py` enforces it (`fact-item-placement`).
   `SPEC REJECTED` / `CANNOT SCAFFOLD` list what to fix; fix the spec and rerun. Read the output: descriptions read well for an LLM, mandatory fields are really necessary, defaults are honest.
7. **Scaffold for real:** the same command without `--dry-run`. For a fact it writes `docfactory/entitymodels/facts/<snake>.py`, `docfactory/entitysaver/<snake>_saver.py` (declares only `model` and `key_patterns`) and `tests/test_<snake>.py`, `tests/test_<snake>_saver.py`. Never hand-edit the generated files to work around a rejection: change the spec. There is no registry or `tools.py` in Phase 1: the saver is used directly and its test calls `<Class>Saver().save(...)`.
8. **Completeness tests (hand-written, appended to the model's test file).** Add: a payload with only mandatory fields scores the hand-computed `answered / total * 100` using `docfactory.completeness`; a fully filled payload scores 100; an optional field passed explicitly as its default is not counted; a legal `NotApplicable` counts. State the arithmetic in a comment.
9. **Quality gate.** Follow the `docfactory-quality-gate` skill.
