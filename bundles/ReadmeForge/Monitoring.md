---
type: "Monitoring"
title: "ReadmeForge.Monitoring"
generated: { by: "seed", at: 2026-10-03T12:30:22Z }
status: draft
fact_key: "ReadmeForge.Monitoring"
version: 1
completeness: 100
---

# ReadmeForge.Monitoring

## Monitoring tools

- Datadog Metrics and Monitors (metric, APM and log monitors, composite monitors)
- Datadog APM (distributed tracing for the six ReadmeForge components)
- Datadog Synthetic Monitoring (HTTP API tests from Indian and global locations)
- Datadog Azure integration (Container Apps, Service Bus, PostgreSQL Flexible Server, Redis)
- Datadog Log Management
- Datadog Agent on Azure Container Apps (sidecar container, DogStatsD for custom metrics)
- PagerDuty

## Key metrics

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

## Alerts

- Item 1
  - **Name:** [ReadmeForge][prod] API 5xx error rate high
  - **Condition:** Datadog APM metric monitor: sum:trace.http.request.errors{service:readmeforge-api,env:production}.as_count() / sum:trace.http.request.hits{service:readmeforge-api,env:production}.as_count() above 0.02 (2%) over the last 5 minutes; warning at 1%; multi-alert by location; no-data notification after 10 minutes.
  - **Severity:** P1 - Critical
  - **Response action:** Follow the runbook 'SOP: Respond to API 5xx error spike in production' (linked in the monitor message).
  - **Notification channel:** PagerDuty service 'ReadmeForge Production' (Datadog handle @pagerduty-ReadmeForge-Production) and Slack #readmeforge-alerts (@slack-readmeforge-alerts)
- Item 2
  - **Name:** [ReadmeForge][prod] Scan-jobs oldest message age high
  - **Condition:** Datadog metric monitor on the custom metric avg:readmeforge.scanjobs.oldest_message_age_seconds{env:production} (reported by repo-scanner-worker every 30 seconds): above 900 seconds (15 minutes) for 10 minutes; warning at 600 seconds.
  - **Severity:** P1 - Critical
  - **Response action:** Follow the runbook 'SOP: Recover a backed-up scan queue' (linked in the monitor message).
  - **Notification channel:** PagerDuty service 'ReadmeForge Production' (Datadog handle @pagerduty-ReadmeForge-Production) and Slack #readmeforge-alerts (@slack-readmeforge-alerts)
- Item 3
  - **Name:** [ReadmeForge][prod] Scan-jobs queue depth high
  - **Condition:** Datadog metric monitor: avg:azure.servicebus_namespaces.active_messages{name:sb-readmeforge-prod,entity_name:scan-jobs} above 500 for 15 minutes; warning at 300.
  - **Severity:** P2 - Warning
  - **Response action:** Check the 'ReadmeForge - Scan pipeline' dashboard; if the oldest-message-age monitor is also close to its threshold, follow 'SOP: Recover a backed-up scan queue'.
  - **Notification channel:** Slack #readmeforge-alerts (@slack-readmeforge-alerts)
- Item 4
  - **Name:** [ReadmeForge][prod] Scan-jobs dead-letter queue not empty
  - **Condition:** Datadog metric monitor: max:azure.servicebus_namespaces.dead_lettered_messages{name:sb-readmeforge-prod,entity_name:scan-jobs} above 0 for 5 minutes.
  - **Severity:** P3 - Info
  - **Response action:** Inspect the dead-lettered messages during working hours and replay them once the cause is fixed; the Scan pipeline dashboard shows the dead-letter count.
  - **Notification channel:** Slack #readmeforge-alerts (@slack-readmeforge-alerts)
- Item 5
  - **Name:** [ReadmeForge][prod] GitHub API rate limit remaining low
  - **Condition:** Datadog metric monitor on the custom metric min:readmeforge.github.ratelimit.remaining_pct{env:production} (reported by repo-scanner-worker): below 15 (percent of the hourly budget) for 5 minutes; warning at 30.
  - **Severity:** P2 - Warning
  - **Response action:** Follow the runbook 'SOP: Handle GitHub API rate limit exhaustion' (linked in the monitor message).
  - **Notification channel:** Slack #readmeforge-alerts (@slack-readmeforge-alerts)
- Item 6
  - **Name:** [ReadmeForge][prod] LLM API throttling rate high
  - **Condition:** Datadog metric monitor (formula): sum:readmeforge.llm.requests.throttled{env:production}.as_count() / sum:readmeforge.llm.requests.total{env:production}.as_count() above 0.10 (10%) over 10 minutes; warning at 5%.
  - **Severity:** P2 - Warning
  - **Response action:** Follow the runbook 'SOP: Handle LLM API throttling' (linked in the monitor message).
  - **Notification channel:** Slack #readmeforge-alerts (@slack-readmeforge-alerts)
- Item 7
  - **Name:** [ReadmeForge][prod] PostgreSQL CPU high
  - **Condition:** Datadog metric monitor from the Azure integration: avg:azure.dbforpostgresql_flexibleservers.cpu_percent{name:psql-readmeforge-prod*} above 85 for 15 minutes; warning at 70; multi-alert by server.
  - **Severity:** P1 - Critical
  - **Response action:** Follow the runbook 'SOP: Respond to PostgreSQL CPU saturation' (linked in the monitor message).
  - **Notification channel:** PagerDuty service 'ReadmeForge Production' (Datadog handle @pagerduty-ReadmeForge-Production) and Slack #readmeforge-alerts (@slack-readmeforge-alerts)
- Item 8
  - **Name:** [ReadmeForge][prod] Synthetic API availability failing
  - **Condition:** Datadog Synthetic API test GET /health on each production location (Pune, Chennai, Mumbai, Jamnagar endpoints), run every 1 minute from 3 locations; alerts when 2 of 3 locations fail for 3 consecutive runs.
  - **Severity:** P1 - Critical
  - **Response action:** Check the 'ReadmeForge - API overview' dashboard and follow 'SOP: Respond to API 5xx error spike in production'; for a single failing location check the Container Apps revision health first.
  - **Notification channel:** PagerDuty service 'ReadmeForge Production' (Datadog handle @pagerduty-ReadmeForge-Production) and Slack #readmeforge-alerts (@slack-readmeforge-alerts)

## Dashboards

- Datadog dashboard - ReadmeForge - API overview (availability per location, latency, 5xx rate, requests per second)
- Datadog dashboard - ReadmeForge - Scan pipeline (queue depth, oldest-message age, dead-letter count, scan duration)
- Datadog dashboard - ReadmeForge - External dependencies (GitHub rate-limit headroom, LLM throttling and failure rate)
- Datadog dashboard - ReadmeForge - PostgreSQL and Redis health (CPU, connections, failover state)
- Datadog Service Catalog entry readmeforge (owners, on-call, runbook links, monitors per service)

## Log locations

- Datadog Log Management, index readmeforge-prod (query service:readmeforge-* env:production, retention 15 days, archived to Azure Blob Storage for 90 days)
- Azure Log Analytics workspace law-readmeforge-prod, table ContainerAppConsoleLogs_CL (raw container output, retention 90 days)
