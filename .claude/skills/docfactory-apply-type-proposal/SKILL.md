---
name: docfactory-apply-type-proposal
description: Review and apply a stored docFactory type proposal (a new entity type the discovery step proposed), by running the gated apply step, reviewing the generated model, tests and signals, and extracting the new entity
argument-hint: <Entity>
disable-model-invocation: true
context: fork
agent: docfactory-pydantic-developer-agent
model: sonnet
background: false
---

You are running as the **docfactory-pydantic-developer-agent**. Follow these steps exactly, in order. Scripts are run from the project root. Read `CLAUDE.md` first (section "OKF alignment redesign").

Request: $ARGUMENTS

A type proposal is a *proposal*: the runtime LLM call only returned a specification, it wrote no code. You are the review step.

1. **Look at the proposal.** `python -m docfactory.agents.apply_type_proposal --list` shows the stored proposals; read `staging/type_proposals/<Entity>.json` (fields, signals, the chunks it came from). If the proposal duplicates an existing entity, invents fields the chunks do not support, or has vague descriptions, stop and report why under `Gaps`; do not apply it.
2. **Apply it.** `python -m docfactory.agents.apply_type_proposal <Entity>`. It runs the scaffold scripts, adds the signals, regenerates `docs/ontology.md`, runs the quality gate and tags the stored originals. On failure it rolls everything back and prints why; fix the cause in the proposal (never hand-edit generated files to get around a rejection) or report it.
3. **Review the result** (the working tree is left uncommitted): the new model file(s) in `docfactory/entitymodels/`, their tests, the registry entry and the `signals.json` entry. Descriptions must read well for an LLM, mandatory fields must be really necessary, defaults honest. Fix wording through the `docfactory-add-field` skill or by editing the model's descriptions; add the hand-written completeness tests described in `docfactory-create-entity-model` step 8.
4. **Quality gate.** Follow the `docfactory-quality-gate` skill. Do not commit.
5. **Report** what was created and the command to extract the new entity: `python -m docfactory.agents.run_extraction "<bundle path>" --entity <Entity>`.
