---
doc_id: SRS1
title: KitchenHQ Software Requirements Specification
app: kitchenhq
template: SRS
template_version: 1
template_hash: 50215865b5e7
generated: 2026-09-23
status: draft
completeness: 62%
completeness_detail: filled=7 partial=11 na=0 missing=2 of 20 required
---

# KitchenHQ Software Requirements Specification

## 1 Document Control
<!-- field id=doc.control required=yes na=no source=overview hint="Document owner, author, status, approvers and distribution list" -->
PARTIAL - Document SRS1 for application `kitchenhq`, template SRS v1, status draft, generated 2026-09-23 from the approved knowledge base (`knowledge/kitchenhq/`, 307 facts from six repository documents). Missing: document owner, author, approvers and distribution list.

## 2 Revision History
<!-- field id=doc.revisions required=no na=allowed source=history hint="Table of versions: version, date, author, summary of change" -->
| Version | Date | Author | Summary of change |
|---|---|---|---|
| 0.1 | 2026-09-23 | docFactory (generated) | Initial draft generated from knowledge base proposals P-kitchenhq-20260923-01 to -06 |

## 3 Introduction
### 3.1 Purpose
<!-- field id=srs.purpose required=yes na=no source=overview hint="Purpose of this SRS and its intended audience" -->
PARTIAL - This SRS specifies the requirements of KitchenHQ, an AI sous-chef for the household that plans the week's meals, batches prep, keeps the pantry accurate and writes the shopping list, automatically on a schedule or on demand from a chat window [F-0001]. It documents the recurring daily feeding logistics (what to eat, what to defrost, what is about to run out, what goes on the list) that KitchenHQ turns into background jobs and a conversation [F-0006]. Missing: the intended audience of this SRS.
### 3.2 Scope
<!-- field id=srs.scope required=yes na=no source=overview hint="What the software will and will not do; benefits and goals" -->
PARTIAL - In scope: planning a complete Monday-Sunday menu [F-0007], generating prep checklists and cooking plans [F-0010], keeping inventory accurate as prep tasks complete [F-0011], drafting a merged and de-duplicated shopping list [F-0012], auditing the other roles' output with the Food Inspector [F-0013], chat with the Executive Chef [F-0015], and opt-in email notifications [F-0016].
Known boundaries: KitchenHQ is described as prototype-grade and not hardened for the open internet [F-0104]; it uses one shared key for the household rather than per-user accounts [F-0103]; it needs no cloud services beyond an LLM provider (OpenAI key or local Ollama) [F-0005].
Missing: an explicit out-of-scope list and the business benefits and measurable goals.
### 3.3 Glossary
<!-- field id=doc.glossary required=no na=allowed source=glossary hint="Terms, acronyms and abbreviations used in this document" -->
MISSING (optional - no question raised)

### 3.4 References
<!-- field id=doc.references required=no na=allowed source=overview hint="External or related documents, standards and links not in the document store" -->
MISSING (optional - no question raised)

## 4 Overall Description
### 4.1 Product Perspective
<!-- field id=srs.perspective required=yes na=no source=overview hint="Where the product fits: context, related systems, major components" -->
KitchenHQ is a small, self-hostable stack of three independently deployable services run with one `docker compose up` [F-0002][F-0026]. A team of LLM agents does the thinking, a SQLite database is the single source of truth, and a React UI is how the household steers the system [F-0003].

| Component | Stack and port | Role |
|---|---|---|
| dbmcp | Python FastAPI + FastMCP, port 18000 | Owns the SQLite database (`kitchen.db`) and its schema; exposes every data operation twice, as REST (`/api/*`) and as MCP tools (`/mcp`), from one FastAPI app [F-0030][F-0031] |
| agent-api (`agents/`) | Python LangChain + APScheduler, port 8090 | The only process that talks to the LLM and to dbmcp over MCP; serves `/chat` and `/invoke/{job}` and runs the cron jobs in-process; every request builds and disposes its own LLM/MCP connections [F-0032][F-0033][F-0034][F-0035] |
| chatui | React (Vite) SPA served by a thin FastAPI backend, port 8080 | Proxies CRUD calls to dbmcp and chat/automation calls to agent-api; holds no LangChain/MCP dependency [F-0036][F-0037][F-0038] |

