This repository is an agent system. Read `CLAUDE.md` at the repo root and follow it exactly.

- Agent role definitions live in `.claude/agents/*.md`; when asked to ingest, extract, generate or design a template, adopt the matching role and follow its steps.
- Never do deterministic work by hand: use `tools/*.py` (store_file, kb, compose, completeness, missing_info, lint_doc, db).
- Never write to `knowledge/` directly; propose via `review/` and apply only with `tools/kb.py apply` after explicit user approval.
