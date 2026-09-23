---
app: kitchenhq
topic: functional
summary: 
updated: 2026-09-23
---

# Functional

## Food Inspector jobs

- [F-0194] The four audit jobs `menu_audit`, `weekly_plan_audit`, `task_audit` and `recipe_audit` are defined in `agents/app/jobs.py` with role `food_inspector`; each fetches whatever is unaudited and scores it. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0195] `menu_audit`, `weekly_plan_audit` and `task_audit` judge against the same `system.md` rules and `get_household_preferences` context the author used, whereas `recipe_audit` uses catalog-only standards and deliberately does not call `get_household_preferences`, since a catalog recipe is not scoped to one household. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0196] `weekly_plan_audit` judges each row against its own snapshot rather than a fresh `get_household_preferences` call. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0197] `weekly_plan_audit` checks completeness: every `(day, meal_type)` slot not listed in `skip_meals_snapshot` must have a saved `weekly_menu` row for that week, and a missing one is a hard fault. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0198] `weekly_plan_audit` also checks the `"week"`-scope entries of `restrictions_snapshot` (e.g. `lunch_variety`) and whether the week's dishes reflect `chef_note_snapshot` when it is non-empty. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0199] New jobs need no explicit Automations wiring: agent-api's `/jobs` lists `SCHEDULED_REQUESTS` dynamically and chatui's `/api/automations/*` proxies whatever it returns. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0200] `food_inspector` has its own prompt fragment (`agents/prompts/food_inspector.md`) but shares `system.md` verbatim like every role. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0201] The Food Inspector's `FoodInspectorResult` is passed explicitly via `JOB_RESULT_MODELS`, the same way `weekly_menu`'s `ExecutiveChefResult` is, and is not registered in `RESPONSE_FORMATS`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0202] Only the "did you check" step of an audit job is a hard `require_tools` requirement (`get_unaudited_weekly_menu_items` / `get_unaudited_weekly_plans` / `get_unaudited_prep_tasks` / `get_unaudited_recipes`); how many rows get scored is not enforced by `JOB_REQUIRED_TOOL_COUNTS`. — src: store/kitchenhq/docs/repo/CLAUDE.md

## Weekly menu job

- [F-0203] `run_agent` enforces the full Monday-Sunday week for the `weekly_menu` job via `_weekly_menu_slot_shortfall`, which checks the distinct `(day, meal)` args actually saved, not just the call count. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0204] A `weekly_menu` run that re-saved weekday slots to reach 28 calls while leaving Saturday/Sunday stale is nudged and then fails. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0205] Before the agent runs, `run_job` deterministically writes the `Skipped` placeholder for every slot excluded by `skip_meals` via `kitchendb/tools/weekly_menu.py::mark_weekly_menu_skipped` (REST-only, `POST /api/weekly-menu/skip`). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0206] The skip placeholders are written up front, before the agent's own `send_weekly_plan_email` call reads the saved menu back, so a slot skipped this week does not keep showing a stale dish from an earlier week in chatui and the plan email. — src: store/kitchenhq/docs/repo/CLAUDE.md

## Recipe catalog behaviour

- [F-0207] The Executive Chef calls `search_recipes` before inventing a dish, adapting a match rather than inventing unaided, unless `get_household_preferences.allow_recipe_invention` is false and nothing relevant comes back. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0208] The Executive Chef transcribes a household member's pasted recipe into the structured shape via `add_recipe`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0209] chatui's Recipes page ("refresh tags" / "rewrite instructions") acts on a recipe catalog id via `get_recipe`/`update_recipe`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0210] The Weekly Menu page's recipe modal makes the same kind of request against a `weekly_menu` row, touching `add_weekly_menu_item` and, when that slot has a `source_recipe_id`, the linked catalog recipe too, to keep both copies in sync. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0211] Both one-off recipe UI requests can pass the Food Inspector's last `score`/`audit_feedback` for that id as extra context, so the rewrite addresses the specific flagged issue. — src: store/kitchenhq/docs/repo/CLAUDE.md

## Email tools

- [F-0212] Email lives entirely in agent-api: dbmcp has no SMTP config, no `send_*_email` tools and no `/api/notifications/*` routes. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0213] `agents/app/email/` has one responsibility per module: `schemas`, `smtp`, `render`, `backfill` and `tools`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0214] The `schemas` module holds Pydantic `*Request` payload contracts and day/meal vocabulary. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0215] The `smtp` module handles transport and recipient resolution, reading `user_profile` over `GET {DB_API_URL}/api/profile`, never SQLite. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0216] Each `render` builder returns `(subject, text_body, html_body)`; `parse_lines` turns a `weekly_menu` JSON-array field or legacy string into a line list. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0217] The `backfill` module fetches the saved menu from `GET /api/dashboard` for `send_weekly_plan_email` when `days` is omitted, the only email data-read left besides the recipient. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0218] `make_email_tools(settings)` in the `tools` module returns the three `StructuredTool`s `send_prep_task_email`, `send_weekly_plan_email` and `send_shopping_list_email`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0219] `kitchen_agent.run_agent` appends the email tools to every run's toolset right after `get_job_context`, with the same per-request lifetime. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0220] Each email tool returns `{"sent": bool, "skipped"?: str, ...}` and never raises: a disabled `notify_on_task_creation`, an unset `SMTP_HOST` or an SMTP failure all come back as `{"sent": false}`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0221] An invalid email payload is rejected, and `send_shopping_list_email` rejects an empty `items`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0222] Only `send_weekly_plan_email`'s `days` is optional (back-filled from the saved menu), since that email summarizes a whole week and sending it is not an enforced job step. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0223] The prep and shopping-list emails take the plan/list the agent just authored and only render and send it. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0224] Recipient resolution (`user_profile` `email`/`cc_emails`/opt-out) stays in `smtp` server-side; the model never picks the address. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0225] `SMTP_*` environment variables are set on the `agent-api` compose service. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0226] The role prompts and `app/jobs.py` job prompts tell each role to send the matching email whenever it saves a prep schedule, weekly plan or shopping list. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0286] Each of the three email tools sends one multipart (plain-text + HTML) message to the household Profile address. — src: store/kitchenhq/docs/repo/agents/README.md
