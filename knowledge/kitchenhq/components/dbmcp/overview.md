---
app: kitchenhq
topic: overview
summary: 
updated: 2026-09-23
---

# Overview

## Summary

- [F-0030] dbmcp (dir `dbmcp/`) is a Python FastAPI + FastMCP service on port 18000 that owns the SQLite database (`kitchen.db`) and its schema. — src: store/kitchenhq/docs/repo/README.md
- [F-0031] dbmcp exposes every data operation twice, as REST (`/api/*`) and as MCP tools (`/mcp`), from one FastAPI app. — src: store/kitchenhq/docs/repo/README.md
- [F-0288] The dbmcp folder is a standalone Docker package for the KitchenHQ SQLite MCP server. — src: store/kitchenhq/docs/repo/dbmcp/README.md
- [F-0289] The dbmcp MCP endpoint is available at `http://localhost:18000/mcp`. — src: store/kitchenhq/docs/repo/dbmcp/README.md
