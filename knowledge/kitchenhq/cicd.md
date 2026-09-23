---
app: kitchenhq
topic: cicd
summary: 
updated: 2026-09-23
---

# Cicd

## Quality

- [F-0109] There is no CI, and linting/formatting is not configured. — src: store/kitchenhq/docs/repo/README.md
- [F-0110] Automated tests exist for dbmcp only (`cd dbmcp && pip install -r requirements-dev.txt && pytest tests/`); each test spins up a temp SQLite DB and needs no live server. — src: store/kitchenhq/docs/repo/README.md
- [F-0111] chatui and agents have no automated tests yet. — src: store/kitchenhq/docs/repo/README.md
