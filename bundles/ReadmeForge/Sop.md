---
type: "Sop"
title: "ReadmeForge.Sop"
generated: { by: "seed", at: 2026-10-03T12:30:22Z }
status: draft
fact_key: "ReadmeForge.Sop"
version: 1
completeness: 100
---

# ReadmeForge.Sop

## Notes

Datadog alert set-up and documentation standard. (1) Every production monitor is defined as code in the repository folder infra/datadog (Terraform resource datadog_monitor) and reviewed in a pull request; monitors are not edited by hand in the Datadog UI. (2) Monitors are named '[ReadmeForge][prod] <what is wrong>' and carry the tags service:readmeforge-<component>, env:production, team:readmeforge-platform, priority:p1|p2|p3 and runbook:<runbook-slug>. (3) Priority decides routing: P1 (Critical) pages the PagerDuty service 'ReadmeForge Production' and posts to #readmeforge-alerts; P2 (Warning) and P3 (Info) post to #readmeforge-alerts only. Warning thresholds are set at roughly half of the critical threshold so that responders get early notice. (4) Every P1 and P2 monitor message has the same layout: what is wrong, the threshold and the current value ({{value}}), the affected {{location.name}}, a link to the dashboard, and the runbook name with its link, wrapped in {{#is_alert}}, {{#is_warning}} and {{#is_recovery}} blocks. (5) Every P1 and P2 monitor must have a runbook in this document whose name is the same as in the monitor message; a monitor without a runbook is not released to production. (6) Runbook content comes from the Sop knowledge fact, so this document is regenerated, never edited by hand, after a runbook changes; the monitor message link is updated in the same pull request. (7) Monitors are tested in staging by lowering the threshold or sending a test event, and are reviewed after every P1 incident and at least twice a year. Commands are examples for the production subscription; always check the resource group and location before running them.

## Procedures

- Item 1
  - **Escalation:** Escalate to the Platform Engineering Lead if not mitigated within 30 minutes; publish a customer notice on the status page if customer impact exceeds 30 minutes.
  - **Frequency:** On demand
  - **Name:** SOP: Respond to API 5xx error spike in production
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
  - **Purpose:** Restore the ReadmeForge API when more than 2% of requests fail with HTTP 5xx, limiting customer impact on README scans and proposals.
  - **Roles:**
    - L3 engineering on-call
    - Application support engineer (L2)
    - Platform engineer
  - **Steps:**
    - Acknowledge the PagerDuty incident and post 'Investigating' with the monitor link in #readmeforge-alerts.
    - Open the dashboard 'ReadmeForge - API overview' and note which location tag (central-india, south-india, west-india, jio-west) carries the errors and when they started.
    - In Datadog APM open Service readmeforge-api, Errors tab, and group by resource_name and error.type to find the failing endpoint and the dominant exception.
    - Open Log Explorer with: service:readmeforge-api env:production status:error and compare the first error time with the latest deployment event shown on the dashboard timeline.
    - If the errors began within 30 minutes of a deployment, roll the api app back: az containerapp revision list --name api --resource-group rg-readmeforge-prod-central-india, then az containerapp ingress traffic set --name api --resource-group rg-readmeforge-prod-central-india --revision-weight <previous-revision>=100
    - If a downstream dependency is failing (the APM trace shows errors on postgresql or redis spans), follow 'SOP: Respond to PostgreSQL CPU saturation' or check Redis health on the 'PostgreSQL and Redis health' dashboard.
    - If a single location is failing, shift traffic away from it at Azure Front Door by disabling the origin of that location, then continue the investigation there.
    - Add the root cause and the actions taken as a note on the Datadog monitor event and update #readmeforge-alerts every 30 minutes until recovery.
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] API 5xx error rate high' is in Alert (P1, paged through PagerDuty) or the monitor '[ReadmeForge][prod] Synthetic API availability failing' alerts.
  - **Verification:** The 5xx ratio on the API overview dashboard is below 1% for 15 minutes, the monitor returns to OK and all Synthetic location tests pass.
- Item 2
  - **Escalation:** Escalate to the Scanner team lead if the age keeps rising after scaling out, and to the Platform Engineering Lead after 60 minutes of impact.
  - **Frequency:** On demand
  - **Name:** SOP: Recover a backed-up scan queue
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
  - **Purpose:** Bring the scan-jobs queue back to normal processing time when repo-scanner-worker is not keeping up, so READMEs are updated within the promised window.
  - **Roles:**
    - L3 engineering on-call
    - Scanner team engineer
  - **Steps:**
    - Acknowledge the page and open the dashboard 'ReadmeForge - Scan pipeline'; note queue depth, oldest-message age and scans per minute.
    - Check whether repo-scanner-worker replicas are running and healthy: az containerapp replica list --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --output table
    - In Datadog Log Explorer run service:repo-scanner-worker env:production status:error and look for repeated failures that make jobs retry (GitHub 403/429, timeouts, out-of-memory).
    - If errors point to GitHub rate limiting, switch to 'SOP: Handle GitHub API rate limit exhaustion' first; if they point to the LLM provider, switch to 'SOP: Handle LLM API throttling'.
    - If workers are healthy but busy, scale out: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --max-replicas 20
    - If one repository or installation dominates the logs (a webhook storm or a very large monorepo), note its installation id and ask the customer-support lead to apply the per-installation scan limit.
    - Check the dead-letter count; do not purge the dead-letter queue, leave it for the dead-letter review.
    - Once the oldest-message age is below 300 seconds, set the maximum replicas back to the standard value of 8 with the same az containerapp update command.
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] Scan-jobs oldest message age high' is in Alert (P1, paged), or the queue depth monitor stays in Warning for more than 30 minutes.
  - **Verification:** Oldest-message age is below 300 seconds and queue depth below 100 for 15 minutes; the monitor is OK and scans per minute is back to baseline.
