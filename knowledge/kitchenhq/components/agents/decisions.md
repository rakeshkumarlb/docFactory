---
app: kitchenhq
topic: decisions
summary: 
updated: 2026-09-23
---

# Decisions

## Design choices

- [F-0254] There is no per-role tool allowlist (`app/mcp_tools.load_tools()` takes no role argument); this deliberately simplified the previous `ROLE_TOOLS` filtering, and per-role restriction is easy to reintroduce if a role misuses a tool. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0255] `run_job` must always pass `trace=False`: `trace=True` returns a human-readable event transcript, not JSON, and passing it silently broke sous_chef/pantry_manager job telemetry for a while. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0256] The `result_model.model_validate(...)` check on a job's structured output is intentionally non-fatal (logs a warning, doesn't raise), because Ollama's `create_agent(..., response_format=...)` support is flaky and the tool calls/DB writes have already happened, so a validation miss must never turn a real success into a reported failure. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0257] A noncompliant weekly plan can reach the household and be acted on same-day: the `weekly_menu` job still emails the plan and `nightly_prep` still creates prep tasks before the first audit pass (Saturday 10:00 plan, Saturday 20:00 prep, Saturday 22:30 audit), and it is caught only after the fact via score/feedback, never blocked. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0258] This lack of a synchronous gate was accepted deliberately in favour of one rule source (the Food Inspector's LLM-as-judge scoring) rather than a second deterministic checker that would need syncing as restrictions become configurable. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0259] `validate_weekly_menu_policy` and its backing `menu_policy_violations` / `RESTRICTED_LUNCH_TERMS` were removed outright, not deprecated. — src: store/kitchenhq/docs/repo/CLAUDE.md