Interactions between the components:
- chatui calls dbmcp directly for all CRUD/read data and agent-api for anything that needs the LLM (chat, "run job now") [F-0039].
- agent-api reaches dbmcp over MCP (`/mcp`) for every data operation the agent performs; its only REST calls to dbmcp are inside the email tools (recipient address and back-filling the saved menu / pending shopping list) [F-0040][F-0041].
- Each agent run's toolset is the remote MCP tools from dbmcp plus local in-process tools: `get_job_context` and the three `send_*_email` tools, which talk SMTP directly to the mail server [F-0042][F-0043].
- Cross-service constants (day / meal-type vocabulary and ordering) live in `shared/constants.py`, which `shared/sync.py` vendors as byte-identical copies into dbmcp and agents [F-0119][F-0300][F-0301].

Four specialist agent roles operate inside agent-api: Executive Chef, Sous Chef, Pantry Manager and Food Inspector [F-0004].
### 4.2 Product Functions
<!-- field id=srs.functions required=yes na=no source=functional hint="High-level summary of the major functions" -->
- Weekly menu planning: the Executive Chef reads inventory and household preferences and writes a full Monday-Sunday menu (breakfast, lunch, snack, dinner), searching the household's recipe catalog before inventing a dish, within dietary rules and prep-time caps [F-0007][F-0008][F-0009].
- Prep and cooking plans: nightly and morning jobs turn each day's menu into an ordered, time-capped prep checklist and a parallel cooking plan [F-0010].
- Inventory upkeep: completing a prep task deducts exactly what it used from inventory [F-0011].
- Shopping list: when stock dips below its threshold the Pantry Manager drafts a merged, de-duplicated shopping list [F-0012].
- Auditing: the Food Inspector scores every menu slot, weekly plan, prep task and recipe against the household's own configurable rules and leaves a written reason [F-0013][F-0014].
- Recipe catalog: a household-editable, searchable catalog with rating and hybrid keyword + semantic search [F-0062][F-0064][F-0193].
- Chat with the chef: swaps, substitutions and "what can I make" requests, with persisted, resumable conversation history [F-0015].
- Scheduled and on-demand jobs: eleven in-process cron jobs, each also invocable on demand from the Automations page [F-0068][F-0070].
- Email notifications: opt-in SMTP emails of the weekly plan, tonight's prep or the shopping list, never sent automatically [F-0016][F-0017].
- Run inspection: every scheduled run is recorded with its tool calls, output, token usage and success/failure [F-0096][F-0097].
- Household profile: a single household record with name, email, notification toggle, household members, restrictions and chef notes [F-0095].
### 4.3 User Classes and Characteristics
<!-- field id=srs.users required=yes na=no source=actors hint="Each user class, its goals and technical proficiency" -->
PARTIAL - The primary user class is the household, which steers the system through the chatui browser app and receives email notifications [F-0016][F-0095]. Access is by a single shared key for the whole household, not per-user accounts [F-0103].
The system's own actors are the four agent roles [F-0020][F-0021][F-0022][F-0023][F-0024]:
- Executive Chef: owns the weekly menu (28 slots with full recipes and macros) and the recipe catalog from chat (add / find / update / rate).
- Sous Chef: owns prep schedules and parallel cooking plans, each capped in minutes, and records what each task will consume.
- Pantry Manager: owns the pending shopping list.
- Food Inspector: audits what the other three saved and records a 0-100 score plus written feedback; scheduled/automation-only with no chat persona [F-0025].
Missing: each user class's goals and technical proficiency, and whether operators or maintainers are a separate user class.
### 4.4 Operating Environment
<!-- field id=srs.environment required=yes na=no source=operations hint="Hardware, OS, runtime, hosting and deployment environment" -->
PARTIAL - KitchenHQ runs as three Docker Compose services (dbmcp on 18000, agent-api on 8090, chatui on 8080), started from the repo root with `docker compose up --build`; prerequisites are Docker + Docker Compose and either an OpenAI API key or a local Ollama [F-0112][F-0115]. A subset can be run, e.g. `docker compose up --build dbmcp chatui` [F-0116].
Runtime stack: Python 3, FastAPI, FastMCP / `mcp`, LangChain 1.x, `langchain-mcp-adapters`, `langchain-openai` / `langchain-ollama`, APScheduler, SQLite; React 18 and Vite for the frontend; pinned dependencies throughout [F-0027][F-0028][F-0029].
Configuration: root `.env` with `KITCHENHQ_API_KEY` and `agents/.env` with the LLM provider settings [F-0113][F-0114]; `KITCHEN_TIMEZONE` sets the scheduler's `TZ` (default `Asia/Kolkata`) [F-0127]; `KITCHEN_DB_HOST_PATH` relocates the SQLite volume (default `./data`) [F-0126]. On Windows, `zoneinfo` needs the `tzdata` package [F-0241].
Each service can also run standalone [F-0082][F-0084][F-0085]; agent-api requires dbmcp reachable at `MCP_URL` (default `http://localhost:18000/mcp` outside Docker) [F-0128].
Missing: hardware sizing, supported operating systems and the hosting environment beyond self-hosting.
### 4.5 Design and Implementation Constraints
<!-- field id=srs.constraints required=yes na=allowed source=nonfunctional hint="Technology, regulatory, standards or policy constraints" -->
PARTIAL - Technology constraints: SQLite is the single source of truth and has no replication, only local timestamped snapshots [F-0003][F-0108]; `dbmcp/schema.sql` is the authoritative schema, a fresh-start script with no in-place migration of older layouts [F-0054]; every LLM/MCP connection must have a bounded lifetime of one request or one scheduled job [F-0232]; agent-api holds no long-lived agent object [F-0046]; each service builds from its own Docker context so shared code is vendored rather than imported [F-0300]; the LLM provider is OpenAI or Ollama [F-0044].
Policy and maturity constraints: authentication is one shared key, not per-user accounts [F-0103]; the system is prototype-grade and not hardened for the open internet [F-0104]; there is no CI and linting/formatting is not configured [F-0109].
Missing: regulatory, standards and organisational policy constraints.
### 4.6 Assumptions and Dependencies
<!-- field id=srs.assumptions required=yes na=allowed source=decisions hint="Assumed factors and external dependencies" -->
Dependencies:
- An LLM provider: OpenAI (`OPENAI_API_KEY`) or a local Ollama (`LLM_PROVIDER=ollama` plus `OLLAMA_BASE_URL`) [F-0044].
- Optionally an SMTP server configured via `SMTP_HOST` (and credentials); a Gmail app password works [F-0045].
- Docker and Docker Compose [F-0112].
- dbmcp must be reachable by agent-api at `MCP_URL`, with a matching `KITCHENHQ_API_KEY` [F-0128].
Assumptions:
- The database is assumed to start empty or already be on the current schema; there is no in-place migration of older layouts [F-0054].
- Household preferences are optional context: when none exist (`has_preferences: false`) every role proceeds anyway [F-0164].

