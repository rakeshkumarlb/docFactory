---
app: kitchenhq
topic: data--weekly-plan
summary: 
updated: 2026-09-23
---

# Data  Weekly Plan

## Weekly menu

- [F-0166] The `weekly_menu` job builds a week slot by slot with 28 `add_weekly_menu_item` upserts (`INSERT ... ON CONFLICT(day_of_week, meal_type) DO UPDATE`), guarded by the `UNIQUE` index on `(day_of_week, meal_type)` in `schema.sql`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0167] `add_weekly_menu_item` takes `ingredients: list[str]` and `full_recipe: list[str]` as plain-text lines stored as JSON arrays (UI and emails render them as `<ul>`/`<ol>`; `parse_lines` handles legacy string rows). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0168] `add_weekly_menu_item` requires a `description`, a short household-facing summary shown on the Weekly Menu page's meal card in place of a raw ingredient/macro preview. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0169] `add_weekly_menu_item` accepts an optional `tags` list (same freeform taxonomy as a `recipes` catalog entry's tags). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0170] `add_weekly_menu_item` accepts an optional `source_recipe_id`, the `recipes` catalog id the dish was adapted from via `search_recipes`, which tells a later "recreate instructions"/"identify tags" request whether the catalog recipe or the `weekly_menu` row is the authoritative record to edit. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0171] `add_weekly_menu_item` refreshes the row's `updated_at` on every upsert. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0172] The old whole-week `add_weekly_menu_plan` function and its `POST /api/weekly-menu/{plan,validate}` routes were removed entirely in the `dbmcp` reorg, leaving only the per-slot `add_weekly_menu_item` upsert (`POST /api/weekly-menu`). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0173] `weekly_menu` slots excluded by `skip_meals` are saved as placeholders with `dish_name='Skipped'` and `is_skipped=1`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0174] Skipped placeholders are pre-scored `score=100` so they never surface in `get_unaudited_weekly_menu_items`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0175] `add_weekly_menu_item` clears `is_skipped` back to 0 (and resets `score`/`audit_feedback` to `NULL`) whenever a real dish is saved for that slot again. — src: store/kitchenhq/docs/repo/CLAUDE.md

## Weekly plans

- [F-0176] `weekly_plans` is the whole-week counterpart to `weekly_menu`'s per-slot rows: one row per planned week (`week_start_date`/`week_end_date`, unique on `week_start_date`). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0177] Each `weekly_plans` row holds `skip_meals_snapshot`, `chef_note_snapshot` and `restrictions_snapshot` (copies of `user_profile.skip_meals`/`notes`/`restrictions`, the last filtered to `enabled: true`) as they were when that week was planned, plus its own `score`/`audit_feedback`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0178] `weekly_plan_audit` is a deliberate exception among the audits: it judges against the snapshot taken at plan time, whereas `weekly_menu`, `detailed_prep_schedule` and `recipes` audits judge against the household's current rules. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0179] A `weekly_plans` row is created deterministically, not by an agent tool call: after a successful `weekly_menu` job, `run_job` computes the week's start/end dates from `get_job_context`'s `target_menu_days` and posts them with the planning snapshot to `POST /api/weekly-plans`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0180] `POST /api/weekly-plans` is REST-only (`kitchendb/tools/weekly_plan.py::upsert_weekly_plan`) and follows the same "code posts after job completion" pattern as `agent_runs` telemetry, so an LLM cannot forget the step. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0181] The planning snapshot (`skip_meals`/`notes`/enabled `restrictions`) is fetched once before the job runs by `_fetch_planning_snapshot` in `agents/app/jobs.py`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0182] `weekly_plan.py::parse_weekly_plan_row` turns `skip_meals_snapshot`/`restrictions_snapshot` back into native JSON for every reader (`get_weekly_plans`, `get_unaudited_weekly_plans`, `record_weekly_plan_audit`, the dashboard payload). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0183] chatui's Weekly Menu page renders all three snapshot fields alongside the plan's score. — src: store/kitchenhq/docs/repo/CLAUDE.md
