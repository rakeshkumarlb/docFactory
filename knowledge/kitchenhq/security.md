---
app: kitchenhq
topic: security
summary: 
updated: 2026-09-23
---

# Security

## Authentication

- [F-0098] A single shared secret, `KITCHENHQ_API_KEY`, gates every REST and MCP request across all three services. — src: store/kitchenhq/docs/repo/README.md
- [F-0099] A `require_api_key` middleware sits in front of every route except `/api/health` on dbmcp and chatui, checking `X-API-Key` against `KITCHENHQ_API_KEY`. — src: store/kitchenhq/docs/repo/README.md
- [F-0100] On dbmcp the middleware is outer FastAPI middleware, so it also covers the mounted MCP app at `/mcp`; there is no separate MCP-layer auth. — src: store/kitchenhq/docs/repo/README.md
- [F-0101] The browser prompts for `KITCHENHQ_API_KEY`, stores it in `localStorage` and sends it as `X-API-Key` on every request. — src: store/kitchenhq/docs/repo/README.md
- [F-0102] The shared key can be generated with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. — src: store/kitchenhq/docs/repo/README.md
- [F-0103] Authentication is one shared key for the whole household, not per-user accounts. — src: store/kitchenhq/docs/repo/README.md
- [F-0120] All three services require `KITCHENHQ_API_KEY` to be set and refuse to start without it. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0121] `docker-compose.yml` fails fast via `${KITCHENHQ_API_KEY:?...}` if `KITCHENHQ_API_KEY` is missing from the root `.env`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0122] Every dbmcp request (REST and MCP) needs an `X-API-Key: <KITCHENHQ_API_KEY>` header. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0123] A 401 from any chatui `/api/*` call clears the stored key in the browser and re-prompts for it. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0124] chatui's own `/api/*` routes (except `/api/health`) sit behind the same `require_api_key` middleware pattern as dbmcp, since real users hit them directly from the browser. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0125] The chatui React app has a key-entry gate (`src/components/AccessGate.jsx`) in front of everything else in `App.jsx`; `src/services/api.js` attaches the stored key to every request and clears it on a 401. — src: store/kitchenhq/docs/repo/CLAUDE.md
