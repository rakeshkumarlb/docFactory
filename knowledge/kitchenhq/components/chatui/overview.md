---
app: kitchenhq
topic: overview
summary: 
updated: 2026-09-23
---

# Overview

## Summary

- [F-0036] chatui (dir `chatui/`) is a React (Vite) single-page app served on port 8080 by a thin FastAPI backend. — src: store/kitchenhq/docs/repo/README.md
- [F-0037] chatui proxies CRUD calls to dbmcp and chat/automation calls to agent-api. — src: store/kitchenhq/docs/repo/README.md
- [F-0038] chatui holds no LangChain/MCP dependency and is a pure REST client. — src: store/kitchenhq/docs/repo/README.md
- [F-0039] chatui calls dbmcp directly for all CRUD/read data (`/api/dashboard` and friends) and agent-api for anything that needs the LLM (chat, "run job now"). — src: store/kitchenhq/docs/repo/README.md
