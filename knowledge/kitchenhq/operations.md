---
app: kitchenhq
topic: operations
summary: 
updated: 2026-09-23
---

# Operations

## Environment

- [F-0128] agent-api requires dbmcp reachable at `MCP_URL` (default `http://localhost:18000/mcp` outside Docker; the Docker Compose network uses the service name `dbmcp`) and a `KITCHENHQ_API_KEY` matching dbmcp's. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0129] chatui's `AGENT_API_URL` and `DB_API_URL` default to the Docker service names (`AGENT_API_URL` default `http://agent-api:8090`). — src: store/kitchenhq/docs/repo/CLAUDE.md
