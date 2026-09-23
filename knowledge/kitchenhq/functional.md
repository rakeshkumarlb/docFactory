---
app: kitchenhq
topic: functional
summary: 
updated: 2026-09-23
---

# Functional

## Planning

- [F-0007] The Executive Chef reads the inventory and household preferences and writes a full Monday-Sunday menu covering breakfast, lunch, snack and dinner. — src: store/kitchenhq/docs/repo/README.md
- [F-0008] The Executive Chef searches the household's own recipe catalog for a match before inventing a dish. — src: store/kitchenhq/docs/repo/README.md
- [F-0009] Menu planning respects the household's dietary rules and prep-time caps. — src: store/kitchenhq/docs/repo/README.md
- [F-0010] Nightly and morning jobs turn each day's menu into an ordered, time-capped prep checklist and a parallel cooking plan. — src: store/kitchenhq/docs/repo/README.md

## Pantry and shopping

- [F-0011] Completing a prep task deducts exactly what it used from inventory. — src: store/kitchenhq/docs/repo/README.md
- [F-0012] When stock dips below its threshold, the Pantry Manager drafts a shopping list that is merged and de-duplicated. — src: store/kitchenhq/docs/repo/README.md

## Auditing

- [F-0013] The Food Inspector never plans anything; it scores every menu slot, weekly plan, prep task and recipe saved by the other three roles against the household's own rules and leaves a written reason. — src: store/kitchenhq/docs/repo/README.md
- [F-0014] Food Inspector scoring uses the household's own configurable rules, never a hardcoded checker. — src: store/kitchenhq/docs/repo/README.md

## Chat

- [F-0015] Chat with the chef supports swaps, substitutions and "what can I make with what's in the fridge" requests, with full conversation history persisted and resumable. — src: store/kitchenhq/docs/repo/README.md

## Email

- [F-0016] Email notifications are opt-in via SMTP: the agents can email the weekly plan, tonight's prep or the shopping list to the address on the Profile page. — src: store/kitchenhq/docs/repo/README.md
- [F-0017] Email is never sent automatically: a job asks for an email as one of its steps. — src: store/kitchenhq/docs/repo/README.md
- [F-0018] A disabled notification toggle or an unset `SMTP_HOST` returns `{"sent": false}` and does not fail the job. — src: store/kitchenhq/docs/repo/README.md

## Job execution

- [F-0019] If a job stops short of its required DB writes, `run_agent` sends corrective nudges and then raises, so a job that saved 22 of 28 menu slots is recorded `failed` with the shortfall, never a blank `completed`. — src: store/kitchenhq/docs/repo/README.md
