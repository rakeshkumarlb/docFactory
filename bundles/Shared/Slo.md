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

## Notes

These objectives apply to every production application on the platform unless a service owner agrees a stricter target. Free or community tiers of a product carry no contractual commitment. The targets are reviewed once a year by the service owners and the platform management team.

## Objectives

- Item 1
  - **Breach consequence:** Post-incident review within 5 business days and a reliability action plan reviewed by the service owner; repeated breaches in consecutive months pause non-critical feature releases.
  - **Definition:** Share of successful requests (non-5xx responses to valid requests) out of all valid requests served by the production service through its public entry point, excluding announced maintenance windows.
  - **Measurement source:** Azure Monitor availability metric and Application Insights request telemetry, reported on the platform reliability dashboard
  - **Measurement window:** Calendar month
  - **Name:** Production service availability
  - **Target:** 99.9%
- Item 2
  - **Breach consequence:** Performance investigation opened as a high-priority backlog item; the owning team reports findings at the next weekly operations review.
  - **Definition:** 95th percentile server-side response time of interactive API requests, measured at the ingress, excluding long-running asynchronous jobs.
  - **Measurement source:** Application Insights request duration percentiles, Grafana latency dashboard
  - **Measurement window:** Rolling 7 days
  - **Name:** API latency (p95)
  - **Target:** Under 800 ms
- Item 3
  - **Breach consequence:** Escalation to the engineering manager on duty and a review of the on-call rota and alert routing in the post-incident review.
  - **Definition:** Time from the first automated alert or customer report of a priority 1 incident to acknowledgement by an on-call engineer who starts working on it.
  - **Measurement source:** Paging tool acknowledgement timestamps compared with the incident record creation time
  - **Measurement window:** Per incident, reported quarterly
  - **Name:** P1 incident response time
  - **Target:** Within 30 minutes, 24x7
- Item 4
  - **Breach consequence:** Mandatory post-incident review with a written root cause analysis shared with the management team within 5 business days.
  - **Definition:** Time from the start of a priority 1 incident to restoration of normal service for affected users, whether by fix, rollback or failover.
  - **Measurement source:** Incident record timeline (detected, mitigated, resolved timestamps)
  - **Measurement window:** Per incident, reported quarterly
  - **Name:** P1 incident restoration time
  - **Target:** Within 4 hours
- Item 5
  - **Breach consequence:** Incident reviewed at the next weekly operations review and a corrective action assigned to the owning team.
  - **Definition:** Time from detection of a priority 2 incident (major degradation with a workaround available) to restoration of normal service.
  - **Measurement source:** Incident record timeline in the service management tool
  - **Measurement window:** Per incident, reported quarterly
  - **Name:** P2 incident restoration time
  - **Target:** Within 1 business day
