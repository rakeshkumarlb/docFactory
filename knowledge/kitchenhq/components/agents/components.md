---
app: kitchenhq
topic: components
summary: 
updated: 2026-09-23
---

# Components

## Prompts

- [F-0065] Prompts live in `agents/prompts/*.md`; `system.md` is a role-neutral shared base (household context, dietary rules) and each role fragment is appended as "Your role". — src: store/kitchenhq/docs/repo/README.md
- [F-0066] Job-specific detail (which day, which meals, the time cap) lives in `agents/app/jobs.py`, not in the prompts. — src: store/kitchenhq/docs/repo/README.md
- [F-0067] Each agent run gets a locally-built `get_job_context` tool, the authoritative source for date math and the intent behind a scheduled run. — src: store/kitchenhq/docs/repo/README.md

## Core entry point

- [F-0227] `agents/app/` replaces the old single `agent.py` file. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0228] `app/kitchen_agent.run_agent(role, text, settings, ...)` is the core entry point: for each call it builds a fresh LLM client (`app/llm.build_model`) and a fresh MCP tool set (`app/mcp_tools.load_tools`), runs the LangChain agent, and disposes the LLM client's HTTP connections (`app/llm.dispose_model`) in a `finally` block. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0229] `run_agent` returns the model's `structured_response` JSON when a `response_format` is in play, else the final assistant text via `_final_text()` (last non-empty assistant message, falling back to a recap of tool names). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0230] Because Ollama often ignores `response_format` and ends a job on a silent tool call, `run_agent` sends a one-shot "reply now in plain text, no more tools" nudge when a job finished its required writes but left no prose and no `structured_response`, so `agent_runs.result` is a real summary. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0231] Before this design, one LLM client per role was kept alive for the life of the process (days, in a long-running container); a long-lived Ollama connection would eventually go stale and wedge further requests, sometimes affecting Ollama access elsewhere on the machine. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0232] Every LLM/MCP connection the codebase opens has a bounded lifetime of one request or one scheduled job, and any new call site must keep that invariant. — src: store/kitchenhq/docs/repo/CLAUDE.md

## Prompts and job context

- [F-0233] The role `.md` prompt files hold only standing behaviour (identity, lane/boundaries, the standard method); everything job-specific lives in `app/jobs.py`'s `SCHEDULED_REQUESTS`, each a self-contained `PURPOSE:` line followed by numbered steps, and new job detail should stay out of the `.md` files. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0234] `system.md` has no "you are X" identity claim, since every role gets it appended before its own role fragment. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0235] `app/prompts.system_prompt_for(role, settings)` prepends a one-line `current_context_block` (current date/time in `settings.tz`) that mainly points the model at `get_job_context`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0236] `get_job_context` is built per run in `app/job_context.py`, appended by `run_agent`, and closes over `settings` and the `job_name` that `run_job` threads down. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0237] `get_job_context` returns date math in which every reference date carries its weekday name, plus the intent behind a scheduled run (`JOB_CONTEXT` gives each job a `focus`/`rationale` and a `menu_scope`). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0238] `build_job_context` resolves `menu_scope` into `job.target_menu_days`, the exact `weekly_menu` weekday rows the job acts on, because that table is keyed by weekday not date and the model must not do date-to-weekday arithmetic itself. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0239] The cron day/time is deliberately never surfaced to the model, since a job can be `/invoke`d at any time. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0240] Interactive chat gets `run_type: "interactive_chat"` and `job: null` in its job context. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0241] `zoneinfo` needs the `tzdata` package on Windows, pinned in `requirements.txt` for `sys_platform == "win32"` (Linux/Docker has it from the OS). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0242] `app/models.py` holds the structured `response_format` models: `SousChefResult` and `PantryManagerResult` are wired per role in `RESPONSE_FORMATS` (for both chat and jobs). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0243] `ExecutiveChefResult` is not in `RESPONSE_FORMATS`, so chat with the chef stays free text; it is passed to `run_agent(response_format=...)` only by the `weekly_menu` job (`JOB_RESULT_MODELS`). — src: store/kitchenhq/docs/repo/CLAUDE.md

## Jobs module

- [F-0244] `app/jobs.py` holds `SCHEDULED_REQUESTS` (canned scheduled prompts), the `JOB_ROLES` / `JOB_RESULT_MODELS` / `JOB_REQUIRED_TOOLS` / `JOB_REQUIRED_TOOL_COUNTS` maps, and `run_job()`, which passes them to `run_agent`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0245] Scheduled job prompts are deliberately silent on which day/time they normally run, since `/invoke/{job_name}` can fire any of them at any time. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0246] `run_agent` compares the tool calls actually made against `require_tools` (each must appear at least once) and `require_tool_counts` (each must appear at least N times; `weekly_menu` needs 28 `add_weekly_menu_item` calls). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0247] On a shortfall, `run_agent` sends up to `_MAX_FOLLOWUPS` corrective "still outstanding: ..., do it now" turns and then raises. — src: store/kitchenhq/docs/repo/CLAUDE.md

## History and server

- [F-0248] Chat history is not kept in process memory: `run_agent()` loads and saves each session's message list from/to dbmcp's `chat_sessions` table (`app/history.py`) using `langchain_core.messages.messages_to_dict`/`messages_from_dict`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0249] Scheduled jobs call `run_agent(..., remember=False)`, which skips chat history entirely so each scheduled run is a fresh one-shot request. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0250] `agents/app/server.py` is the single deployable unit that replaced the old `agent-worker` container; its FastAPI `lifespan` starts an `AsyncIOScheduler` (`app/scheduler.py`) that calls `run_job()` in-process, the same way the HTTP route does. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0251] agent-api exposes `POST /chat`, `POST /invoke/{job_name}`, `GET /jobs` and `GET /health`. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0252] `POST /chat` is keyed by session id with a per-session `asyncio.Lock`, so only same-session turns serialize. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0253] `cli.py` is a separate, unrelated entry point: a standalone terminal REPL over `run_agent()` for local dev with no server or scheduler. — src: store/kitchenhq/docs/repo/CLAUDE.md
