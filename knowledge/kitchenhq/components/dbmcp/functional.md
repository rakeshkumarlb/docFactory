---
app: kitchenhq
topic: functional
summary: 
updated: 2026-09-23
---

# Functional

## Food Inspector audit data

- [F-0188] `weekly_menu`, `weekly_plans`, `detailed_prep_schedule` and `recipes` each carry `score` (0-100) and `audit_feedback` (text) columns; `NULL` means not yet audited. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0189] `add_weekly_menu_item` resets a slot's `score`/`audit_feedback` to `NULL` on every upsert, because a re-planned slot is a new decision awaiting judgement. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0190] `detailed_prep_schedule` and `recipes` rows are audited once at creation/last edit and are not reset on read. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0191] Four MCP tool pairs drive the Food Inspector: `get_unaudited_weekly_menu_items`/`record_weekly_menu_audit`, `get_unaudited_weekly_plans`/`record_weekly_plan_audit`, `get_unaudited_prep_tasks`/`record_prep_task_audit` and `get_unaudited_recipes`/`record_recipe_audit`, all filtered on `score IS NULL`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0192] The prep-task audit pair deliberately includes cancelled tasks, since the decision being judged is what the Sous Chef planned, not whether it was performed; `get_prep_schedules` by contrast excludes them. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0193] `recipes` is a household-editable catalog, not a fifth planning role's output. — src: store/kitchenhq/docs/repo/CLAUDE.md
