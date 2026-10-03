# ReadmeForge Standard Operating Procedures (Datadog alert runbooks)

- **Document ID:** ReadmeForge-SOP-001
- **Version:** 1.0
- **Status:** Draft
- **Owner:** ReadmeForge Platform Engineering Lead
- **Approvers:** Head of Developer Experience, ReadmeForge Platform Engineering Lead
- **Created:** 2026-10-03
- **Last Updated:** 2026-10-03

## Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-10-03 | docFactory seed | Initial SOP with five Datadog alert runbooks and the alert set-up standard. |

## Application Summary

**Application Name:** ReadmeForge

**Purpose:** Lets a developer connect a GitHub repository and have its README.md generated and kept up to date automatically: ReadmeForge scans every change pushed to the repository, rebuilds the README context (entry points, dependencies, configuration, CI setup) and proposes an updated README, so documentation no longer drifts out of sync with the code.

**Business Overview:** ReadmeForge is a subscription SaaS product with two plans. The Free plan links 1 repository and includes community support only. The Pro plan links up to 10 repositories and includes customer support through a support desk. It removes the recurring chore of writing and maintaining README files, shortens onboarding for new contributors and cuts the number of 'how do I run this' questions that maintainers answer by hand. Customer data stays in India.

**Target Users:**
- Individual developers and open-source maintainers on the Free plan
- Engineering team leads and small teams on the Pro plan
- New contributors onboarding onto a connected repository
- ReadmeForge support engineers

**Key Capabilities:**
- Connect a GitHub repository through the ReadmeForge GitHub App with read-only access
- Automatically detect pushed changes to a connected repository and re-scan it
- Extract structured facts about entry points, dependencies, configuration and CI pipelines
- Draft README.md content from those facts and show a suggested diff
- Let the maintainer accept, edit or reject each suggested README change before anything is committed
- Enforce plan limits: 1 linked repository on Free, up to 10 on Pro
- Provide customer support for Pro subscribers through a support desk

**Business Criticality:** Tier 2 - paying Pro customers rely on it for documentation updates, but an outage delays README updates only and does not stop any customer's production system.

**Out Of Scope:**
- Hosting or generating any documentation other than the top-level README (for example API reference docs or wikis)
- Source hosting providers other than GitHub
- Writing code comments or docstrings inside source files
- Committing or opening pull requests without explicit maintainer approval

**Technology Summary:** Python FastAPI backend and React dashboard running as Azure Container Apps in four Azure locations in India (Central, South, West and Jio India West), backed by Azure Database for PostgreSQL, Azure Service Bus, Redis and Blob Storage, with an LLM used to draft README prose.


## Monitoring

**Monitoring Tools:**
- Datadog Metrics and Monitors (metric, APM and log monitors, composite monitors)
- Datadog APM (distributed tracing for the six ReadmeForge components)
- Datadog Synthetic Monitoring (HTTP API tests from Indian and global locations)
- Datadog Azure integration (Container Apps, Service Bus, PostgreSQL Flexible Server, Redis)
- Datadog Log Management
- Datadog Agent on Azure Container Apps (sidecar container, DogStatsD for custom metrics)
- PagerDuty

**Key Metrics:**
- API 5xx error rate (trace.http.request.errors / trace.http.request.hits for service readmeforge-api)
- API p95 latency (trace.http.request.duration.by.service.95p)
- Synthetic API availability per location
- Scan-jobs queue depth (azure.servicebus_namespaces.active_messages)
- Scan-jobs oldest-message age (custom metric readmeforge.scanjobs.oldest_message_age_seconds)
- Scan-jobs dead-letter count (azure.servicebus_namespaces.dead_lettered_messages)
- GitHub API rate-limit headroom (custom metric readmeforge.github.ratelimit.remaining_pct)
- LLM API throttling rate (custom metrics readmeforge.llm.requests.throttled and readmeforge.llm.requests.total)
- PostgreSQL CPU (azure.dbforpostgresql_flexibleservers.cpu_percent)
- PostgreSQL connections (azure.dbforpostgresql_flexibleservers.active_connections)

**Alerts:**

