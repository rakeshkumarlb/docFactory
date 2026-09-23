---
app: kitchenhq
topic: components
summary: 
updated: 2026-09-23
---

# Components

## Backend

- [F-0261] `chatui/app.py` has no LangChain/MCP dependency and imports nothing from `agents`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0262] chatui's `/api/chat` and `/api/automations/*` proxy to agent-api (`AGENT_API_URL`, default `http://agent-api:8090`) the same way `/api/dashboard` etc. proxy to dbmcp (`DB_API_URL`). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0263] Being a pure REST client let chatui's Docker image drop the shared root `requirements.txt` and build from its own directory with just `fastapi`, `uvicorn`, `httpx` and `pydantic`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0264] chatui's inventory-mutation proxies (`PATCH /api/inventory/{id}`, `.../discard`) are commented out (no caller) now that the Pantry page is read-only. — src: store/kitchenhq/docs/repo/CLAUDE.md

## Frontend

- [F-0265] `App.jsx` holds `page` in `useState` and switch-renders `Dashboard`/`Pantry`/`WeeklyMenu`/`Recipes`/`TaskList`/`Chat`/`Automations`/`UsageStats`/`Profile`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0266] All pages except `Recipes`, `Automations` and `UsageStats` are fed from one `/api/dashboard` payload fetched on mount and patched locally after each mutation. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0267] `Automations` fetches its own data from `/api/automations/jobs` and `/api/automations/runs` and can trigger `/api/automations/invoke/{job_name}` to show a job's output without waiting for its cron time. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0268] `Recipes` calls `search_recipes`/`rate_recipe`/`delete_recipe` (via `/api/recipes*`) directly rather than reading the dashboard payload. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0269] The Recipes page's "refresh tags"/"rewrite instructions" buttons post a one-off request straight to `/api/chat`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0270] `UsageStats` reads `/api/usage-stats/daily` and `/api/usage-stats/breakdown`, which chatui proxies to dbmcp's `/api/agent-runs/usage-summary` and `/api/agent-runs/usage-breakdown`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0271] `UsageStats` renders `agent_runs.context_length`/`input_tokens`/`output_tokens`/`total_tokens` as daily totals for the last 7 days and all-time min/max/avg overall and per `agent_role`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0272] `Profile` reads/writes the single `user_profile` row via `/api/profile` (also embedded in the dashboard payload as `profile`) and does CRUD for `household_members` via `/api/household-members`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0273] The dashboard payload carries a `constants` block (`days`, `meal_types` and their order maps) so the React app never hard-codes the weekday/meal vocabulary; `WeeklyMenu.jsx` builds its grid from `data.constants`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0274] `WeeklyMenu`, `TaskList` and `Recipes` each render a `score`/`audit_feedback` badge per row, showing "Unaudited" when `score` is `null`. — src: store/kitchenhq/docs/repo/CLAUDE.md
