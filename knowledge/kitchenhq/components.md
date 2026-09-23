---
app: kitchenhq
topic: components
summary: 
updated: 2026-09-23
---

# Components

## Services

- [F-0026] KitchenHQ consists of three independently deployable services orchestrated by the root `docker-compose.yml`: dbmcp, agent-api and chatui. — src: store/kitchenhq/docs/repo/README.md

## Tech stack

- [F-0027] Backend stack: Python 3, FastAPI, FastMCP / `mcp`, LangChain 1.x, `langchain-mcp-adapters`, `langchain-openai` / `langchain-ollama`, APScheduler, SQLite. — src: store/kitchenhq/docs/repo/README.md
- [F-0028] Frontend stack: React 18, Vite, `lucide-react`. — src: store/kitchenhq/docs/repo/README.md
- [F-0029] Infrastructure: Docker Compose, with pinned dependencies throughout. — src: store/kitchenhq/docs/repo/README.md
