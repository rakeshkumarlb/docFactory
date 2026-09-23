---
app: kitchenhq
topic: data
summary: 
updated: 2026-09-23
---

# Data

## Schema

- [F-0054] `dbmcp/schema.sql` is the single source of truth for the schema: a fresh-start `CREATE TABLE IF NOT EXISTS` script with no in-place migration of older layouts. — src: store/kitchenhq/docs/repo/README.md
- [F-0055] `dbmcp/db_design.md` documents the same schema for humans; if it disagrees with `schema.sql`, `schema.sql` wins. — src: store/kitchenhq/docs/repo/README.md
- [F-0056] Data operations are plain functions in `kitchendb/tools/*.py`, added once to a `FastMCP` instance (`/mcp`) and re-exposed as thin REST routes (`/api/*`) from the same FastAPI app. — src: store/kitchenhq/docs/repo/README.md

## Inventory

- [F-0057] Inventory writes are propose-then-acknowledge: the propose step never touches `inventory`, and the acknowledge step is idempotent via a required `acknowledgement_key`. — src: store/kitchenhq/docs/repo/README.md

## Shopping

- [F-0058] There is no "shopping list" entity: `shopping_items` is the one pending list, unique on `item_name`. — src: store/kitchenhq/docs/repo/README.md
- [F-0059] `add_shopping_items` is an upsert. — src: store/kitchenhq/docs/repo/README.md
- [F-0060] Acknowledging a shopping purchase adds the real quantity to `inventory` and deletes the `shopping_items` row. — src: store/kitchenhq/docs/repo/README.md
- [F-0148] `shopping_items.item_name` is unique with `COLLATE NOCASE`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0149] `add_shopping_items` is an `INSERT ... ON CONFLICT(item_name) DO UPDATE` upsert that merges `proposed_quantity`, so callers never choose between creating and appending. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0150] `edit_shopping_item`, `delete_shopping_item` and `clear_shopping_items` round out add/edit/delete/clear for the shopping list. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0151] `acknowledge_shopping_items` is REST-only (not an MCP tool) because it is a human action, not an agent one; it matches each purchased item to `inventory` by `item_name`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0152] Because the `shopping_items` row is gone on replay, shopping acknowledgement idempotency is checked against `inventory_transactions.idempotency_key` (`{acknowledgement_key}:{shopping_item_id}`) instead of a status flag. — src: store/kitchenhq/docs/repo/CLAUDE.md

## Idempotency

- [F-0136] Idempotency keys for inventory-affecting acknowledgements are recorded in `inventory_transactions.idempotency_key`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0137] Shopping's `acknowledge_shopping_items` returns `{"replayed": True, ...}` on a repeat call, whereas prep's `capture_prep_completion_status` returns the unchanged row with no `replayed` flag, so a prep replay is recognised by `status`. — src: store/kitchenhq/docs/repo/CLAUDE.md

## Prep tasks

- [F-0138] `add_detailed_prep_schedule(detailed_instructions: list[str], ingredients_used: list[{item_name, quantity, unit}])` stores both as validated JSON on the row with `status='assigned'` and `created_at` stamped. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0139] `ingredients_used` is the only place the agent supplies what a prep task will consume; it is matched by `item_name`, never `inventory_id`, since the caller cannot reliably know an id ahead of time. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0140] Prep has no separate acknowledge endpoint: `capture_prep_completion_status(is_completed=True)` is the one human action ("check this task off") and always deducts whatever `ingredients_used` holds. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0141] A prep task with empty `ingredients_used` becomes `status='completed'` when checked off (nothing to deduct, so it can still be reopened). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0142] A prep task with non-empty `ingredients_used` becomes `status='acknowledged'` when checked off (key `prep-<id>-complete`) and is locked against reopening, because undoing a real deduction is not safe to automate. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0143] Both `completed` and `acknowledged` mean "done" to the household and land in the same "recently completed" bucket (dashboard, `get_prep_schedules`, chatui's Task List); an `acknowledged` row rejects a later `is_completed=False` call with 400 while a `completed` one does not. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0144] `inventory.quantity` and `inventory_transactions.quantity_after` have no `>= 0` CHECK in `schema.sql`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0145] A prep task still `'assigned'` more than 2 hours after `created_at` is stale; `expire_stale_prep_tasks()` (MCP tool, no REST route) flips it to `status='expired'` without touching inventory. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0146] `capture_prep_completion_status` and `cancel_prep_schedule` reject an expired prep task with 400, as they do an already-`acknowledged` row. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0147] The `expire_prep_tasks` job is the only caller of `expire_stale_prep_tasks()`; it is a deterministic housekeeping sweep, not a planning decision. — src: store/kitchenhq/docs/repo/CLAUDE.md
