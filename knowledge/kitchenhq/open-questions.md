---
app: kitchenhq
topic: open-questions
summary: 
updated: 2026-09-23
---

# Open Questions

## Documentation inconsistencies

- [F-0117] The README architecture diagram labels agent-api "6 cron jobs, in-process", while the rest of the README lists and counts 11 cron jobs; the diagram is presumed stale and needs confirmation. — src: store/kitchenhq/docs/repo/README.md
- [F-0279] CLAUDE.md's chatui section says the Profile `email` is where dbmcp sends the "new prep task" notification, but the same file says email lives entirely in agent-api and dbmcp has no SMTP or notification routes; the dbmcp wording is presumed stale and needs confirmation. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0287] chatui/README.md says the chat UI connects to a "long-lived Executive Chef agent" and gives a local run recipe (install the root requirements, set `MCP_URL`, run `uvicorn chatui.app:app`), which contradicts the root README and CLAUDE.md (no long-lived agent, chatui has its own requirements and no MCP dependency, run `uvicorn app:app` from `chatui/`); the chatui README is presumed stale and needs confirmation. — src: store/kitchenhq/docs/repo/chatui/README.md
