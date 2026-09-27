---
name: docfactory-quality-gate
description: The mandatory final step of every docFactory task. Runs the structure check and the full test suite, fixes failures and reports in the fixed format. Reference for the pydantic-developer-agent.
user-invocable: false
---

# Quality gate

A task is **not done** until this prints `GATE PASSED`.

## Steps

1. From the project root run:
   ```
   python .claude/scripts/run_gate.py
   ```
   It runs `check_structure.py` (one class per file, names, folders, base model, `doc_field` descriptions, forbidden types, saver bodies, layering, stray models, a test per class) and then `pytest -q`.
2. `GATE FAILED: structure` -> each line is `path:line: RULE message`. Fix the code (not the rule, not the checker), rerun.
3. `GATE FAILED: tests` -> read the failure, fix the cause. **Never** delete, skip, loosen or `xfail` a test to get green. If a test is genuinely wrong, say so in the report and say why.
4. `pytest exit 5 = no tests collected` means the tests you were supposed to write are missing. Write them.
5. Repeat until `GATE PASSED`. If you cannot get there after three fix rounds, stop and report the exact output.

## Report format (your final message to the caller)

```
Created:   <files>            (or Changed / Reviewed)
Fields:    <name: mandatory|optional, na_allowed?> ...   (models only)
Judgement: <defaults, na_allowed, bindings you chose and why>
Gaps:      <what could not be done and why; open questions for the caller>
Gate:      GATE PASSED   (paste the pytest summary line)
```

If you could not finish, say `Gate: NOT RUN` or `Gate: FAILED` with the output. Never claim success without the gate line. You cannot ask the user questions directly: put open questions under `Gaps`.