| Name | Condition | Severity | Response Action | Notification Channel |
|---|---|---|---|---|
| [ReadmeForge][prod] API 5xx error rate high | Datadog APM metric monitor: sum:trace.http.request.errors{service:readmeforge-api,env:production}.as_count() / sum:trace.http.request.hits{service:readmeforge-api,env:production}.as_count() above 0.02 (2%) over the last 5 minutes; warning at 1%; multi-alert by location; no-data notification after 10 minutes. | P1 - Critical | Follow the runbook 'SOP: Respond to API 5xx error spike in production' (linked in the monitor message). | PagerDuty service 'ReadmeForge Production' (Datadog handle @pagerduty-ReadmeForge-Production) and Slack #readmeforge-alerts (@slack-readmeforge-alerts) |
| [ReadmeForge][prod] Scan-jobs oldest message age high | Datadog metric monitor on the custom metric avg:readmeforge.scanjobs.oldest_message_age_seconds{env:production} (reported by repo-scanner-worker every 30 seconds): above 900 seconds (15 minutes) for 10 minutes; warning at 600 seconds. | P1 - Critical | Follow the runbook 'SOP: Recover a backed-up scan queue' (linked in the monitor message). | PagerDuty service 'ReadmeForge Production' (Datadog handle @pagerduty-ReadmeForge-Production) and Slack #readmeforge-alerts (@slack-readmeforge-alerts) |
| [ReadmeForge][prod] Scan-jobs queue depth high | Datadog metric monitor: avg:azure.servicebus_namespaces.active_messages{name:sb-readmeforge-prod,entity_name:scan-jobs} above 500 for 15 minutes; warning at 300. | P2 - Warning | Check the 'ReadmeForge - Scan pipeline' dashboard; if the oldest-message-age monitor is also close to its threshold, follow 'SOP: Recover a backed-up scan queue'. | Slack #readmeforge-alerts (@slack-readmeforge-alerts) |
| [ReadmeForge][prod] Scan-jobs dead-letter queue not empty | Datadog metric monitor: max:azure.servicebus_namespaces.dead_lettered_messages{name:sb-readmeforge-prod,entity_name:scan-jobs} above 0 for 5 minutes. | P3 - Info | Inspect the dead-lettered messages during working hours and replay them once the cause is fixed; the Scan pipeline dashboard shows the dead-letter count. | Slack #readmeforge-alerts (@slack-readmeforge-alerts) |
| [ReadmeForge][prod] GitHub API rate limit remaining low | Datadog metric monitor on the custom metric min:readmeforge.github.ratelimit.remaining_pct{env:production} (reported by repo-scanner-worker): below 15 (percent of the hourly budget) for 5 minutes; warning at 30. | P2 - Warning | Follow the runbook 'SOP: Handle GitHub API rate limit exhaustion' (linked in the monitor message). | Slack #readmeforge-alerts (@slack-readmeforge-alerts) |
| [ReadmeForge][prod] LLM API throttling rate high | Datadog metric monitor (formula): sum:readmeforge.llm.requests.throttled{env:production}.as_count() / sum:readmeforge.llm.requests.total{env:production}.as_count() above 0.10 (10%) over 10 minutes; warning at 5%. | P2 - Warning | Follow the runbook 'SOP: Handle LLM API throttling' (linked in the monitor message). | Slack #readmeforge-alerts (@slack-readmeforge-alerts) |
| [ReadmeForge][prod] PostgreSQL CPU high | Datadog metric monitor from the Azure integration: avg:azure.dbforpostgresql_flexibleservers.cpu_percent{name:psql-readmeforge-prod*} above 85 for 15 minutes; warning at 70; multi-alert by server. | P1 - Critical | Follow the runbook 'SOP: Respond to PostgreSQL CPU saturation' (linked in the monitor message). | PagerDuty service 'ReadmeForge Production' (Datadog handle @pagerduty-ReadmeForge-Production) and Slack #readmeforge-alerts (@slack-readmeforge-alerts) |
| [ReadmeForge][prod] Synthetic API availability failing | Datadog Synthetic API test GET /health on each production location (Pune, Chennai, Mumbai, Jamnagar endpoints), run every 1 minute from 3 locations; alerts when 2 of 3 locations fail for 3 consecutive runs. | P1 - Critical | Check the 'ReadmeForge - API overview' dashboard and follow 'SOP: Respond to API 5xx error spike in production'; for a single failing location check the Container Apps revision health first. | PagerDuty service 'ReadmeForge Production' (Datadog handle @pagerduty-ReadmeForge-Production) and Slack #readmeforge-alerts (@slack-readmeforge-alerts) |

**Dashboards:**
- Datadog dashboard - ReadmeForge - API overview (availability per location, latency, 5xx rate, requests per second)
- Datadog dashboard - ReadmeForge - Scan pipeline (queue depth, oldest-message age, dead-letter count, scan duration)
- Datadog dashboard - ReadmeForge - External dependencies (GitHub rate-limit headroom, LLM throttling and failure rate)
- Datadog dashboard - ReadmeForge - PostgreSQL and Redis health (CPU, connections, failover state)
- Datadog Service Catalog entry readmeforge (owners, on-call, runbook links, monitors per service)

