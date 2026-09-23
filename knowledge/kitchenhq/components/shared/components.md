---
app: kitchenhq
topic: components
summary: 
updated: 2026-09-23
---

# Components

## Vendored copies

- [F-0300] The three services each build from their own Docker context and share no Python package or package manager, by design, so each stays independently deployable; this is why the constants are copied rather than imported. — src: store/kitchenhq/docs/repo/shared/README.md
- [F-0301] `shared/sync.py` vendors a byte-identical copy of `shared/constants.py` into each Python service that needs the values in-process. — src: store/kitchenhq/docs/repo/shared/README.md
- [F-0302] `dbmcp/constants.py` is used for schema validation, the `ORDER BY ... CASE` builders and the `constants` block in `GET /api/dashboard`. — src: store/kitchenhq/docs/repo/shared/README.md
- [F-0303] `agents/app/constants.py` is used for Pydantic validators and module-level slot sets in the email package and `kitchen_agent`. — src: store/kitchenhq/docs/repo/shared/README.md
- [F-0304] The chatui React app cannot import Python, so it reads the same values at runtime from dbmcp's `GET /api/dashboard` response (`data.constants`). — src: store/kitchenhq/docs/repo/shared/README.md
