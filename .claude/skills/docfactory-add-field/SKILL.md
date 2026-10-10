---
name: docfactory-add-field
description: Add a field to an existing entity or shared model, updating tests, templates and golden files
argument-hint: <ModelClass> <field name> [type, meaning, default, N/A allowed?]
disable-model-invocation: true
context: fork
agent: docfactory-pydantic-developer-agent
model: sonnet
background: false
---

You are running as the **docfactory-pydantic-developer-agent**. Follow these steps exactly, in order. Scripts are run from the project root. Read `CLAUDE.md` first.

Request: $ARGUMENTS

## Steps

1. **Find everything that touches the model.**
   `python .claude/scripts/find_usages.py <ModelClass>`
   Read the model, its test, its saver, and every document template (`generation/templates/*.yaml`), seed script and golden `.md` in the output. If the class is not found, stop and report it.
2. **Get the inputs.** Field name, type, meaning, default, N/A allowed?. If any is missing, **stop and return the questions under `Gaps`; do not invent the field**. Default to an optional field with an honest default. A mandatory field breaks every stored payload: only when the request says it truly identifies the object.
3. **Write the field spec** to `<scratchpad>/<field>.field.json`: one field object per `docfactory-field-spec` plus an optional `"imports"` list. If the type is a new nested class or enum, create that class first with its own file (see `docfactory-field-spec`).
4. **Dry run.**
   `python .claude/scripts/add_field.py <ModelClass> <field.json> --dry-run`
   Fix any `SPEC REJECTED` / `CANNOT ADD`. (A mandatory field needs `--allow-mandatory`; use it only when step 2 justified it.)
5. **Apply.** Run the same command without `--dry-run`. It inserts the field and imports and prints `add_to_FULL` / `add_to_MINIMAL` and the test file path.
6. **Update the tests.** In the model's test file add the printed lines to `FULL` (and `MINIMAL` if mandatory); add the field to the parametrized lists (`test_not_applicable_...`, mandatory list, defaults test); update hand-written completeness tests, because total field count changed.
7. **Update everything that depends on it**, from step 1's list: document templates that should now bind to the field (a field entry in the YAML file), seed scripts (never invent a value for the new field to raise completeness), the saver test (`tests/test_<snake>_saver.py`, if it exists: add the entry to `_FULL`), and golden `.md` files.
8. **State the data impact.** Changing a model changes stored data's meaning. Report: existing stored rows are unchanged until re-saved, their completeness drops because total fields grew, and if the field is mandatory every stored payload becomes invalid.
9. **Quality gate.** Follow the `docfactory-quality-gate` skill.