**Log Locations:**
- Datadog Log Management, index readmeforge-prod (query service:readmeforge-* env:production, retention 15 days, archived to Azure Blob Storage for 90 days)
- Azure Log Analytics workspace law-readmeforge-prod, table ContainerAppConsoleLogs_CL (raw container output, retention 90 days)


## Support

**Support Model:** Three-level support for Pro customers: L1 Zendesk support desk, L2 application support engineers on the Platform team during business hours, and L3 engineering on-call 24x7 via PagerDuty for P1 incidents. Free-tier users are supported by the community forum and email on a best-effort basis with no SLA.

**Contacts:**

| Role | Team | Contact Channel | Support Hours | Escalates To |
|---|---|---|---|---|
| L1 customer support (Pro) | ReadmeForge Support Desk | Zendesk help centre at https://support.readmeforge.example or support@readmeforge.example | Mon-Fri 09:00-18:00 IST; first response within 1 business day | L2 application support |
| L2 application support | Platform team application support engineers | Slack #readmeforge-support-l2 and Zendesk internal escalation queue | Mon-Fri 09:00-18:00 IST | L3 engineering on-call |
| L3 engineering on-call | Engineering on-call rotation (Platform and Scanner teams) | PagerDuty service 'ReadmeForge Production'; P1 incidents reported 24x7 by email to p1@readmeforge.example | 24x7 | Engineering manager on duty |
| Free-tier community support | Community volunteers and ReadmeForge developer relations | Community forum at https://community.readmeforge.example or community@readmeforge.example | Best effort, no SLA | None; Free-tier users may upgrade to Pro for supported access |

**Escalation Path:** L1 Zendesk support desk, then L2 application support engineers, then L3 engineering on-call. P1 incidents reported 24x7 by email skip L1 and go directly to L3 via PagerDuty.

**Incident Process:** Incidents are logged as Zendesk tickets (or raised by PagerDuty from Azure Monitor alerts), classified P1-P4 within 30 minutes, and worked by the responsible level. P1 incidents open a Slack incident channel, get status updates to affected customers every hour, and are closed after a post-incident review is written within 5 business days.

**Runbooks:**
- docs/runbooks/handle-github-api-rate-limiting.md
- docs/runbooks/handle-llm-api-throttling.md
- docs/runbooks/recover-from-slow-or-backed-up-scan-queue.md
- docs/runbooks/respond-to-api-outage-or-high-latency.md
- docs/runbooks/drain-and-replay-scan-jobs-dead-letter-queue.md
- docs/runbooks/fail-over-database-to-south-india.md
- docs/runbooks/rotate-github-app-private-key.md
- docs/runbooks/raise-customer-from-free-to-pro-repository-limit.md
- docs/runbooks/add-a-new-production-location.md


## Standard Operating Procedures

**Procedures:**
1.
  - **Name:** SOP: Respond to API 5xx error spike in production
  - **Purpose:** Restore the ReadmeForge API when more than 2% of requests fail with HTTP 5xx, limiting customer impact on README scans and proposals.
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] API 5xx error rate high' is in Alert (P1, paged through PagerDuty) or the monitor '[ReadmeForge][prod] Synthetic API availability failing' alerts.
  - **Frequency:** On demand
  - **Roles:**
    - L3 engineering on-call
    - Application support engineer (L2)
    - Platform engineer
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
  - **Steps:**
    1. Acknowledge the PagerDuty incident and post 'Investigating' with the monitor link in #readmeforge-alerts.
    2. Open the dashboard 'ReadmeForge - API overview' and note which location tag (central-india, south-india, west-india, jio-west) carries the errors and when they started.
    3. In Datadog APM open Service readmeforge-api, Errors tab, and group by resource_name and error.type to find the failing endpoint and the dominant exception.
    4. Open Log Explorer with: service:readmeforge-api env:production status:error and compare the first error time with the latest deployment event shown on the dashboard timeline.
    5. If the errors began within 30 minutes of a deployment, roll the api app back: az containerapp revision list --name api --resource-group rg-readmeforge-prod-central-india, then az containerapp ingress traffic set --name api --resource-group rg-readmeforge-prod-central-india --revision-weight <previous-revision>=100
    6. If a downstream dependency is failing (the APM trace shows errors on postgresql or redis spans), follow 'SOP: Respond to PostgreSQL CPU saturation' or check Redis health on the 'PostgreSQL and Redis health' dashboard.
    7. If a single location is failing, shift traffic away from it at Azure Front Door by disabling the origin of that location, then continue the investigation there.
    8. Add the root cause and the actions taken as a note on the Datadog monitor event and update #readmeforge-alerts every 30 minutes until recovery.
  - **Verification:** The 5xx ratio on the API overview dashboard is below 1% for 15 minutes, the monitor returns to OK and all Synthetic location tests pass.
  - **Escalation:** Escalate to the Platform Engineering Lead if not mitigated within 30 minutes; publish a customer notice on the status page if customer impact exceeds 30 minutes.
