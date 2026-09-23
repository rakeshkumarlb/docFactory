# Synapse

Synapse connects pharmaceutical **manufacturers** (API and finished-formulation producers, human and animal health) with B2B **partners** (distributors, importers and marketers) around the world. It holds a database of manufacturers and their products, and of partners and the molecules they deal in per country. It suggests manufacturer ↔ partner ↔ product ↔ country matches and tracks the commercial follow-up on each.

Users work with the app **through chat**. The web UI lets them explore the data and make a few light edits: match status, follow-ups, verify/reject, and the editable vocabularies. Single user, runs locally, no auth.

## Architecture

```
ui/ (React, :5173) ──/api──────────────────────────────▶ dbmcp/ (FastAPI + MCP, :8100) ── SQLite data/synapse.db
        └──────────/agent/chat (SSE)──▶ agent/ (:8200) ──MCP /mcp──┘
                                          ├─ Ollama Cloud LLM (gemma4:31b)
                                          └─ Ollama web_search / web_fetch
```

The Vite dev server proxies `/api` → :8100 and `/agent/*` → :8200.

| Component | Path | Stack |
|---|---|---|
| **dbmcp** | `dbmcp/src/synapse_db/` | Python 3.14, FastAPI, `mcp` 2.x (`MCPServer`), SQLAlchemy 2, Alembic, rapidfuzz, openpyxl |
| **agent** | `agent/src/synapse_agent/` | Python 3.14, LangChain 1.x `create_agent`, LangGraph (AsyncSqliteSaver), langchain-ollama, langchain-mcp-adapters, ollama SDK |
| **ui** | `ui/src/` | React 19, TypeScript, Vite, Tailwind v4, TanStack Query, React Router, openapi-fetch |

### dbmcp layout
- `models.py`: the **only** schema definition. Changes need an Alembic migration (`uv run alembic revision --autogenerate -m ...`).
- `services/`: all business logic, shared by `api/routes.py` (REST) and `mcp_tools.py` (MCP). Keep endpoints and tools thin.
  - `reference.py`: countries, lookups, taxonomy, regulatory types, molecules, plus the `resolve_*` fuzzy resolvers that turn free text into canonical rows.
  - `manufacturers.py` / `partners.py`: upserts and `save_*_profile` (idempotent merge used by agents, demo seed and, later, Excel import).
  - `matching.py`: the deterministic scoring engine (see its docstring for weights), plus matches and follow-ups.
- `seed/`: reference data (countries, ~500 taxonomy entries, ~100 regulatory types, ~360 molecules, lookups) and fictional demo companies (`.example` domains, `data_source="DEMO"`).

### agent layout
- `graph.py`: the **coordinator** agent (chat and analyst). It delegates to the **Partner Researcher** and **Manufacturer Researcher** sub-agents, which are exposed to it as tools.
- `mcp_client.py`: loads the dbmcp tools and defines which tools each agent gets, plus the `MUTATING` set that triggers UI refresh.
- `prompts.py`: system prompts written for mid-size models, with numbered procedures, exact enum values, and one save call per company.
- `app.py`: `POST /chat` streams SSE events (`thread`, `token`, `tool_start`, `tool_end`, `message`, `data_changed`, `error`, `done`); `/threads` CRUD.

## Rules
- Only dbmcp touches the SQLite DB. The agent uses MCP tools, the UI uses REST.
- Research writes are saved as `verification_status=UNVERIFIED` with provenance: `data_source`, `research_run_id`, `confidence`, `source` rows. Only a user verifies a record.
- Fixed enums: usage `HUMAN|ANIMAL`, stage, partner type `DISTRIBUTOR|IMPORTER|MARKETER`, portfolio relation `CURRENTLY_SELLS|SEEKING|INTERESTED`, match status, verification.
- **Editable** vocabularies live in tables: `classification` (speciality → disease/indication), `regulatory_type`, and `lookup_value` (PRODUCT_CATEGORY, DOSAGE_FORM, CAPABILITY, TERRITORY_ROLE, SITE_CAPABILITY). Seeded rows (`is_system`) are deactivated, never deleted.
- Countries are ISO 3166-1 alpha-2. Molecules are INN names; `molecule` is the join key between products and partner portfolios.
- Web research uses only Ollama Cloud `web_search` / `web_fetch`.
- The MCP endpoint has DNS-rebinding protection. Use `localhost` / `127.0.0.1` hosts (tests use `base_url="http://localhost:8100"`); other hosts must be listed in `MCP_ALLOWED_HOSTS` (compose sets `["dbmcp:*"]`).
- Tests must never write to `data/synapse.db`. dbmcp tests use a temp DB; the agent test starts its own dbmcp on :8199.

## Commands
```powershell
.\dev.ps1 -Setup          # first run: deps, migrate + seed, demo data
.\dev.ps1                 # start dbmcp, agent, ui

# docker: whole system at http://localhost:8080 (REST docs still on :8100)
docker compose up -d --build   # reads .env; seeds on first start (SYNAPSE_LOAD_DEMO=false to skip demo)
docker compose down            # data persists in volumes dbmcp-data / agent-data (-v deletes them)

# dbmcp
cd dbmcp
uv run synapse-db seed    # migrate + reference data (idempotent)
uv run synapse-db demo    # fictional demo companies + matching (--remove to delete)
uv run synapse-db match   # recompute matches
uv run synapse-db serve   # http://localhost:8100/docs, MCP at /mcp
uv run pytest; uv run ruff check src tests; uv run ruff format src tests

# agent
cd agent
uv run synapse-agent      # http://localhost:8200/health
uv run pytest; uv run ruff check src tests

# ui
cd ui
npm run dev; npm run typecheck; npm run lint; npm run build
npm run gen:api           # regenerate src/api/schema.d.ts (dbmcp must be running)
```

## Configuration (`.env` in the repo root, never commit)
See `.env.example`: `OLLAMA_API_KEY` (required for chat and research), `OLLAMA_MODEL=gemma4:31b`, `OLLAMA_HOST`, `SYNAPSE_DB_PATH`, `DBMCP_URL`, ports.

## UI conventions
- Neumorphic, blue theme. Tokens and utilities (`neu`, `neu-sm`, `neu-xs`, `neu-inset`, `neu-inset-sm`, `brand-gradient`) are defined in `ui/src/index.css`. Reuse the primitives in `components/ui.tsx` and `components/domain.tsx`; don't hand-roll shadows.
- API types come from dbmcp's OpenAPI (`src/api/schema.d.ts`). After changing a schema, regenerate it; don't hand-edit it.
- After a mutation, invalidate TanStack queries. The chat does this automatically on `data_changed`.

## Status
- Done: schema, seed data, REST + MCP, matching v1, coordinator and researcher agents, chat UI, explorer, vocabulary editors, docker-compose (`*/Dockerfile`, `ui/nginx.conf` mirrors the Vite proxy).
- Planned: Excel import. The template is downloadable at `/api/imports/template`; `services/imports.py` holds the provision. Also planned: a world map and embeddings-based matching. See `docs/PLAN.md`.
