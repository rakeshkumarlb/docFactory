---
app: kitchenhq
topic: operations
summary: 
updated: 2026-09-23
---

# Operations

## Scheduler

- [F-0068] agent-api fires eleven cron jobs in-process, defined in `agents/app/scheduler.py`. — src: store/kitchenhq/docs/repo/README.md
- [F-0069] Cron job times are interpreted in `KITCHEN_TIMEZONE` (default `Asia/Kolkata`). — src: store/kitchenhq/docs/repo/README.md
- [F-0070] Every scheduled job is also `POST /invoke/{job_name}` and can be triggered from the Automations page to see its output immediately. — src: store/kitchenhq/docs/repo/README.md

## Scheduled jobs

- [F-0071] Job `weekly_menu` (Executive Chef) runs Saturday 10:00 and replaces the saved menu with a fresh, complete Mon-Sun week. — src: store/kitchenhq/docs/repo/README.md
- [F-0072] Job `sunday_prep` (Sous Chef) runs Sunday 14:00 and produces one 60-minute batch-prep session for the week ahead. — src: store/kitchenhq/docs/repo/README.md
- [F-0073] Job `nightly_prep` (Sous Chef) runs daily at 20:00 and creates a task of at most 10 minutes tonight so tomorrow's breakfast and lunch are quick. — src: store/kitchenhq/docs/repo/README.md
- [F-0074] Job `morning_cooking` (Sous Chef) runs Mon-Fri 06:30 and produces a parallel cooking plan for the breakfast and lunch being made now. — src: store/kitchenhq/docs/repo/README.md
- [F-0075] Job `dinner_cooking` (Sous Chef) runs Mon-Fri 18:00 and produces a parallel cooking plan for tonight's snack and dinner. — src: store/kitchenhq/docs/repo/README.md
- [F-0076] Job `pantry_manager` (Pantry Manager) runs daily at 18:00 and proposes a shopping list for whatever is running low or needed for the week. — src: store/kitchenhq/docs/repo/README.md
- [F-0077] Job `expire_prep_tasks` (role Sous Chef) runs every 2 hours as deterministic housekeeping, flipping any prep task nobody acted on within 2 hours to `expired`. — src: store/kitchenhq/docs/repo/README.md
- [F-0078] Job `menu_audit` (Food Inspector) runs daily at 22:30 and scores every unaudited weekly-menu slot against household rules and preferences. — src: store/kitchenhq/docs/repo/README.md
- [F-0079] Job `weekly_plan_audit` (Food Inspector) runs daily at 22:35 and scores whole-week completeness and week-scope rules (e.g. lunch variety) against the context that week was actually planned under. — src: store/kitchenhq/docs/repo/README.md
- [F-0080] Job `task_audit` (Food Inspector) runs daily at 22:45 and scores every unaudited prep task, including cancelled ones (the decision is judged, not whether it happened). — src: store/kitchenhq/docs/repo/README.md
- [F-0081] Job `recipe_audit` (Food Inspector) runs daily at 23:00 and scores every unaudited catalog recipe against recipe-catalog standards only (tags, instruction quality), independent of any household's preferences. — src: store/kitchenhq/docs/repo/README.md

## Standalone run

- [F-0082] agent-api can be run standalone with `pip install -r requirements.txt` in `agents/`, then `python -m uvicorn app.server:app --host 0.0.0.0 --port 8090` for the API plus scheduler. — src: store/kitchenhq/docs/repo/README.md
- [F-0083] `python cli.py` in `agents/` gives an interactive terminal REPL with the Executive Chef, with no server. — src: store/kitchenhq/docs/repo/README.md

## Endpoints

- [F-0280] agent-api is available at `http://localhost:8090` with `/health`, `/chat`, `/jobs` and `/invoke/{job_name}`. — src: store/kitchenhq/docs/repo/agents/README.md
- [F-0281] chatui proxies to agent-api, so day-to-day the API should not need to be called directly. — src: store/kitchenhq/docs/repo/agents/README.md

## Email configuration

- [F-0282] Email configuration is env-only: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_SSL`, `SMTP_STARTTLS` and `SMTP_TIMEOUT`. — src: store/kitchenhq/docs/repo/agents/README.md
- [F-0283] `SMTP_PORT` defaults to 587 (465 with `SMTP_SSL=true`), and `SMTP_STARTTLS` defaults to true unless SSL is used. — src: store/kitchenhq/docs/repo/agents/README.md
- [F-0284] With `SMTP_HOST` unset the email tools return `{"sent": false, "skipped": ...}` and jobs are unaffected. — src: store/kitchenhq/docs/repo/agents/README.md
- [F-0285] `notify_on_task_creation = 0` on the household profile suppresses all three email tools. — src: store/kitchenhq/docs/repo/agents/README.md
