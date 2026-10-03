# ReadmeForge Software Requirements Specification

- **Document ID:** ReadmeForge-SRS-001
- **Version:** 1.0
- **Status:** Draft
- **Owner:** ReadmeForge Product Owner
- **Approvers:** Head of Developer Experience, ReadmeForge Platform Engineering Lead
- **Created:** 2026-10-03
- **Last Updated:** 2026-10-03

## Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-10-03 | docFactory seed | Initial SRS generated from the seeded ReadmeForge facts. |

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


## Functional Requirements

**Summary:** ReadmeForge keeps a repository README current by scanning the repository after each push and proposing README updates that a maintainer reviews and accepts or rejects.

**Requirements:**

| ID | Title | Description | Priority | Rationale | Acceptance Criteria |
|---|---|---|---|---|---|
| FR-001 | Scan a repository on push | The system shall start a scan of a connected repository whenever a commit is pushed to its default branch. | MUST | Maintainers should not have to trigger README updates by hand. | A scan starts within 60 seconds of a push to the default branch, The scan result is visible in the dashboard |
| FR-002 | Propose README changes | The system shall generate a proposed README update from the scan result and present it to the maintainer as a diff. | MUST | A reviewable diff keeps the maintainer in control of what is published. | A proposal is shown as a diff against the current README, The maintainer can accept or reject each proposal |
| FR-003 | Exclude paths from scanning | The system shall let a maintainer exclude directories from scanning using a .readmeforge-ignore file in the repository root. | SHOULD | _N/A — The need is self-evident from FR-001 and no separate rationale has been recorded._ | Paths listed in .readmeforge-ignore are not read during a scan |

**Out Of Scope:**
- Editing any file other than the README
- Generating documentation for repositories that are not connected through GitHub


## Non Functional Requirements

**Summary:** The dashboard must feel responsive, the service must be available during working hours and access to repositories must be limited to what the user has authorised.

**Requirements:**

| ID | Category | Statement | Target | Priority | Verification |
|---|---|---|---|---|---|
| NFR-001 | PERFORMANCE | The dashboard shall load its main page quickly for typical users. | 95th percentile page load under 2 seconds | SHOULD | Monthly load test against the staging environment |
| NFR-002 | AVAILABILITY | The dashboard and webhook receiver shall be available during working hours. | 99.5% monthly availability | MUST | Availability reported from the monitoring dashboard each month |
| NFR-003 | SECURITY | The system shall only read repositories that the signing-in user has authorised through GitHub OAuth. | _N/A — Access control is a yes-or-no property and has no numeric target._ | MUST | Covered by the automated authorisation test suite on every release |


## Service Levels

**Objectives:**

| Name | Definition | Target | Measurement Window | Measurement Source | Breach Consequence |
|---|---|---|---|---|---|
| Production service availability | Share of successful requests (non-5xx responses to valid requests) out of all valid requests served by the production service through its public entry point, excluding announced maintenance windows. | 99.9% | Calendar month | Azure Monitor availability metric and Application Insights request telemetry, reported on the platform reliability dashboard | Post-incident review within 5 business days and a reliability action plan reviewed by the service owner; repeated breaches in consecutive months pause non-critical feature releases. |
| API latency (p95) | 95th percentile server-side response time of interactive API requests, measured at the ingress, excluding long-running asynchronous jobs. | Under 800 ms | Rolling 7 days | Application Insights request duration percentiles, Grafana latency dashboard | Performance investigation opened as a high-priority backlog item; the owning team reports findings at the next weekly operations review. |
| P1 incident response time | Time from the first automated alert or customer report of a priority 1 incident to acknowledgement by an on-call engineer who starts working on it. | Within 30 minutes, 24x7 | Per incident, reported quarterly | Paging tool acknowledgement timestamps compared with the incident record creation time | Escalation to the engineering manager on duty and a review of the on-call rota and alert routing in the post-incident review. |
| P1 incident restoration time | Time from the start of a priority 1 incident to restoration of normal service for affected users, whether by fix, rollback or failover. | Within 4 hours | Per incident, reported quarterly | Incident record timeline (detected, mitigated, resolved timestamps) | Mandatory post-incident review with a written root cause analysis shared with the management team within 5 business days. |
| P2 incident restoration time | Time from detection of a priority 2 incident (major degradation with a workaround available) to restoration of normal service. | Within 1 business day | Per incident, reported quarterly | Incident record timeline in the service management tool | Incident reviewed at the next weekly operations review and a corrective action assigned to the owning team. |

**Notes:** These objectives apply to every production application on the platform unless a service owner agrees a stricter target. Free or community tiers of a product carry no contractual commitment. The targets are reviewed once a year by the service owners and the platform management team.
