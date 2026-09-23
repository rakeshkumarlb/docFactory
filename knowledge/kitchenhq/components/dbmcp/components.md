---
app: kitchenhq
topic: components
summary: 
updated: 2026-09-23
---

# Components

## Code layout

- [F-0130] The MCP app is served via `mcp.streamable_http_app()` mounted on the same FastAPI app as the REST routes. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0131] `kitchendb/schema.py`'s `initialize_database()` runs `schema.sql` and seeds a fresh DB (`kitchendb/seed.py`); it is called on FastAPI `lifespan` startup. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0132] Data operations in `kitchendb/tools/*.py` are decorated with a local `@tool`; `kitchendb/tools/registry.py` collects them and `kitchendb/server.py`'s `build_mcp()` adds each to a fresh `FastMCP` instance built per app. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0133] `kitchendb/routes.py` re-exposes almost every tool as a thin Pydantic-validated FastAPI REST route that calls the same function. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0134] `dbmcp/init_db.py` is only a compatibility shim (`uvicorn init_db:app`, the `python init_db.py` dev runner) re-exporting from the `kitchendb` package; the implementation is not in that file. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0294] The `kitchendb/` package consists of `config`, `db`, `schema`, `seed`, `validation` and `models` modules, `tools/` (data operations by domain, each an MCP tool and/or a REST handler), `routes.py`, and `server.py` (`create_app()`). — src: store/kitchenhq/docs/repo/dbmcp/README.md
- [F-0295] The compatibility shim `init_db.py` also supports `from init_db import DATABASE_PATH`. — src: store/kitchenhq/docs/repo/dbmcp/README.md
- [F-0296] The inventory-mutation REST routes (`POST /api/inventory`, `PATCH /api/inventory/{id}`, `POST /api/inventory/{id}/discard`) are kept because pytest exercises them and they mirror live MCP tools, even though the read-only chatui Pantry page no longer calls them. — src: store/kitchenhq/docs/repo/dbmcp/README.md