## 5 Specific Requirements
### 5.1 External Interface Requirements
#### 5.1.1 User Interfaces
<!-- field id=srs.if.ui required=yes na=allowed source=functional hint="Screens, layout constraints, UI standards, accessibility" -->
PARTIAL - chatui is one React app with no router; `App.jsx` switch-renders these pages [F-0086][F-0265]:
- Dashboard: the week at a glance (today's meals, open tasks, low-stock count) [F-0087].
- Weekly Menu: every slot with ingredients and full recipe, plus its Food Inspector score/feedback badge; also shows the plan's snapshot fields [F-0088][F-0183].
- Recipes: the searchable catalog; rate a recipe, or ask the Executive Chef in one click to refresh tags or rewrite instructions with the Food Inspector's feedback as context [F-0089].
- Pantry: read-only inventory with thresholds and last-updated [F-0090].
- Tasks: prep schedules; checking one complete deducts its ingredients from inventory; scored by the Food Inspector [F-0091].
- Chat: talk to the Executive Chef; list and resume the 5 most recent conversations [F-0092].
- Automations: every scheduled job, its recent runs, and a "run now" button per job [F-0093].
- Usage Stats: daily and all-time token/context usage per agent role [F-0094].
- Profile: the single household record (name drives the greeting, email is where notifications go, notification toggle, household members, restrictions, chef notes) [F-0095].
The weekday/meal vocabulary is not hard-coded in the UI but read from the `constants` block of the dashboard payload [F-0273]. On first load the browser prompts for the access key, stores it in `localStorage` and sends it as `X-API-Key`; a 401 clears it and re-prompts [F-0101][F-0123].
Missing: layout constraints, UI standards and accessibility requirements.
#### 5.1.2 Software Interfaces
<!-- field id=srs.if.software required=yes na=allowed source=integrations hint="APIs, services, databases and libraries interfaced with, incl. protocol and data format" -->
- dbmcp REST API (`/api/*`) and MCP endpoint (`/mcp`, streamable HTTP) on port 18000, every request requiring an `X-API-Key` header [F-0031][F-0122][F-0292]; both are served from one FastAPI app [F-0130].
- agent-api HTTP endpoints on port 8090: `POST /chat`, `POST /invoke/{job_name}`, `GET /jobs`, `GET /health` [F-0251][F-0280]. `/chat` is keyed by session id [F-0252].
- chatui backend: `/api/*` routes proxying to dbmcp (`DB_API_URL`) and agent-api (`AGENT_API_URL`, default `http://agent-api:8090`), covered by the same key middleware except `/api/health` [F-0262][F-0124].
- LLM providers: OpenAI or Ollama [F-0044].
- SQLite database `kitchen.db`, owned exclusively by dbmcp [F-0030].
- Chat history is stored in dbmcp's `chat_sessions` table, and run telemetry is posted to dbmcp's `/api/agent-runs` [F-0248][F-0260].
- Usage statistics are served from dbmcp's `/api/agent-runs/usage-summary` and `/api/agent-runs/usage-breakdown` [F-0270].
#### 5.1.3 Hardware Interfaces
<!-- field id=srs.if.hardware required=yes na=allowed source=integrations hint="Devices and hardware interfaces" -->
MISSING (see Q-SRS1-15)

#### 5.1.4 Communication Interfaces
<!-- field id=srs.if.comms required=yes na=allowed source=integrations hint="Network protocols, messaging, email, notifications" -->
- HTTP REST between chatui, agent-api and dbmcp, on ports 8080, 8090 and 18000 [F-0037][F-0039][F-0262].
- MCP over streamable HTTP from agent-api to dbmcp `/mcp` [F-0040][F-0292].
- SMTP from agent-api directly to the mail server for the three email tools; `SMTP_PORT` defaults to 587 (465 with `SMTP_SSL=true`) and `SMTP_STARTTLS` defaults to true unless SSL is used [F-0043][F-0283].
- Emails are multipart (plain-text + HTML) messages to the household Profile address [F-0286]; the recipient is resolved server-side from `user_profile` and is never chosen by the model [F-0224].
- Email is opt-in and never automatic; a disabled toggle, an unset `SMTP_HOST` or an SMTP failure returns `{"sent": false}` and does not fail the job [F-0017][F-0018][F-0220].
### 5.2 Functional Requirements
#### 5.2.1 Feature List and Requirements
<!-- field id=srs.fr.list required=yes na=no source=functional hint="Per feature: description, inputs, processing, outputs, and numbered requirements (FR-nn) with priority" -->
PARTIAL - The requirements below are derived from documented system behaviour and are stated as "shall" requirements with their source facts. Missing: a priority for each requirement, and formal inputs/outputs for features other than those noted.

**Feature 1: Weekly menu planning**
- FR-01: The system shall generate a complete Monday-Sunday menu covering breakfast, lunch, snack and dinner (28 slots) from inventory and household preferences [F-0007][F-0020].
- FR-02: The Executive Chef shall search the household recipe catalog before inventing a dish [F-0008].
- FR-03: Menu planning shall respect the household's dietary rules and prep-time caps [F-0009].
- FR-04: Each menu slot shall be saved with ingredients, full recipe (plain-text lines) and a required household-facing description, and may carry tags and a `source_recipe_id` [F-0167][F-0168][F-0169][F-0170].
- FR-05: Saving a menu slot shall be an upsert keyed on `(day_of_week, meal_type)` and shall refresh `updated_at` [F-0166][F-0171].
- FR-06: A `weekly_menu` run shall be recorded as failed unless all Monday-Sunday slots were saved, judged on distinct `(day, meal)` pairs, not call count [F-0019][F-0203][F-0204].
- FR-07: Slots excluded by `skip_meals` shall be written deterministically as `Skipped` placeholders before the agent runs [F-0157][F-0173][F-0205].
- FR-08: After a successful `weekly_menu` job the system shall record a `weekly_plans` row with the planning snapshot (skip meals, chef note, enabled restrictions) [F-0177][F-0179].

**Feature 2: Prep and cooking plans**
- FR-09: The system shall produce an ordered, time-capped prep checklist and a parallel cooking plan from each day's menu [F-0010][F-0022].
- FR-10: A prep task shall record what it will consume as `ingredients_used` (`item_name`, `quantity`, `unit`) [F-0138][F-0139].
- FR-11: Checking a prep task complete shall deduct its `ingredients_used` from inventory; with none, the task becomes `completed`, otherwise `acknowledged` [F-0011][F-0140][F-0141][F-0142].
- FR-12: An `acknowledged` prep task shall reject reopening [F-0143].
- FR-13: A prep task still `assigned` more than 2 hours after creation shall be marked `expired` without touching inventory [F-0077][F-0145].
- FR-14: Prep deduction shall not guard on stock and may leave a negative balance until a shopping run [F-0053][F-0144].

**Feature 3: Shopping list**
- FR-15: The Pantry Manager shall propose a merged, de-duplicated shopping list for items below threshold or short for the week [F-0012][F-0023].
- FR-16: The shopping list shall be the single `shopping_items` table, unique on `item_name` (case-insensitive), with upsert semantics that merge `proposed_quantity` [F-0058][F-0148][F-0149].
- FR-17: Acknowledging a purchase shall add the actual quantity to inventory and delete the shopping row, idempotently [F-0060][F-0151][F-0152].
- FR-18: Inventory-affecting acknowledgements shall be idempotent via a required `acknowledgement_key` [F-0057][F-0135][F-0136].

**Feature 4: Food Inspector auditing**
- FR-19: The Food Inspector shall score (0-100) and give written feedback on menu slots, weekly plans, prep tasks (including cancelled ones) and catalog recipes; `NULL` score means unaudited [F-0013][F-0188][F-0192].
- FR-20: Audits shall run as scheduled jobs: `menu_audit`, `weekly_plan_audit`, `task_audit`, `recipe_audit` [F-0078][F-0079][F-0080][F-0081].
- FR-21: Audits shall use the household's own configurable restrictions, never a hardcoded checker; `recipe_audit` shall use catalog-only standards [F-0014][F-0195].
- FR-22: `weekly_plan_audit` shall judge completeness, week-scope restrictions and chef-note reflection against the snapshot taken when the week was planned [F-0178][F-0196][F-0197][F-0198].
- FR-23: Re-planning a menu slot shall reset its score and feedback to unaudited [F-0189].

**Feature 5: Recipe catalog**
- FR-24: A recipe shall store its structured recipe, embedding and rating on one row, recomputing the embedding on every add/update [F-0062][F-0063].
- FR-25: `search_recipes` shall combine keyword and semantic search with no external vector store; a recipe surfaces if either score clears the 0.65 threshold [F-0064][F-0186][F-0187].
- FR-26: The Executive Chef shall add, find, update and rate catalog recipes from chat, including transcribing a pasted recipe [F-0021][F-0208].

**Feature 6: Chat**
- FR-27: The system shall support chat with the Executive Chef with conversation history persisted and resumable [F-0015][F-0248].
- FR-28: The chat UI shall list the 5 most recently updated conversations and resume a chosen one [F-0092][F-0276][F-0278].

**Feature 7: Scheduling and automation**
- FR-29: The system shall run eleven cron jobs in-process, in `KITCHEN_TIMEZONE` (default `Asia/Kolkata`) [F-0068][F-0069].
- FR-30: The schedule shall be: `weekly_menu` Sat 10:00; `sunday_prep` Sun 14:00; `nightly_prep` daily 20:00; `morning_cooking` Mon-Fri 06:30; `dinner_cooking` Mon-Fri 18:00; `pantry_manager` daily 18:00; `expire_prep_tasks` every 2 hours; `menu_audit` 22:30, `weekly_plan_audit` 22:35, `task_audit` 22:45, `recipe_audit` 23:00, daily [F-0071][F-0072][F-0073][F-0074][F-0075][F-0076][F-0077][F-0078][F-0079][F-0080][F-0081].
- FR-31: Every job shall also be invocable on demand via `POST /invoke/{job_name}` from the Automations page [F-0070].
- FR-32: A job that stops short of its required DB writes shall be recorded as failed with the shortfall [F-0019][F-0247].
- FR-33: Every run, successful or failed, shall be recorded with tool calls, output and token/context usage and be visible on the Usage Stats page [F-0096][F-0097][F-0260].

**Feature 8: Email notifications**
- FR-34: The agents shall be able to email the weekly plan, tonight's prep and the shopping list to the Profile address, only when a job step asks for it [F-0016][F-0017].
- FR-35: Email tools shall never raise; when disabled (`notify_on_task_creation = 0`), `SMTP_HOST` unset or SMTP failing they shall return `{"sent": false}` [F-0018][F-0220][F-0284][F-0285].

**Feature 9: Household profile**
- FR-36: The system shall hold one household profile with name, email, notification toggle, household members, restrictions (scoped `per_meal` or `week`) and chef notes [F-0061][F-0095][F-0153][F-0155].
- FR-37: Household members shall be managed via REST only, from the Profile page [F-0154].
#### 5.2.2 Use Cases or User Stories
<!-- field id=srs.fr.usecases required=no na=allowed source=functional hint="Key use cases or user stories that illustrate the requirements" -->
MISSING (optional - no question raised)

### 5.3 Non-Functional Requirements
#### 5.3.1 Performance
<!-- field id=srs.nfr.performance required=yes na=allowed source=nonfunctional hint="Response time, throughput, capacity targets" -->
MISSING (see Q-SRS1-19)

#### 5.3.2 Security and Privacy
<!-- field id=srs.nfr.security required=yes na=allowed source=nonfunctional hint="Authentication, authorisation, data protection, audit" -->
PARTIAL - Authentication: a single shared secret, `KITCHENHQ_API_KEY`, gates every REST and MCP request across the three services [F-0098]; a `require_api_key` middleware checks `X-API-Key` on every route except `/api/health` on dbmcp and chatui [F-0099][F-0124]; on dbmcp it is outer middleware so it also covers the mounted `/mcp` app, with no separate MCP-layer auth [F-0100]. All three services refuse to start without the key, and `docker-compose.yml` fails fast if it is missing [F-0120][F-0121]. The key can be generated with `secrets.token_urlsafe(32)` [F-0102].
The browser stores the key in `localStorage` and sends it as `X-API-Key`; a 401 clears it and re-prompts [F-0101][F-0123].
Authorisation model: one shared key for the whole household, not per-user accounts [F-0103]. Recipient of email is resolved server-side and never chosen by the model [F-0224]. The system is prototype-grade and not hardened for the open internet [F-0104].
Missing: authorisation roles, data protection and privacy requirements, transport encryption, and audit requirements.
#### 5.3.3 Reliability and Availability
<!-- field id=srs.nfr.reliability required=yes na=allowed source=nonfunctional hint="Uptime targets, failure handling, backup and recovery" -->
PARTIAL - Failure handling: a job that stops short of its required writes is nudged with corrective follow-ups and then recorded as failed, never as a blank completed [F-0019][F-0247]; email failures never fail a job [F-0018][F-0220]; every LLM/MCP connection is disposed after one request or job so a stale connection cannot wedge later requests [F-0046][F-0047]; inventory acknowledgements are replay-safe [F-0135].
Backup and recovery: `python dbmcp/scripts/backup_db.py` snapshots the database into `dbmcp/backups/` using the SQLite online-backup API (safe under concurrent writers), keeping the last 14 [F-0105][F-0106]; daily scheduling via cron / Task Scheduler is advised [F-0107][F-0297]. There is no replication [F-0108].
Missing: uptime/availability targets and RTO/RPO.
#### 5.3.4 Usability
<!-- field id=srs.nfr.usability required=no na=allowed source=nonfunctional hint="Ease-of-use and accessibility requirements" -->
MISSING (optional - no question raised)

#### 5.3.5 Maintainability and Portability
<!-- field id=srs.nfr.maintainability required=no na=allowed source=nonfunctional hint="Supportability, configurability, portability requirements" -->
PARTIAL - Configuration is environment-driven (`KITCHENHQ_API_KEY`, `KITCHEN_TIMEZONE`, `KITCHEN_DB_HOST_PATH`, `SMTP_*`, `MCP_URL`, `DB_API_URL`, `AGENT_API_URL`) [F-0113][F-0126][F-0127][F-0128][F-0129][F-0282]. Dependencies are pinned [F-0029]. Shared constants are edited once in `shared/constants.py` and synced, with `sync.py --check` and a dbmcp test guarding drift [F-0305][F-0306][F-0307]. Automated tests exist for dbmcp only; there is no CI and no linting/formatting configured [F-0109][F-0110][F-0111]. The stack is portable via Docker Compose and each service can run standalone [F-0112][F-0082][F-0084][F-0085]. Missing: formal maintainability and portability requirements.
### 5.4 Data Requirements
<!-- field id=srs.data required=yes na=allowed source=data hint="Entities, key attributes, retention, volumes and data quality rules" -->
PARTIAL - `dbmcp/schema.sql` is the single source of truth for the schema (a fresh-start `CREATE TABLE IF NOT EXISTS` script; `db_design.md` documents it for humans and `schema.sql` wins on disagreement) [F-0054][F-0055]. Key entities and attributes documented so far:
- `inventory` and `inventory_transactions`: quantities without a `>= 0` CHECK; idempotency keys recorded in `inventory_transactions.idempotency_key` [F-0136][F-0144].
- `shopping_items`: the one pending list, unique on `item_name` (NOCASE) [F-0058][F-0148].
- `detailed_prep_schedule`: `detailed_instructions`, `ingredients_used` JSON, `status` (`assigned`, `completed`, `acknowledged`, `expired`, cancelled), `created_at`, `score`, `audit_feedback` [F-0138][F-0141][F-0142][F-0145][F-0188].
- `weekly_menu`: one row per `(day_of_week, meal_type)` with ingredients, full recipe, description, tags, `source_recipe_id`, `is_skipped`, `updated_at`, `score`, `audit_feedback` [F-0166][F-0167][F-0168][F-0169][F-0170][F-0173][F-0188].
- `weekly_plans`: one row per planned week (`week_start_date`, `week_end_date`, unique on `week_start_date`) with `skip_meals_snapshot`, `chef_note_snapshot`, `restrictions_snapshot`, `score`, `audit_feedback` [F-0176][F-0177].
- `recipes`: structured recipe, embedding, rating, `score`, `audit_feedback` [F-0062][F-0188].
- `household_members`: `id`, `name`, `dietary_preferences` JSON array, `health_conditions` JSON array [F-0153].
- `user_profile`: `restrictions`, `allow_recipe_invention`, `allow_unapproved_recipes`, `skip_meals`, `preferred_tags`, `excluded_tags`, `notes`, `favorite_recipes` (legacy), email and notification settings [F-0155][F-0156][F-0157][F-0158][F-0160][F-0162].
- `chat_sessions` (message lists) and `agent_runs` (`context_length`, `input_tokens`, `output_tokens`, `total_tokens`, `agent_role`, result) [F-0248][F-0271].
Retention: the chat-session listing returns only the 5 most recent sessions but does not prune anything [F-0276]; database backups keep the last 14 snapshots [F-0105].
Missing: data volumes, retention rules for chat history and run records, and data quality rules.

## 6 Appendices
### 6.1 Requirements Traceability
<!-- field id=srs.traceability required=no na=allowed source=functional hint="Mapping of requirements to business needs and source documents" -->
MISSING (optional - no question raised)

### 6.2 Open Issues
<!-- field id=srs.open-issues required=yes na=allowed source=open-questions hint="Unresolved questions and TBD items" -->
- The README architecture diagram labels agent-api "6 cron jobs, in-process", while the rest of the documentation lists 11; the diagram is presumed stale [F-0117].
- CLAUDE.md says the Profile email is where dbmcp sends the "new prep task" notification, but email lives entirely in agent-api; the dbmcp wording is presumed stale [F-0279].
- chatui/README.md describes a "long-lived Executive Chef agent" and a local run recipe (root requirements, `MCP_URL`, `uvicorn chatui.app:app`) that contradict the other documents; presumed stale [F-0287].
- `allow_unapproved_recipes` is captured but unused until a recipe-approval workflow exists [F-0156].
- A noncompliant weekly plan can reach the household (emailed, prep tasks created) before the first audit; this was accepted deliberately, but no compensating control is documented [F-0257][F-0258].

## 7 Sources
<!-- field id=doc.sources required=yes na=no source=none hint="Relative markdown links to every original document in store/ that this document was built from" -->
- [README.md (v1)](../../store/kitchenhq/docs/repo/README.md)
- [CLAUDE.md (v1)](../../store/kitchenhq/docs/repo/CLAUDE.md)
- [agents/README.md (v1)](../../store/kitchenhq/docs/repo/agents/README.md)
- [chatui/README.md (v1)](../../store/kitchenhq/docs/repo/chatui/README.md)
- [dbmcp/README.md (v1)](../../store/kitchenhq/docs/repo/dbmcp/README.md)
- [shared/README.md (v1)](../../store/kitchenhq/docs/repo/shared/README.md)
