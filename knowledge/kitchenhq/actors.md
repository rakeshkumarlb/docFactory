---
app: kitchenhq
topic: actors
summary: 
updated: 2026-09-23
---

# Actors

## Agent roles

- [F-0020] The Executive Chef owns the weekly menu (28 slots with full recipes and macros, described in household-facing language); its structured output `ExecutiveChefResult` is used for the weekly-menu job only. — src: store/kitchenhq/docs/repo/README.md
- [F-0021] The Executive Chef owns the recipe catalog from chat (add / find / update / rate a recipe), and chat with the chef stays free-text. — src: store/kitchenhq/docs/repo/README.md
- [F-0022] The Sous Chef owns prep schedules and parallel cooking plans, each capped in minutes, and records exactly what each task will consume so inventory can deduct on completion; its structured output is `SousChefResult`. — src: store/kitchenhq/docs/repo/README.md
- [F-0023] The Pantry Manager owns the pending shopping list (what is below threshold or short for the week), upserted so add-vs-append is never a choice; its structured output is `PantryManagerResult`. — src: store/kitchenhq/docs/repo/README.md
- [F-0024] The Food Inspector audits what the other three roles already saved (menu slots, whole-week plans, prep tasks, recipes) and records a 0-100 score plus written feedback on each; its structured output is `FoodInspectorResult`. — src: store/kitchenhq/docs/repo/README.md
- [F-0025] The Food Inspector is scheduled/automation-only and has no chat persona. — src: store/kitchenhq/docs/repo/README.md
