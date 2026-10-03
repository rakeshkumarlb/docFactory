---
type: "Support"
title: "ReadmeForge.Support"
generated: { by: "seed", at: 2026-10-03T12:30:22Z }
status: draft
fact_key: "ReadmeForge.Support"
version: 1
completeness: 100
---

# ReadmeForge.Support

## Support model

Three-level support for Pro customers: L1 Zendesk support desk, L2 application support engineers on the Platform team during business hours, and L3 engineering on-call 24x7 via PagerDuty for P1 incidents. Free-tier users are supported by the community forum and email on a best-effort basis with no SLA.

## Contacts

- Item 1
  - **Role:** L1 customer support (Pro)
  - **Team:** ReadmeForge Support Desk
  - **Contact channel:** Zendesk help centre at https://support.readmeforge.example or support@readmeforge.example
  - **Support hours:** Mon-Fri 09:00-18:00 IST; first response within 1 business day
  - **Escalates to:** L2 application support
- Item 2
  - **Role:** L2 application support
  - **Team:** Platform team application support engineers
  - **Contact channel:** Slack #readmeforge-support-l2 and Zendesk internal escalation queue
  - **Support hours:** Mon-Fri 09:00-18:00 IST
  - **Escalates to:** L3 engineering on-call
- Item 3
  - **Role:** L3 engineering on-call
  - **Team:** Engineering on-call rotation (Platform and Scanner teams)
  - **Contact channel:** PagerDuty service 'ReadmeForge Production'; P1 incidents reported 24x7 by email to p1@readmeforge.example
  - **Support hours:** 24x7
  - **Escalates to:** Engineering manager on duty
- Item 4
  - **Role:** Free-tier community support
  - **Team:** Community volunteers and ReadmeForge developer relations
  - **Contact channel:** Community forum at https://community.readmeforge.example or community@readmeforge.example
  - **Support hours:** Best effort, no SLA
  - **Escalates to:** None; Free-tier users may upgrade to Pro for supported access

## Escalation path

L1 Zendesk support desk, then L2 application support engineers, then L3 engineering on-call. P1 incidents reported 24x7 by email skip L1 and go directly to L3 via PagerDuty.

## Incident process

Incidents are logged as Zendesk tickets (or raised by PagerDuty from Azure Monitor alerts), classified P1-P4 within 30 minutes, and worked by the responsible level. P1 incidents open a Slack incident channel, get status updates to affected customers every hour, and are closed after a post-incident review is written within 5 business days.

## Runbooks

- docs/runbooks/handle-github-api-rate-limiting.md
- docs/runbooks/handle-llm-api-throttling.md
- docs/runbooks/recover-from-slow-or-backed-up-scan-queue.md
- docs/runbooks/respond-to-api-outage-or-high-latency.md
- docs/runbooks/drain-and-replay-scan-jobs-dead-letter-queue.md
- docs/runbooks/fail-over-database-to-south-india.md
- docs/runbooks/rotate-github-app-private-key.md
- docs/runbooks/raise-customer-from-free-to-pro-repository-limit.md
- docs/runbooks/add-a-new-production-location.md
