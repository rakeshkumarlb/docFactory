---
app: kitchenhq
topic: operations
summary: 
updated: 2026-09-23
---

# Operations

## Standalone run

- [F-0084] dbmcp can be run standalone: `pip install -r requirements.txt`, then `KITCHENHQ_API_KEY=... python init_db.py`, which creates/seeds `kitchen.db` on startup and serves REST + MCP on port 18000. — src: store/kitchenhq/docs/repo/README.md

## Docker

- [F-0290] dbmcp can be built and run standalone with `docker build -t kitchenhq-db-mcp .` and `docker run --rm -p 18000:18000 -e KITCHENHQ_API_KEY=your-key -v "${PWD}/data:/data" kitchenhq-db-mcp`. — src: store/kitchenhq/docs/repo/dbmcp/README.md
- [F-0291] The SQLite database is stored in the host `data` folder mounted at `/data`; the container always accesses it as `/data/kitchen.db` and only the host-side location changes. — src: store/kitchenhq/docs/repo/dbmcp/README.md

## Configuration

- [F-0292] The dbmcp container always serves over streamable HTTP. — src: store/kitchenhq/docs/repo/dbmcp/README.md
- [F-0293] `KITCHENHQ_API_KEY` (required), `KITCHEN_DB_PATH`, `MCP_HOST` and `MCP_PORT` can be overridden with environment variables. — src: store/kitchenhq/docs/repo/dbmcp/README.md
