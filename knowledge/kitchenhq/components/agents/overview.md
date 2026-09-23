---
app: kitchenhq
topic: overview
summary: 
updated: 2026-09-23
---

# Overview

## Summary

- [F-0032] agent-api (dir `agents/`) is a Python LangChain + APScheduler service on port 8090. — src: store/kitchenhq/docs/repo/README.md
- [F-0033] agent-api is the only process that talks to the LLM and to dbmcp over MCP. — src: store/kitchenhq/docs/repo/README.md
- [F-0034] agent-api serves `/chat` and `/invoke/{job}` and runs the cron jobs in-process. — src: store/kitchenhq/docs/repo/README.md
- [F-0035] Every agent-api request builds and disposes its own LLM/MCP connections; nothing outlives a single call. — src: store/kitchenhq/docs/repo/README.md
