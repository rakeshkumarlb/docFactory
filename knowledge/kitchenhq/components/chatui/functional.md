---
app: kitchenhq
topic: functional
summary: 
updated: 2026-09-23
---

# Functional

## Pages

- [F-0086] chatui is one React app with no router; `App.jsx` switch-renders each page. — src: store/kitchenhq/docs/repo/README.md
- [F-0087] The Dashboard page shows the week at a glance: today's meals, open tasks and the low-stock count. — src: store/kitchenhq/docs/repo/README.md
- [F-0088] The Weekly Menu page shows every slot with ingredients and full recipe, plus its Food Inspector score/feedback badge. — src: store/kitchenhq/docs/repo/README.md
- [F-0089] The Recipes page is the household's searchable catalog: a recipe can be rated, or the Executive Chef can be asked in one click to refresh its tags or rewrite its instructions, with the Food Inspector's own feedback fed in as context. — src: store/kitchenhq/docs/repo/README.md
- [F-0090] The Pantry page is a read-only inventory view with thresholds and last-updated. — src: store/kitchenhq/docs/repo/README.md
- [F-0091] The Tasks page shows prep schedules; checking one complete deducts its ingredients from inventory, and tasks are also scored by the Food Inspector. — src: store/kitchenhq/docs/repo/README.md
- [F-0092] The Chat page talks to the Executive Chef and can list and resume the 5 most recent conversations. — src: store/kitchenhq/docs/repo/README.md
- [F-0093] The Automations page lists every scheduled job with its recent runs and a "run now" button per job. — src: store/kitchenhq/docs/repo/README.md
- [F-0094] The Usage Stats page shows daily and all-time token/context usage broken down per agent role. — src: store/kitchenhq/docs/repo/README.md
- [F-0095] The Profile page edits the single household record: name (drives the greeting), email (where notifications go), notification toggle, household members, restrictions and chef notes. — src: store/kitchenhq/docs/repo/README.md

## Chat history

- [F-0275] `Chat.jsx` can list and switch back into recent conversations via `GET /api/chat-sessions` (proxied to dbmcp's `GET /api/chat-sessions?limit=5`) and `GET /api/chat-sessions/{id}`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0276] dbmcp's chat-session listing returns the 5 most recently updated sessions ordered by `updated_at`, with a preview built from the first human message; it does not prune anything, only limits what is returned. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0277] For `GET /api/chat-sessions/{id}`, chatui converts dbmcp's raw LangChain-dict messages into the simple `{role, content}` shape the UI renders, dropping tool-call and empty-content messages. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0278] Picking a past conversation swaps the browser's stored `session_id` and repopulates the transcript; agent-api's history load/save is unaffected. — src: store/kitchenhq/docs/repo/CLAUDE.md