2.
  - **Name:** SOP: Recover a backed-up scan queue
  - **Purpose:** Bring the scan-jobs queue back to normal processing time when repo-scanner-worker is not keeping up, so READMEs are updated within the promised window.
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] Scan-jobs oldest message age high' is in Alert (P1, paged), or the queue depth monitor stays in Warning for more than 30 minutes.
  - **Frequency:** On demand
  - **Roles:**
    - L3 engineering on-call
    - Scanner team engineer
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
  - **Steps:**
    1. Acknowledge the page and open the dashboard 'ReadmeForge - Scan pipeline'; note queue depth, oldest-message age and scans per minute.
    2. Check whether repo-scanner-worker replicas are running and healthy: az containerapp replica list --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --output table
    3. In Datadog Log Explorer run service:repo-scanner-worker env:production status:error and look for repeated failures that make jobs retry (GitHub 403/429, timeouts, out-of-memory).
    4. If errors point to GitHub rate limiting, switch to 'SOP: Handle GitHub API rate limit exhaustion' first; if they point to the LLM provider, switch to 'SOP: Handle LLM API throttling'.
    5. If workers are healthy but busy, scale out: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --max-replicas 20
    6. If one repository or installation dominates the logs (a webhook storm or a very large monorepo), note its installation id and ask the customer-support lead to apply the per-installation scan limit.
    7. Check the dead-letter count; do not purge the dead-letter queue, leave it for the dead-letter review.
    8. Once the oldest-message age is below 300 seconds, set the maximum replicas back to the standard value of 8 with the same az containerapp update command.
  - **Verification:** Oldest-message age is below 300 seconds and queue depth below 100 for 15 minutes; the monitor is OK and scans per minute is back to baseline.
  - **Escalation:** Escalate to the Scanner team lead if the age keeps rising after scaling out, and to the Platform Engineering Lead after 60 minutes of impact.
3.
  - **Name:** SOP: Handle GitHub API rate limit exhaustion
  - **Purpose:** Keep the scan pipeline running when the GitHub App installation tokens are close to their hourly API budget, without losing scan jobs or being blocked by GitHub.
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] GitHub API rate limit remaining low' is in Alert (P2, Slack), or repo-scanner-worker logs show HTTP 403 or 429 responses with X-RateLimit-Remaining 0.
  - **Frequency:** On demand
  - **Roles:**
    - Application support engineer (L2)
    - Scanner team engineer
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
  - **Steps:**
    1. Open the dashboard 'ReadmeForge - External dependencies' and read the GitHub rate-limit headroom and the time the budget resets (top of the hour).
    2. In Datadog Log Explorer run service:repo-scanner-worker env:production "X-RateLimit-Remaining" and group by @installation_id to find the heaviest consumers.
    3. If one installation dominates, check for a webhook storm or a large monorepo and note the installation id in the incident record.
    4. Reduce the load on GitHub by lowering scanner concurrency: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars SCAN_MAX_CONCURRENCY=2 GITHUB_LOW_PRIORITY_PAUSED=true
    5. Expect the queue to grow while the limit is exhausted; the jobs are retried after the reset and must not be purged.
    6. After the budget resets and the headroom is above 40%, restore the settings: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars SCAN_MAX_CONCURRENCY=8 GITHUB_LOW_PRIORITY_PAUSED=false
  - **Verification:** readmeforge.github.ratelimit.remaining_pct stays above 30 after the reset, the monitor returns to OK and the queue depth is falling.
  - **Escalation:** Escalate to the Scanner team engineer on-call if the limit is exhausted twice in one day; they review the conditional-request caching.
