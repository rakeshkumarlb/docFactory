---
type: "Slo"
title: "Shared.Slo"
generated: { by: "seed", at: 2026-10-03T12:30:22Z }
status: draft
fact_key: "Shared.Slo"
version: 1
completeness: 100
---

# Shared.Slo

## Objectives

- Item 1
  - **Name:** Production service availability
  - **Definition:** Share of successful requests (non-5xx responses to valid requests) out of all valid requests served by the production service through its public entry point, excluding announced maintenance windows.
  - **Target:** 99.9%
  - **Measurement window:** Calendar month
  - **Measurement source:** Azure Monitor availability metric and Application Insights request telemetry, reported on the platform reliability dashboard
  - **Breach consequence:** Post-incident review within 5 business days and a reliability action plan reviewed by the service owner; repeated breaches in consecutive months pause non-critical feature releases.
- Item 2
  - **Name:** API latency (p95)
  - **Definition:** 95th percentile server-side response time of interactive API requests, measured at the ingress, excluding long-running asynchronous jobs.
  - **Target:** Under 800 ms
  - **Measurement window:** Rolling 7 days
  - **Measurement source:** Application Insights request duration percentiles, Grafana latency dashboard
  - **Breach consequence:** Performance investigation opened as a high-priority backlog item; the owning team reports findings at the next weekly operations review.
- Item 3
  - **Name:** P1 incident response time
  - **Definition:** Time from the first automated alert or customer report of a priority 1 incident to acknowledgement by an on-call engineer who starts working on it.
  - **Target:** Within 30 minutes, 24x7
  - **Measurement window:** Per incident, reported quarterly
  - **Measurement source:** Paging tool acknowledgement timestamps compared with the incident record creation time
  - **Breach consequence:** Escalation to the engineering manager on duty and a review of the on-call rota and alert routing in the post-incident review.
- Item 4
  - **Name:** P1 incident restoration time
  - **Definition:** Time from the start of a priority 1 incident to restoration of normal service for affected users, whether by fix, rollback or failover.
  - **Target:** Within 4 hours
  - **Measurement window:** Per incident, reported quarterly
  - **Measurement source:** Incident record timeline (detected, mitigated, resolved timestamps)
  - **Breach consequence:** Mandatory post-incident review with a written root cause analysis shared with the management team within 5 business days.
- Item 5
  - **Name:** P2 incident restoration time
  - **Definition:** Time from detection of a priority 2 incident (major degradation with a workaround available) to restoration of normal service.
  - **Target:** Within 1 business day
  - **Measurement window:** Per incident, reported quarterly
  - **Measurement source:** Incident record timeline in the service management tool
  - **Breach consequence:** Incident reviewed at the next weekly operations review and a corrective action assigned to the owning team.

## Notes

These objectives apply to every production application on the platform unless a service owner agrees a stricter target. Free or community tiers of a product carry no contractual commitment. The targets are reviewed once a year by the service owners and the platform management team.
