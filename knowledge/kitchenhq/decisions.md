---
app: kitchenhq
topic: decisions
summary: 
updated: 2026-09-23
---

# Decisions

## Architecture

- [F-0046] Bounded connection lifetime: agent-api builds a fresh LLM client and MCP toolset per request and disposes them in a `finally` block; there is no long-lived agent object and no cross-call lock, so concurrent chats and jobs run fully independently. — src: store/kitchenhq/docs/repo/README.md
- [F-0047] The bounded-connection-lifetime design is a deliberate fix for a real incident where a stale long-lived Ollama connection wedged the host. — src: store/kitchenhq/docs/repo/README.md
- [F-0048] The cron scheduler runs in-process on an `AsyncIOScheduler` inside the agent-api process, with no extra worker container and no network hop. — src: store/kitchenhq/docs/repo/README.md
- [F-0049] Role boundaries are enforced by the prompt, not by hiding tools: all four roles get the identical MCP toolset. — src: store/kitchenhq/docs/repo/README.md

## Menu policy

- [F-0050] The weekly menu has no deterministic policy check: `user_profile.restrictions` is the only rule source. — src: store/kitchenhq/docs/repo/README.md
- [F-0051] The Executive Chef reads the restrictions via `get_household_preferences` while planning, and the Food Inspector reads the same thing while auditing (`menu_audit` for per-meal rules, `weekly_plan_audit` for week-scope rules such as lunch variety). — src: store/kitchenhq/docs/repo/README.md
- [F-0052] There is no synchronous gate before a plan is saved or emailed. — src: store/kitchenhq/docs/repo/README.md