4.
  - **Name:** SOP: Handle LLM API throttling
  - **Purpose:** Keep README proposals flowing when the Anthropic API throttles requests, by backing off and routing proposals to the fallback model.
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] LLM API throttling rate high' is in Alert (P2, Slack), or readme-builder-worker logs show HTTP 429 responses from the Anthropic API.
  - **Frequency:** On demand
  - **Roles:**
    - Application support engineer (L2)
    - Platform engineer
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
  - **Steps:**
    1. Open the dashboard 'ReadmeForge - External dependencies' and read the LLM throttled-request ratio and failure rate.
    2. In Datadog APM open Service readme-builder-worker, filter resource anthropic.messages and confirm the 429 status and the retry-after values.
    3. Reduce parallel proposal builds: az containerapp update --name readme-builder-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars BUILD_MAX_CONCURRENCY=3
    4. Enable the fallback model route by setting LLM_FALLBACK_ENABLED=true on readme-builder-worker with the same az containerapp update command.
    5. Check the provider status page and the usage tier; if normal traffic growth causes the limit, request a higher rate limit from the provider.
    6. When the throttled ratio is below 2% for 30 minutes, set BUILD_MAX_CONCURRENCY=8 and LLM_FALLBACK_ENABLED=false again.
  - **Verification:** The throttled ratio is below 5%, the README proposal success rate on the dashboard is above 95% and the monitor is OK.
  - **Escalation:** Escalate to the Platform Engineering Lead if throttling lasts longer than 2 hours or proposals are failing for customers.
5.
  - **Name:** SOP: Respond to PostgreSQL CPU saturation
  - **Purpose:** Restore headroom on the production PostgreSQL Flexible Server when CPU stays above 85%, preventing slow queries and connection failures across the API and workers.
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] PostgreSQL CPU high' is in Alert (P1, paged).
  - **Frequency:** On demand
  - **Roles:**
    - L3 engineering on-call
    - Database engineer
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
    - Database Monitoring enabled for the server and psql access through the jump host
  - **Steps:**
    1. Acknowledge the page and open the dashboard 'ReadmeForge - PostgreSQL and Redis health'; note CPU, active connections and which server (central-india or south-india) alerts.
    2. Open Datadog Database Monitoring for the server and sort Query Metrics by total time to find the heaviest statements; note the top three.
    3. Check for long-running or blocked sessions: SELECT pid, now() - query_start AS runtime, state, left(query, 120) FROM pg_stat_activity WHERE state <> 'idle' ORDER BY runtime DESC LIMIT 10;
    4. If a runaway query from a worker is the cause, cancel it with SELECT pg_cancel_backend(<pid>); and record the statement for the Scanner team.
    5. If the load is genuine traffic growth, scale the server up one compute tier: az postgres flexible-server update --name psql-readmeforge-prod-central --resource-group rg-readmeforge-prod-central-india --sku-name Standard_D8ds_v5 --tier GeneralPurpose
    6. Reduce pressure while scaling by pausing non-urgent scans: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars SCAN_MAX_CONCURRENCY=2
    7. If the server does not recover or fails, follow the database fail-over procedure to South India in the backup and recovery chapter of the SMTD.
  - **Verification:** CPU is below 70% for 30 minutes, active connections are below 80% of the maximum and the API p95 latency stays normal.
  - **Escalation:** Escalate to the database engineer on-call after 20 minutes without improvement; inform the Platform Engineering Lead before any fail-over.

**Notes:** Datadog alert set-up and documentation standard. (1) Every production monitor is defined as code in the repository folder infra/datadog (Terraform resource datadog_monitor) and reviewed in a pull request; monitors are not edited by hand in the Datadog UI. (2) Monitors are named '[ReadmeForge][prod] <what is wrong>' and carry the tags service:readmeforge-<component>, env:production, team:readmeforge-platform, priority:p1|p2|p3 and runbook:<runbook-slug>. (3) Priority decides routing: P1 (Critical) pages the PagerDuty service 'ReadmeForge Production' and posts to #readmeforge-alerts; P2 (Warning) and P3 (Info) post to #readmeforge-alerts only. Warning thresholds are set at roughly half of the critical threshold so that responders get early notice. (4) Every P1 and P2 monitor message has the same layout: what is wrong, the threshold and the current value ({{value}}), the affected {{location.name}}, a link to the dashboard, and the runbook name with its link, wrapped in {{#is_alert}}, {{#is_warning}} and {{#is_recovery}} blocks. (5) Every P1 and P2 monitor must have a runbook in this document whose name is the same as in the monitor message; a monitor without a runbook is not released to production. (6) Runbook content comes from the Sop knowledge fact, so this document is regenerated, never edited by hand, after a runbook changes; the monitor message link is updated in the same pull request. (7) Monitors are tested in staging by lowering the threshold or sending a test event, and are reviewed after every P1 incident and at least twice a year. Commands are examples for the production subscription; always check the resource group and location before running them.
