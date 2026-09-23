---
app: kitchenhq
topic: releases
summary: 
updated: 2026-09-23
---

# Releases

## Deployment

- [F-0112] Prerequisites are Docker + Docker Compose and either an OpenAI API key or a local Ollama. — src: store/kitchenhq/docs/repo/README.md
- [F-0113] Setup: copy `.env.example` to `.env` and set `KITCHENHQ_API_KEY` (the shared secret for all three services). — src: store/kitchenhq/docs/repo/README.md
- [F-0114] Setup: copy `agents/.env.example` to `agents/.env`, set `OPENAI_API_KEY` (or `LLM_PROVIDER=ollama` + `OLLAMA_BASE_URL`) and the same `KITCHENHQ_API_KEY`. — src: store/kitchenhq/docs/repo/README.md
- [F-0115] The whole stack is started from the repo root with `docker compose up --build`, and the UI is then at http://localhost:8080. — src: store/kitchenhq/docs/repo/README.md
- [F-0116] A subset of services can be run while iterating, e.g. `docker compose up --build dbmcp chatui`. — src: store/kitchenhq/docs/repo/README.md

## Configuration

- [F-0126] `KITCHEN_DB_HOST_PATH` in the root `.env` relocates the SQLite volume (defaults to `./data`). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0127] `KITCHEN_TIMEZONE` sets the scheduler's `TZ` (default `Asia/Kolkata`). — src: store/kitchenhq/docs/repo/CLAUDE.md
