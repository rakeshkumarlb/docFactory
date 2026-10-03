---
name: review-models
description: Review existing docFactory models and savers against the CLAUDE.md principles (read-only findings list)
argument-hint: [path, class name, or "all" (default)]
disable-model-invocation: true
context: fork
agent: pydantic-developer-agent
model: sonnet
background: false
---

You are running as the **pydantic-developer-agent**. This is a **read-only review: change no files.** Scripts are run from the project root. Read `CLAUDE.md` first.

Scope: $ARGUMENTS (empty means everything under `docfactory/models`, `entitymodels/facts`, `entitymodels/items`, `documentmodels`, `entitysaver`, `documentsaver`, and `tests/`).

## Steps

1. **Mechanical findings first (deterministic).**
   `python .claude/scripts/check_structure.py [paths]`
   Every line (`path:line: RULE message`) is a finding, reported as-is. Rules: syntax, one-class, file-name, saver-name, saver-base, saver-body, base-model, field-helper, forbidden-type, layering, stray-model, class-docstring, test-missing.
2. **Tests.** `python -m pytest -q`. Report the real result. `no tests collected` is a finding.
3. **Judgment findings (what scripts cannot see).** For each model in scope, read it and report with `file:line`:
   - a description that does not say what a good value looks like, or reads badly for an LLM;
   - a missing or vague `question` where the description does not work as one;
   - a mandatory field that is not absolutely necessary (would the object be meaningless without it?);
   - a default that pretends to be knowledge, or a field whose default is also a legitimate answer (completeness cannot tell);
   - `na_allowed` on a field where N/A is not a real answer, or missing where it is;
   - a list of `str` that hides structure and should be typed item models;
   - an entity model doing a document's job or the reverse; a shared model used by only one side;
   - a document field with a wrong binding; document control or revision history inside a body model; a section redefined instead of reused;
   - a test that is weak: asserts nothing meaningful, hard-codes a number without the arithmetic, or was skipped/loosened;
   - Phase 2 features (RAG, LLM calls, provenance, history, approval gate) in the code.
4. **Output.** Findings grouped by severity: **violates a principle** / **smell** / **nit**. Each: `file:line`, one-line problem, one-line suggested fix, which principle. End with a two-line summary and the pytest result. If there is nothing to review yet, say so and stop.

Do not fix anything. Fixes are separate tasks (`/add-field`, or re-running the relevant create skill).