- Item 3
  - **Escalation:** Escalate to the Scanner team engineer on-call if the limit is exhausted twice in one day; they review the conditional-request caching.
  - **Frequency:** On demand
  - **Name:** SOP: Handle GitHub API rate limit exhaustion
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
  - **Purpose:** Keep the scan pipeline running when the GitHub App installation tokens are close to their hourly API budget, without losing scan jobs or being blocked by GitHub.
  - **Roles:**
    - Application support engineer (L2)
    - Scanner team engineer
  - **Steps:**
    - Open the dashboard 'ReadmeForge - External dependencies' and read the GitHub rate-limit headroom and the time the budget resets (top of the hour).
    - In Datadog Log Explorer run service:repo-scanner-worker env:production "X-RateLimit-Remaining" and group by @installation_id to find the heaviest consumers.
    - If one installation dominates, check for a webhook storm or a large monorepo and note the installation id in the incident record.
    - Reduce the load on GitHub by lowering scanner concurrency: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars SCAN_MAX_CONCURRENCY=2 GITHUB_LOW_PRIORITY_PAUSED=true
    - Expect the queue to grow while the limit is exhausted; the jobs are retried after the reset and must not be purged.
    - After the budget resets and the headroom is above 40%, restore the settings: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars SCAN_MAX_CONCURRENCY=8 GITHUB_LOW_PRIORITY_PAUSED=false
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] GitHub API rate limit remaining low' is in Alert (P2, Slack), or repo-scanner-worker logs show HTTP 403 or 429 responses with X-RateLimit-Remaining 0.
  - **Verification:** readmeforge.github.ratelimit.remaining_pct stays above 30 after the reset, the monitor returns to OK and the queue depth is falling.
- Item 4
  - **Escalation:** Escalate to the Platform Engineering Lead if throttling lasts longer than 2 hours or proposals are failing for customers.
  - **Frequency:** On demand
  - **Name:** SOP: Handle LLM API throttling
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
  - **Purpose:** Keep README proposals flowing when the Anthropic API throttles requests, by backing off and routing proposals to the fallback model.
  - **Roles:**
    - Application support engineer (L2)
    - Platform engineer
  - **Steps:**
    - Open the dashboard 'ReadmeForge - External dependencies' and read the LLM throttled-request ratio and failure rate.
    - In Datadog APM open Service readme-builder-worker, filter resource anthropic.messages and confirm the 429 status and the retry-after values.
    - Reduce parallel proposal builds: az containerapp update --name readme-builder-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars BUILD_MAX_CONCURRENCY=3
    - Enable the fallback model route by setting LLM_FALLBACK_ENABLED=true on readme-builder-worker with the same az containerapp update command.
    - Check the provider status page and the usage tier; if normal traffic growth causes the limit, request a higher rate limit from the provider.
    - When the throttled ratio is below 2% for 30 minutes, set BUILD_MAX_CONCURRENCY=8 and LLM_FALLBACK_ENABLED=false again.
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] LLM API throttling rate high' is in Alert (P2, Slack), or readme-builder-worker logs show HTTP 429 responses from the Anthropic API.
  - **Verification:** The throttled ratio is below 5%, the README proposal success rate on the dashboard is above 95% and the monitor is OK.
- Item 5
  - **Escalation:** Escalate to the database engineer on-call after 20 minutes without improvement; inform the Platform Engineering Lead before any fail-over.
  - **Frequency:** On demand
  - **Name:** SOP: Respond to PostgreSQL CPU saturation
  - **Prerequisites:**
    - Datadog access with Monitors Read and Dashboards Read permissions (team readmeforge)
    - Member of the PagerDuty service 'ReadmeForge Production' or its escalation policy
    - Azure CLI signed in to the production subscription with az login
    - Database Monitoring enabled for the server and psql access through the jump host
  - **Purpose:** Restore headroom on the production PostgreSQL Flexible Server when CPU stays above 85%, preventing slow queries and connection failures across the API and workers.
  - **Roles:**
    - L3 engineering on-call
    - Database engineer
  - **Steps:**
    - Acknowledge the page and open the dashboard 'ReadmeForge - PostgreSQL and Redis health'; note CPU, active connections and which server (central-india or south-india) alerts.
    - Open Datadog Database Monitoring for the server and sort Query Metrics by total time to find the heaviest statements; note the top three.
    - Check for long-running or blocked sessions: SELECT pid, now() - query_start AS runtime, state, left(query, 120) FROM pg_stat_activity WHERE state <> 'idle' ORDER BY runtime DESC LIMIT 10;
    - If a runaway query from a worker is the cause, cancel it with SELECT pg_cancel_backend(<pid>); and record the statement for the Scanner team.
    - If the load is genuine traffic growth, scale the server up one compute tier: az postgres flexible-server update --name psql-readmeforge-prod-central --resource-group rg-readmeforge-prod-central-india --sku-name Standard_D8ds_v5 --tier GeneralPurpose
    - Reduce pressure while scaling by pausing non-urgent scans: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars SCAN_MAX_CONCURRENCY=2
    - If the server does not recover or fails, follow the database fail-over procedure to South India in the backup and recovery chapter of the SMTD.
  - **Trigger:** Datadog monitor '[ReadmeForge][prod] PostgreSQL CPU high' is in Alert (P1, paged).
  - **Verification:** CPU is below 70% for 30 minutes, active connections are below 80% of the maximum and the API p95 latency stays normal.
