# ReadmeForge System Maintenance and Technical Document

- **Document ID:** ReadmeForge-SMTD-001
- **Version:** 1.0
- **Status:** Draft
- **Owner:** ReadmeForge Platform Engineering Lead
- **Approvers:** Head of Developer Experience, ReadmeForge Platform Engineering Lead
- **Created:** 2026-09-28
- **Last Updated:** 2026-09-28

## Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-09-28 | docFactory seed | Initial SMTD generated from the seeded ReadmeForge facts (Azure Container Apps, four India locations). |

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


## Architecture

**Architecture Style:** Event-driven microservices on Azure Container Apps: a React dashboard and a FastAPI REST API in front, with webhook-triggered scan and README-build workers decoupled through Azure Service Bus queues.

**Technology Stack:**
- React single-page application
- Python 3.12
- FastAPI
- tree-sitter
- Azure Container Apps
- Azure Front Door with WAF
- Azure Database for PostgreSQL Flexible Server
- Azure Cache for Redis
- Azure Service Bus (Standard)
- Azure Blob Storage (RA-GRS)
- Azure Key Vault
- Azure Monitor, Application Insights and Log Analytics
- Bicep
- GitHub Actions

**Components:**

| Name | Purpose | Technology | Owner | Dependencies |
|---|---|---|---|---|
| web-app | React single-page dashboard where maintainers link repositories, review and accept, edit or reject README diff proposals, and manage their plan. | React single-page application served from Azure Container Apps | Frontend team | api |
| api | REST API for authentication, repository linking, README proposals and tier-limit checks. Single backend entry point for the dashboard. | Python 3.12 / FastAPI | Platform team | Azure Database for PostgreSQL, Azure Cache for Redis, Azure Service Bus, billing-service, GitHub OAuth, Azure Key Vault |
| webhook-receiver | Receives GitHub App push webhooks, validates their signatures and enqueues scan jobs on the scan-jobs queue. | Python 3.12 / FastAPI | Platform team | Azure Service Bus, Azure Cache for Redis, Azure Key Vault, GitHub |
| repo-scanner-worker | Takes read-only shallow clones of linked repositories, parses them with tree-sitter and extracts structured facts (entry points, dependencies, configuration, CI setup). Scales on Service Bus queue depth. | Python 3.12 / tree-sitter | Scanner team | Azure Service Bus, Azure Blob Storage, Azure Database for PostgreSQL, GitHub |
| readme-builder-worker | Assembles the README context from extracted facts, calls the LLM to draft prose and produces the README diff proposal for maintainer review. | Python 3.12 | Scanner team | Azure Service Bus, Azure Blob Storage, Azure Database for PostgreSQL, Anthropic API, Azure Key Vault |
| billing-service | Enforces tier limits (Free 1 linked repository, Pro up to 10) and synchronises subscription state with Stripe. | Python 3.12 / FastAPI | Platform team | Azure Database for PostgreSQL, Stripe, Azure Key Vault |

**Data Stores:**

| Name | Store Type | Technology | Contents |
|---|---|---|---|
| ReadmeForge PostgreSQL database | relational database | Azure Database for PostgreSQL Flexible Server, zone-redundant, primary write region Central India (Pune) | Accounts, linked repositories, scan result metadata, README proposals and subscription state. |
| Redis cache | in-memory cache | Azure Cache for Redis | User sessions, rate-limiting counters and scan job de-duplication keys. Holds no data that cannot be rebuilt. |
| Service Bus messaging | message queue and topic | Azure Service Bus (Standard) | The scan-jobs queue with its dead-letter queue, and the proposal-events topic. |
| Blob Storage | object storage | Azure Blob Storage with RA-GRS replication | Temporary repository snapshots (automatically deleted after 24 hours) and generated README artifacts. |
| Key Vault | secrets store | Azure Key Vault | GitHub App private key, Stripe keys and the LLM API key. |

**Integrations:**

| Name | Direction | Protocol | Purpose | Data Exchanged | Authentication |
|---|---|---|---|---|---|
| GitHub (GitHub App) | bidirectional | Webhooks (inbound) and REST over HTTPS (outbound) | Notifies ReadmeForge of repository pushes and lets it read repository contents for scanning. | Push event payloads inbound; read-only repository contents and metadata outbound. | GitHub App installation tokens (private key held in Key Vault); webhook payloads verified by HMAC signature |
| Anthropic API | outbound | REST over HTTPS | Drafts README prose from the structured facts extracted from a repository. | Extracted repository facts and prompt context outbound; drafted README text inbound. | API key stored in Key Vault |
| Stripe | bidirectional | REST over HTTPS (outbound) and webhooks (inbound) | Bills Pro subscriptions and keeps subscription state in sync. | Customer and subscription identifiers, plan and payment status; no card data is handled by ReadmeForge. | Stripe secret API key in Key Vault outbound; Stripe webhook signing secret inbound |
| Zendesk | outbound | REST over HTTPS | Creates and updates Pro customer support tickets. | Ticket subject, description, requester email and account plan. | Zendesk API token |
| PagerDuty | outbound | Events API over HTTPS | Pages the engineering on-call rotation when Azure Monitor alerts fire. | Alert name, severity, affected environment and a link to the alert. | PagerDuty integration (routing) key |
| GitHub OAuth | inbound | OAuth 2.0 authorization code flow over HTTPS | Lets users sign in to ReadmeForge with their GitHub identity. | Authorization code and access token exchange; GitHub user id, login and verified email. | OAuth client id and secret; client secret held in Key Vault |

**Diagram Reference:** docs/architecture/readmeforge-azure.md

**Notes:** All components run in Azure Container Apps, one Container Apps environment per location, with Azure Front Door routing traffic to the nearest healthy location. All data stays in India. The database has a single primary write region (Central India, Pune) with South India (Chennai) as the paired disaster-recovery region.


## Environments

**Environments:**

| Name | Purpose | Hosting | URL | Access Control | Notes |
|---|---|---|---|---|---|
| dev | Development and integration testing by engineers, including feature branches deployed as short-lived revisions. | Azure Container Apps environment in Central India (Pune); ingress public IP 198.51.100.60, VNet 10.60.0.0/16 | https://dev.readmeforge.example | Engineering staff via Entra ID SSO group readmeforge-dev with Contributor rights; not reachable by customers. | Uses a small PostgreSQL instance and a GitHub App registered against test repositories only; data may be wiped at any time. |
| staging | Pre-production verification of each release, including the weekly release candidate, smoke tests and canary checks before production rollout. | Azure Container Apps environment in Central India (Pune); ingress public IP 203.0.113.50, VNet 10.50.0.0/16 | https://staging.readmeforge.example | Engineering and QA via Entra ID SSO group readmeforge-staging; deployments only through the release pipeline. | First location in the rollout order; configuration mirrors production. Contains no customer data. |
| prod-central-india | Production location in Central India (Pune) serving customers and hosting the primary write database. | Azure Container Apps environment in Central India (Pune); ingress public IP 203.0.113.10, VNet 10.10.0.0/16 | https://prod-central-india.readmeforge.example | Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only. | Primary write region for PostgreSQL. Second in the rollout order. |
| prod-south-india | Production location in South India (Chennai) serving customers and acting as the disaster-recovery region. | Azure Container Apps environment in South India (Chennai); ingress public IP 203.0.113.20, VNet 10.20.0.0/16 | https://prod-south-india.readmeforge.example | Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only. | Paired disaster-recovery and geo-backup region; promoted to primary write region during a regional failure of Central India. Third in the rollout order. |
| prod-west-india | Production location in West India (Mumbai) serving customers. | Azure Container Apps environment in West India (Mumbai); ingress public IP 198.51.100.30, VNet 10.30.0.0/16 | https://prod-west-india.readmeforge.example | Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only. | Fourth in the rollout order. |
| prod-jio-west | Production location in Jio India West (Jamnagar) serving customers. | Azure Container Apps environment in Jio India West (Jamnagar); ingress public IP 198.51.100.40, VNet 10.40.0.0/16 | https://prod-jio-west.readmeforge.example | Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only. | Last in the rollout order. |

**Notes:** All environments run on Azure in India only, keeping data resident in India. Global traffic enters through Azure Front Door (https://app.readmeforge.example, API at https://api.readmeforge.example) with WAF enabled, which routes to the nearest healthy production location. Dev and staging are both in Central India.


## Deployment

**Release Process:** GitHub Actions builds and tests the container images and pushes them to Azure Container Registry (readmeforgeacr.azurecr.io). The pipeline then deploys each image as a new Container Apps revision using blue/green traffic splitting: 10% canary traffic for 30 minutes, then 100% if health checks and alerts stay clean. Locations roll out one at a time in the order staging, prod-central-india, prod-south-india, prod-west-india, prod-jio-west.

**CI CD Tooling:** GitHub Actions for build, test and deployment; Bicep for infrastructure as code; Azure Container Registry for images; Azure Container Apps revisions for releases.

**Release Frequency:** Weekly on Tuesdays at 11:00 IST; hotfixes may be released on any day.

**Rollback Procedure:** Re-activate the previous Container Apps revision and shift 100% of traffic back to it, which takes under 5 minutes. Database migrations are backward-compatible (expand/contract), so the previous revision keeps working against the migrated schema.

**Configuration Management:** Container Apps secrets that reference Azure Key Vault hold all secrets. Environment-specific settings live in Bicep parameter files in the repository and are applied by the deployment pipeline.


## Monitoring

**Monitoring Tools:**
- Azure Monitor (metric alerts, log alerts, action groups)
- Application Insights (availability tests, custom metrics, smart detection)
- Log Analytics
- Azure Managed Grafana
- PagerDuty

**Key Metrics:**
- API availability (per location)
- API p95 latency
- API 5xx rate
- API request throughput (requests/s vs baseline)
- GitHub API rate-limit headroom (remaining % of hourly budget)
- LLM API 429/throttling rate
- LLM call failure rate
- Webhook processing lag (receipt to enqueue)
- Scan-jobs queue depth
- Scan-jobs oldest-message age
- Scan-jobs dead-letter count
- Scan throughput (repos scanned per minute)
- Scan duration p95
- README proposal success rate
- Free-tier repo-limit rejections (billing-service)
- PostgreSQL CPU
- PostgreSQL connections

**Alerts:**

| Name | Condition | Severity | Response Action | Notification Channel |
|---|---|---|---|---|
| App Insights - Availability test failing in a production location | Application Insights availability test (standard ping test on https://<env>.readmeforge.example/healthz, every 5 minutes from 5 Azure test locations) fails from 2 or more test locations for 2 consecutive runs, for any of prod-central-india, prod-south-india, prod-west-india or prod-jio-west. | Critical | Follow 'SOP: Respond to API outage or high latency': check Azure Front Door origin health and the api Container App revisions in the affected location and confirm traffic is routed to healthy locations. If the whole Central India location is lost, follow 'SOP: Fail over database to South India'. | PagerDuty on-call rotation (L3) and Slack #readmeforge-alerts |
| Azure Monitor metric alert - API 5xx rate high | Container Apps metric alert on the api app: 5xx responses above 2% of requests, evaluated every minute over a 5-minute window, per production location. | Critical | Follow 'SOP: Respond to API outage or high latency': inspect AppTraces in law-readmeforge-prod for the failing endpoint, check PostgreSQL and Redis health, and re-activate the previous revision if errors began after a release. | PagerDuty on-call rotation (L3) and Slack #readmeforge-alerts |
| App Insights - API p95 latency high | Application Insights metric alert on requests/duration for the api app: p95 above 800 ms for 10 minutes. | Warning | Follow 'SOP: Respond to API outage or high latency': check PostgreSQL CPU and connections, look for slow dependencies in the Application map, and scale out api replicas if CPU is saturated. | Slack #readmeforge-alerts |
| Azure Monitor metric alert (dynamic threshold) - API request throughput anomaly | Dynamic-threshold metric alert on api requests per second: traffic drops below 50% or spikes above 300% of the learned same-hour baseline for 15 minutes (medium sensitivity). | Warning | A drop usually means an ingress or Front Door problem: run 'SOP: Respond to API outage or high latency'. A spike is usually a webhook storm or abusive client: check WAF logs and rate-limit counters in Redis, and see 'SOP: Recover from slow or backed-up scan queue' if the scan queue is growing. | Slack #readmeforge-alerts |
| App Insights - GitHub API rate limit remaining low | Application Insights custom metric github.ratelimit.remaining_pct (reported by repo-scanner-worker from the X-RateLimit-Remaining header) below 15% of the hourly budget for 5 minutes. | Warning | Follow 'SOP: Handle GitHub API rate limiting': pause low-priority rescans, reduce repo-scanner-worker concurrency, and confirm the GitHub App installation token budget resets at the top of the hour. | Slack #readmeforge-alerts |
| App Insights - LLM API 429/throttling rate high | Application Insights dependency alert on outbound Anthropic API calls from readme-builder-worker: HTTP 429 responses above 10% of calls over 10 minutes, or any call failing with a timeout or 5xx more than 5% of the time. | Warning | Follow 'SOP: Handle LLM API throttling': reduce readme-builder-worker concurrency, verify the LLM API key and quota in Key Vault and the provider console, and confirm proposals are only delayed, not lost. | Slack #readmeforge-alerts |
| Azure Monitor metric alert - Scan-jobs queue depth high | Service Bus metric alert on the scan-jobs queue: ActiveMessages above 500 for 15 minutes. | Warning | Follow 'SOP: Recover from slow or backed-up scan queue': raise the maximum replica count of repo-scanner-worker and check for oversized repositories or a GitHub rate-limit pause. | Slack #readmeforge-alerts |
| Azure Monitor log alert (KQL) - Scan-jobs oldest message age high | KQL log alert over the custom metric scanjobs.oldest_message_age_seconds in AppMetrics (law-readmeforge-prod), evaluated every 5 minutes: maximum above 600 seconds (10 minutes) in the last 10 minutes. | Critical | Follow 'SOP: Recover from slow or backed-up scan queue'. If messages are stuck or repeatedly failing, run 'SOP: Drain and replay scan-jobs dead-letter queue' after fixing the cause. | PagerDuty on-call rotation (L3) and Slack #readmeforge-alerts |
| Azure Monitor metric alert - Scan-jobs dead-letter queue not empty | Service Bus metric alert on the scan-jobs queue: DeadletteredMessages greater than 0 for 5 minutes. | Warning | Follow 'SOP: Drain and replay scan-jobs dead-letter queue': inspect the dead-letter reason, fix the cause, then replay the messages. | Slack #readmeforge-alerts |
| Azure Monitor log alert (KQL) - Scan throughput dropping | KQL log alert over AppTraces (law-readmeforge-prod): repos scanned per minute below 50% of the trailing 7-day same-hour baseline for 15 minutes while scan-jobs ActiveMessages is above 50. | Warning | Follow 'SOP: Recover from slow or backed-up scan queue': check repo-scanner-worker replicas and restarts, node memory pressure and whether 'SOP: Handle GitHub API rate limiting' applies. | Slack #readmeforge-alerts |
| App Insights - Webhook processing lag high | Application Insights custom metric webhook.receipt_to_enqueue_seconds for webhook-receiver: p95 above 30 seconds for 10 minutes. | Warning | Check webhook-receiver replicas and the Service Bus namespace health; if the scan queue is also growing follow 'SOP: Recover from slow or backed-up scan queue'. GitHub redelivers failed webhooks, so watch for duplicate scans (KE-001). | Slack #readmeforge-alerts |
| Azure Monitor log alert (KQL) - Free-tier repo-limit rejections spike | KQL log alert over ContainerAppConsoleLogs_CL for billing-service: more than 100 TIER_LIMIT_EXCEEDED rejections for Free-tier accounts in 15 minutes. | Info | Check whether a repo-linking loop or client bug is generating retries; if the volume looks like genuine demand, tell the product team and support desk. If a customer has upgraded, follow the SOP for raising the repo limit after a Pro upgrade. | Slack #readmeforge-alerts |
| Azure Monitor metric alert - PostgreSQL CPU high | PostgreSQL Flexible Server metric alert: cpu_percent above 85% (average) for 15 minutes. | Critical | Identify heavy queries via Query Performance Insight, scale up the Flexible Server compute tier if needed, and follow 'SOP: Respond to API outage or high latency' if the API is degraded. Follow 'SOP: Fail over database to South India' only for a regional failure. | PagerDuty on-call rotation (L3) and Slack #readmeforge-alerts |
| Azure Monitor metric alert - PostgreSQL connections high | PostgreSQL Flexible Server metric alert: active_connections above 80% of max_connections (average) for 10 minutes. | Warning | Check for connection leaks in api and billing-service replicas, restart the offending Container App revision, and review connection pool sizes. | Slack #readmeforge-alerts |
| App Insights - README proposal success rate low | Application Insights custom metric readme.proposal.success_rate below 95% over 30 minutes. | Critical | Check readme-builder-worker logs and the LLM failure rate; if the cause is throttling follow 'SOP: Handle LLM API throttling', otherwise roll back the latest readme-builder-worker revision. | PagerDuty on-call rotation (L3) and Slack #readmeforge-alerts |

**Dashboards:**
- Grafana - ReadmeForge API overview (availability per location, latency, 5xx, requests/s vs baseline)
- Grafana - Scan pipeline (queue depth, oldest message age, dead-letter count, repos scanned per minute, scan duration p95)
- Grafana - External dependencies (GitHub API rate-limit headroom, LLM 429 rate and failure rate)
- Grafana - README proposals (success rate, proposal latency)
- Grafana - Billing and tier limits (Free-tier repo-limit rejections, Stripe webhook health)
- Grafana - PostgreSQL and Redis health (CPU, connections, failover state)
- Application Insights - Application map and availability test results

**Log Locations:**
- Log Analytics workspace law-readmeforge-prod, table ContainerAppConsoleLogs_CL (container stdout/stderr of all six components, retention 90 days)
- Log Analytics workspace law-readmeforge-prod, table AppTraces (application traces from Application Insights, retention 90 days)


## Backup Recovery

**Backup Schedule:** PostgreSQL: automated continuous backups (a full snapshot daily plus continuous WAL archiving). Blob Storage: continuous through RA-GRS replication with soft delete enabled.

**Backup Retention:** PostgreSQL: point-in-time restore window of 14 days. Blob Storage: soft delete retention of 7 days. Redis is a cache and is not backed up.

**Backup Location:** PostgreSQL: geo-redundant backup stored in South India (Chennai), the paired disaster-recovery region. Blob Storage: RA-GRS, with the secondary copy in South India.

**Restore Procedure:** PostgreSQL: use point-in-time restore to a new Flexible Server in Central India (or promote South India for a regional failure), then repoint the api and workers via Key Vault-backed connection secrets. Blob Storage: undelete soft-deleted blobs within 7 days, or read from the RA-GRS secondary. Redis is rebuilt empty on restart; users simply sign in again.

**RPO:** 15 minutes

**RTO:** 1 hour for regional failure

**Disaster Recovery Plan:** On loss of Central India (Pune), promote South India (Chennai) as the primary write region for PostgreSQL, let Azure Front Door route traffic to the remaining healthy locations, and follow the database fail-over SOP at docs/runbooks/fail-over-database-to-south-india.md.


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


## Known Errors

**Known Errors:**

| Title | Error ID | Symptoms | Cause | Workaround | Permanent Fix | Severity | Status | Related Ticket |
|---|---|---|---|---|---|---|---|---|
| Duplicate scans triggered by GitHub webhook redelivery | KE-001 | A single push shows two or three scan runs for the same commit in the dashboard, and the maintainer receives duplicate README proposals for the same change. | GitHub redelivers a webhook when the webhook-receiver does not answer within 10 seconds. During load the receiver enqueues the scan job before responding, so redelivered deliveries create additional scan-jobs messages for the same commit. | Reject the surplus proposals in the dashboard. Support can purge duplicate messages from the scan-jobs queue in Azure Service Bus Explorer if a backlog builds up. | Acknowledge the webhook immediately and de-duplicate on the X-GitHub-Delivery id and commit SHA in Azure Cache for Redis before enqueueing (planned for the webhook-receiver in release 2.14). | Medium | Workaround available | RF-1423 |
| Repositories larger than about 2 GB time out during scan | KE-002 | The scan for a large repository stays in Running and then fails after 30 minutes with the message 'Scan timed out'. No README proposal is created. | The repo-scanner-worker performs a shallow clone and parses with tree-sitter within the container's ephemeral storage and a fixed 30-minute job lock. Repositories above roughly 2 GB exceed the storage or time budget. | The maintainer can exclude large directories (for example vendored dependencies or assets) with a .readmeforge-ignore file in the repository root and retrigger the scan from the dashboard. | Introduce sparse checkout of only the files relevant to entry points, dependencies, config and CI, and move snapshots to Azure Blob Storage to lift the size limit. | Medium | Open | RF-1377 |
| Users are signed out when Azure Cache for Redis fails over | KE-003 | During a Redis failover users are suddenly returned to the sign-in page and must sign in again with GitHub OAuth. Unsaved edits to a README proposal in the browser may be lost. | Sessions are stored only in Azure Cache for Redis. A failover to the replica drops connections and, because replication is asynchronous, the most recent session writes are not present on the new primary. | Sign in again; the proposal itself is stored in PostgreSQL and is still available. Support informs affected users through the status page when a failover is announced. | Issue signed, short-lived session tokens that can be re-validated against PostgreSQL after a cache miss so that a Redis failover no longer ends the session. | Low | Workaround available | RF-1290 |
| CRLF-only changes produce noisy README diffs | KE-004 | A push that only converts line endings (CRLF to LF or the reverse) leads to a proposal in which large unchanged sections of README.md are shown as modified. | The readme-builder-worker compares the regenerated README.md text with the committed file byte by byte, and does not normalize line endings before computing the diff. | Reject the proposal in the dashboard. Repositories can add a .gitattributes file with 'README.md text eol=lf' so that line endings stay consistent. | _N/A — The behaviour is accepted as low impact and the .gitattributes workaround is sufficient; no permanent fix is planned at this time._ | Low | Accepted, no fix planned | _N/A — The issue is documented only in the support knowledge base and no engineering ticket has been raised for it._ |
| LLM rate limiting (HTTP 429) delays README proposals | KE-005 | README proposals stay in the Drafting state for tens of minutes, mostly on weekday mornings after the weekly release. The readme-builder-worker logs show repeated 429 responses from the Anthropic API. | The combined request rate of the readme-builder-worker replicas exceeds the requests-per-minute quota of the Anthropic API key held in Azure Key Vault, so calls are throttled and retried with exponential backoff. | No action is needed from the customer, the proposal completes once capacity is available. Operations can follow 'SOP: Handle LLM API throttling' to lower readme-builder-worker concurrency. | Request a higher quota from the LLM provider and add a global token-bucket limiter with a priority queue so that Pro customers are drafted first. | Medium | Open | RF-1451 |

**Notes:** The known errors are reviewed at every weekly release and at the monthly operations review. Errors are closed when the permanent fix has been deployed to all four production locations. Support engineers use the workarounds when answering Pro customer tickets in Zendesk.


## Standard Operating Procedures

**Procedures:**
1.
  - **Name:** SOP: Handle GitHub API rate limiting
  - **Purpose:** Keep the scan pipeline healthy when the GitHub App installation tokens are close to or over their hourly REST API budget, without losing scan jobs or getting the app blocked by GitHub.
  - **Trigger:** The alert 'App Insights - GitHub API rate limit remaining low' fires (github.ratelimit.remaining_pct below 15% for 5 minutes), or repo-scanner-worker logs show HTTP 403/429 responses with X-RateLimit-Remaining 0.
  - **Frequency:** On demand
  - **Roles:**
    - Application support engineer (L2)
    - Platform engineer
    - Scanner team engineer (L3 on-call)
  - **Prerequisites:**
    - Reader access to Application Insights and Log Analytics workspace law-readmeforge-prod
    - Contributor role on the production Container Apps resource groups
    - Azure CLI signed in to the production subscription with az login
  - **Steps:**
    1. Open the Grafana dashboard 'External dependencies' and confirm the GitHub rate-limit headroom is low in one or several locations and note the time the budget resets (top of the hour).
    2. In Log Analytics run this KQL to find the heaviest consumers: ContainerAppConsoleLogs_CL | where ContainerAppName_s == 'repo-scanner-worker' and Log_s has 'X-RateLimit-Remaining' | summarize calls=count() by installation=extract('installation=([0-9]+)', 1, Log_s) | top 10 by calls desc
    3. If one installation dominates, check whether it is a large monorepo or a webhook storm from the customer and note the installation id in the incident record.
    4. Reduce the load on the GitHub API by lowering scanner concurrency: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars SCAN_MAX_CONCURRENCY=2 GITHUB_LOW_PRIORITY_PAUSED=true
    5. Repeat the update in the other production locations that show low headroom, one location at a time.
    6. Watch the Scan-jobs queue depth and oldest-message age in the Grafana 'Scan pipeline' dashboard; messages wait in the queue and are not lost while low-priority rescans are paused.
    7. After the budget resets, restore the settings: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --set-env-vars SCAN_MAX_CONCURRENCY=8 GITHUB_LOW_PRIORITY_PAUSED=false
    8. If the queue is backed up afterwards, continue with 'SOP: Recover from slow or backed-up scan queue'.
  - **Verification:** github.ratelimit.remaining_pct is back above 40%, no 403/429 responses from GitHub appear in repo-scanner-worker logs for 15 minutes, and the alert has auto-resolved.
  - **Escalation:** If the budget is exhausted repeatedly within a day or GitHub returns abuse-detection (secondary rate limit) errors, escalate from L2 to the L3 engineering on-call through PagerDuty and open a request with GitHub support.
2.
  - **Name:** SOP: Handle LLM API throttling
  - **Purpose:** Limit the impact of Anthropic API throttling or failures so that README proposals are delayed rather than lost or failed.
  - **Trigger:** The alert 'App Insights - LLM API 429/throttling rate high' fires (429 responses above 10% of calls over 10 minutes, or timeouts and 5xx above 5%), or the alert 'App Insights - README proposal success rate low' fires and the cause is throttling.
  - **Frequency:** On demand
  - **Roles:**
    - Application support engineer (L2)
    - Scanner team engineer (L3 on-call)
  - **Prerequisites:**
    - Reader access to Application Insights and Log Analytics workspace law-readmeforge-prod
    - Contributor role on the production Container Apps resource groups
    - Access to the LLM provider console for quota and status information
  - **Steps:**
    1. Open Application Insights > Investigate > Application map and select the dependency 'api.anthropic.com' to see the failure rate, the response codes and the slowest calls.
    2. Run this KQL in law-readmeforge-prod to see the 429 rate per 5 minutes: AppDependencies | where Target has 'anthropic' | summarize total=count(), throttled=countif(ResultCode == '429') by bin(TimeGenerated, 5m) | extend pct = 100.0 * throttled / total
    3. Check the LLM provider status page and the console for quota usage and any incident, and note the outcome in the incident record.
    4. If the quota is exhausted, reduce request pressure by lowering concurrency: az containerapp update --name readme-builder-worker --resource-group rg-readmeforge-prod-central-india --max-replicas 4 --set-env-vars LLM_MAX_CONCURRENCY=2
    5. Repeat the update in the other production locations so that the combined rate stays below the provider quota.
    6. Confirm in the dashboard 'README proposals' that proposals are in the Drafting state and are being retried with backoff rather than failing; the retry keeps them for up to 6 hours.
    7. If the API key itself is rejected (401), check the secret llm-api-key in Azure Key Vault and follow the provider process to replace it, then restart the readme-builder-worker revisions.
    8. When the 429 rate has stayed below 2% for 30 minutes, restore the normal settings: az containerapp update --name readme-builder-worker --resource-group rg-readmeforge-prod-central-india --max-replicas 12 --set-env-vars LLM_MAX_CONCURRENCY=8
  - **Verification:** The 429 rate is below 2%, the README proposal success rate is back above 95%, delayed proposals have been completed and the alert has auto-resolved.
  - **Escalation:** If throttling lasts more than 2 hours or proposals start to fail permanently, escalate from L2 to the L3 engineering on-call through PagerDuty and ask the product owner to inform Pro customers through the status page.
3.
  - **Name:** SOP: Recover from slow or backed-up scan queue
  - **Purpose:** Bring the scan-jobs Service Bus queue back to a normal depth and message age when scans are slow or stuck, so that README proposals are produced within their normal time.
  - **Trigger:** The alert 'Azure Monitor metric alert - Scan-jobs queue depth high' (ActiveMessages above 500 for 15 minutes), 'Azure Monitor log alert (KQL) - Scan-jobs oldest message age high' (older than 10 minutes) or 'Azure Monitor log alert (KQL) - Scan throughput dropping' fires.
  - **Frequency:** On demand, typically after a webhook burst, a GitHub rate-limit pause or a release
  - **Roles:**
    - Application support engineer (L2)
    - Platform engineer
    - Scanner team engineer (L3 on-call)
  - **Prerequisites:**
    - Azure Service Bus Data Receiver role on the production Service Bus namespace
    - Contributor role on the production Container Apps resource groups
    - Confirmation on the Grafana 'PostgreSQL and Redis health' dashboard that PostgreSQL CPU is below 70 percent before adding workers
  - **Steps:**
    1. Open the Grafana 'Scan pipeline' dashboard and read queue depth, oldest-message age, repos scanned per minute and scan duration p95 for the affected location.
    2. Check the queue in the Azure portal (Service Bus namespace > Queues > scan-jobs) or with: az servicebus queue show --resource-group rg-readmeforge-prod-central-india --namespace-name sb-readmeforge-prod --name scan-jobs --query "{active:countDetails.activeMessageCount, dead:countDetails.deadLetterMessageCount, oldest:accessedAt}"
    3. Check the oldest message age in Service Bus Explorer by peeking at the first messages, and in Log Analytics run: AppMetrics | where Name == 'scanjobs.oldest_message_age_seconds' | summarize max(Val) by bin(TimeGenerated, 5m) | render timechart
    4. Look at repo-scanner-worker health: az containerapp replica list --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --output table, and look for restarts or OOM kills in ContainerAppConsoleLogs_CL.
    5. If workers are healthy but saturated, raise the replicas: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --min-replicas 5 --max-replicas 40
    6. If a few very large repositories occupy the workers (scan duration above 20 minutes), note them for KE-002 and lower the priority of their jobs; if GitHub rate limiting is the cause, continue with 'SOP: Handle GitHub API rate limiting'.
    7. If messages fail repeatedly and move to the dead-letter queue, continue with 'SOP: Drain and replay scan-jobs dead-letter queue'.
    8. Watch queue depth and oldest-message age every 10 minutes; when the queue depth is below 100 restore the standard scale limits: az containerapp update --name repo-scanner-worker --resource-group rg-readmeforge-prod-central-india --min-replicas 2 --max-replicas 20
  - **Verification:** Queue depth is below 100, oldest-message age is below 2 minutes, scan throughput is back to the 7-day baseline, scale limits are back to their standard values and the alerts have auto-resolved.
  - **Escalation:** If the oldest-message age stays above 30 minutes after scaling, or PostgreSQL alerts fire while scaling, escalate from L2 to the L3 engineering on-call through PagerDuty.
4.
  - **Name:** SOP: Respond to API outage or high latency
  - **Purpose:** Restore availability and normal response times of the ReadmeForge API when a production location fails health checks, returns errors or becomes slow, and protect users by routing traffic to healthy locations.
  - **Trigger:** The alert 'App Insights - Availability test failing in a production location', 'Azure Monitor metric alert - API 5xx rate high', 'App Insights - API p95 latency high' or 'Azure Monitor metric alert (dynamic threshold) - API request throughput anomaly' fires.
  - **Frequency:** On demand
  - **Roles:**
    - Application support engineer (L2)
    - Platform engineer
    - L3 engineering on-call
    - Incident commander
  - **Prerequisites:**
    - Reader access to Application Insights and Log Analytics workspace law-readmeforge-prod
    - Contributor role on the production Container Apps resource groups and on the Azure Front Door profile
    - Azure CLI signed in to the production subscription with az login
  - **Steps:**
    1. Acknowledge the PagerDuty page, open an incident in the #readmeforge-alerts Slack channel and note which production location the alert names.
    2. Open Application Insights > Investigate > Availability and check which test locations fail, and the Grafana 'API overview' dashboard for availability, p95 latency and 5xx rate per location.
    3. Run this KQL in law-readmeforge-prod to see failing endpoints: AppRequests | where TimeGenerated > ago(30m) and Success == false | summarize failures=count() by Name, ResultCode, bin(TimeGenerated, 5m) | order by failures desc
    4. In the Azure portal open Front Door and CDN profiles > afd-readmeforge > Origin groups > og-api and check the health status of the origin of the affected location.
    5. If a location is unhealthy, shift traffic away from it: az afd origin update --resource-group rg-readmeforge-global --profile-name afd-readmeforge --origin-group-name og-api --origin-name prod-central-india --enabled-state Disabled
    6. Check the api Container App in the affected location: az containerapp revision list --name api --resource-group rg-readmeforge-prod-central-india --output table, and check PostgreSQL and Azure Cache for Redis health for the same location.
    7. If errors started with a release, re-activate the previous revision and move traffic back: az containerapp ingress traffic set --name api --resource-group rg-readmeforge-prod-central-india --revision-weight <previous-revision>=100
    8. If latency is high and api CPU is saturated, scale out: az containerapp update --name api --resource-group rg-readmeforge-prod-central-india --min-replicas 6 --max-replicas 30
    9. If PostgreSQL CPU or connections are the bottleneck, identify heavy queries with Query Performance Insight and follow the database alert responses; only for a full regional loss run 'SOP: Fail over database to South India'.
    10. When the health probes are green for 15 minutes, re-enable the origin: az afd origin update --resource-group rg-readmeforge-global --profile-name afd-readmeforge --origin-group-name og-api --origin-name prod-central-india --enabled-state Enabled
  - **Verification:** Availability tests pass from all test locations, the 5xx rate is below 0.5%, p95 latency is below 800 ms, Front Door shows all four origins healthy and the alerts have auto-resolved.
  - **Escalation:** If the outage is not mitigated within 30 minutes, escalate from L2 to the L3 engineering on-call through PagerDuty; declare a P1 incident (4-hour restore target) and involve the engineering manager on duty.
5.
  - **Name:** SOP: Drain and replay scan-jobs dead-letter queue
  - **Purpose:** Recover scan jobs that failed repeatedly and were moved to the dead-letter queue of the Service Bus scan-jobs queue, so that the affected repositories get their README proposals.
  - **Trigger:** The alert 'Azure Monitor metric alert - Scan-jobs dead-letter queue not empty' fires (DeadletteredMessages above 0 for 5 minutes), or a customer reports a missing README proposal after a push.
  - **Frequency:** On demand
  - **Roles:**
    - Application support engineer (L2)
    - Platform engineer
  - **Prerequisites:**
    - Azure Service Bus Data Owner role on the production Service Bus namespace
    - The root cause of the dead-lettering (for example a bug or an outage) has been fixed or ruled out
    - Azure CLI with the servicebus extension installed
  - **Steps:**
    1. Open the Service Bus namespace in the Azure portal, select Queues > scan-jobs > Service Bus Explorer > Dead-letter, and peek at several messages to read the DeadLetterReason and the repository id.
    2. Group the messages by reason and repository, and confirm that the cause has been resolved.
    3. Check the number of messages: az servicebus queue show --resource-group rg-readmeforge-prod-central-india --namespace-name sb-readmeforge-prod --name scan-jobs --query countDetails.deadLetterMessageCount
    4. In Service Bus Explorer, use Re-send selected messages to move the dead-lettered messages back to the scan-jobs queue in batches of 50.
    5. After each batch, watch the queue depth and the scan failure rate on the Grafana 'Scan pipeline' dashboard for 5 minutes before sending the next batch.
    6. Purge messages that fail again with a permanent error such as a deleted repository, and note their repository ids in the ticket.
  - **Verification:** The dead-letter count is 0 or only contains documented permanent failures, the scan-jobs queue depth returns to normal, and the affected repositories show a new README proposal.
  - **Escalation:** If messages are dead-lettered again with the same reason, stop replaying and escalate from L2 to the L3 engineering on-call (Scanner team) through PagerDuty.
6.
  - **Name:** SOP: Fail over database to South India
  - **Purpose:** Promote the geo-replicated PostgreSQL server in South India (Chennai) to primary write region when Central India (Pune) is unavailable, meeting the RPO of 15 minutes and the RTO of 1 hour.
  - **Trigger:** A declared regional outage of Central India lasting longer than 15 minutes, or a decision by the incident commander for a P1 incident affecting the primary database.
  - **Frequency:** On demand; rehearsed once a year in staging
  - **Roles:**
    - Incident commander (approver)
    - Platform engineer
    - L3 engineering on-call
  - **Prerequisites:**
    - Incident commander approval recorded in the incident channel
    - Contributor role on the production resource groups in Central India and South India
    - Read replica of the PostgreSQL Flexible Server in South India is healthy and its replication lag is known
  - **Steps:**
    1. Check the current replication lag of the South India replica in the Azure portal (PostgreSQL Flexible Server > Monitoring > Metrics > Read Replica Lag) and note it for the incident record.
    2. Promote the replica to a standalone primary: az postgres flexible-server replica promote --resource-group rg-readmeforge-prod-south-india --name psql-readmeforge-prod-south --promote-mode switchover --promote-option forced
    3. Update the database connection secret in Azure Key Vault to point to the South India server host name.
    4. Restart the api, billing-service and readme-builder-worker Container Apps in every healthy production location so they pick up the new connection string.
    5. Confirm the api health endpoint returns 200 on https://prod-south-india.readmeforge.example/healthz.
    6. Disable the failing Central India origin in Azure Front Door (see 'SOP: Respond to API outage or high latency') so that traffic goes only to healthy locations.
    7. Post an update to the #readmeforge-alerts Slack channel and the status page that the service is running on the South India database.
  - **Verification:** The api availability metric returns to normal, new README proposals are written to the South India primary, and the availability test alert is cleared.
  - **Escalation:** If the promotion does not complete within 30 minutes, open an Azure support request with severity A and escalate to the engineering manager on duty.
7.
  - **Name:** SOP: Rotate GitHub App private key
  - **Purpose:** Replace the private key that the api and webhook-receiver use to authenticate as the ReadmeForge GitHub App, so that a key is never valid longer than 12 months or after a suspected leak.
  - **Trigger:** Yearly rotation date in the operations calendar, or immediately after a suspected exposure of the key.
  - **Frequency:** Yearly, and on demand after a security event
  - **Roles:**
    - Platform engineer
    - Security officer (approver)
  - **Prerequisites:**
    - Owner permission on the ReadmeForge GitHub App in the GitHub organization settings
    - Key Vault Secrets Officer role on the production Azure Key Vault
    - Azure CLI signed in with az login to the production subscription
    - Approved change record for the rotation
  - **Steps:**
    1. In GitHub, open Organization settings > Developer settings > GitHub Apps > ReadmeForge and choose Generate a private key; download the new .pem file to a secured workstation.
    2. Store the new key as a new version of the Key Vault secret: az keyvault secret set --vault-name kv-readmeforge-prod --name github-app-private-key --file ./readmeforge-app.pem
    3. Shred the local .pem file once the upload is confirmed.
    4. Restart the api and webhook-receiver revisions in each production location so they reload the secret, for example: az containerapp revision restart --name api --resource-group rg-readmeforge-prod-central-india --revision <active-revision>
    5. Repeat the restart for prod-south-india, prod-west-india and prod-jio-west, one location at a time.
    6. Trigger a test push to the ReadmeForge sandbox repository and confirm that a scan job is created and the repository contents can be read.
    7. In GitHub, delete the old private key from the GitHub App settings.
    8. Record the completion in the change record.
  - **Verification:** The api logs in Log Analytics show successful GitHub App installation token requests after the restart, the test push produces a README proposal, and the GitHub App settings list only the new key.
  - **Escalation:** If authentication fails, re-activate the previous Key Vault secret version, restart the affected Container Apps and escalate from L2 to the L3 engineering on-call through PagerDuty.
8.
  - **Name:** SOP: Raise customer from Free to Pro repository limit after upgrade check
  - **Purpose:** Apply the Pro limit of up to 10 linked repositories for a customer whose payment succeeded but whose limit was not updated automatically by the billing-service.
  - **Trigger:** A Pro customer contacts support through Zendesk saying they cannot link a second repository after upgrading, or the alert 'Azure Monitor log alert (KQL) - Free-tier repo-limit rejections spike' points to an upgraded customer.
  - **Frequency:** On demand, a few times per month
  - **Roles:**
    - Support agent (L1)
    - Application support engineer (L2)
  - **Prerequisites:**
    - Zendesk ticket with the account email of the customer
    - Read access to the Stripe dashboard
    - Read and write access to the ReadmeForge admin tool of the api
  - **Steps:**
    1. In the Stripe dashboard, search for the customer by email and confirm there is an active Pro subscription with a paid latest invoice.
    2. If the subscription is unpaid or cancelled, reply to the customer in Zendesk with the payment status and stop the procedure.
    3. In the ReadmeForge admin tool, open the account and compare the stored plan with the Stripe subscription.
    4. Use the Resync subscription action so that the billing-service pulls the state from Stripe and sets the plan to Pro with a limit of 10 repositories.
    5. Ask the customer to reload the dashboard and try to link the additional repository.
    6. Add an internal note with the Stripe subscription id to the Zendesk ticket and set the status to Solved.
  - **Verification:** The admin tool shows plan Pro and a repository limit of 10, and the customer confirms that the second repository can be linked.
  - **Escalation:** If the resync does not change the plan, escalate from L1 to the L2 application support engineer and, if a Stripe webhook problem is suspected, to the L3 engineering on-call (Platform team) through PagerDuty.
9.
  - **Name:** SOP: Add a new production location
  - **Purpose:** Extend ReadmeForge with an additional Azure India region so that it becomes part of the global Azure Front Door routing, with the same components and configuration as the existing production locations.
  - **Trigger:** An approved capacity or resilience plan that adds a new production location.
  - **Frequency:** Rarely, about once a year at most
  - **Roles:**
    - Platform engineer
    - Release manager (approver)
    - Security officer
  - **Prerequisites:**
    - Approved change record and budget for the new location
    - Available Azure quota for Container Apps, Service Bus and PostgreSQL in the target region
    - A free internal VNet range in the 10.x.0.0/16 plan and a public ingress IP
    - Owner permission on the production subscription
  - **Steps:**
    1. Copy an existing Bicep parameter file, for example infra/parameters/prod-west-india.bicepparam, to a new file for the new location and set the region name, VNet range and ingress settings.
    2. Create the resource group: az group create --name rg-readmeforge-prod-<location> --location <azure-region>
    3. Deploy the infrastructure: az deployment group create --resource-group rg-readmeforge-prod-<location> --template-file infra/main.bicep --parameters infra/parameters/prod-<location>.bicepparam
    4. Grant the new Container Apps managed identities access to Azure Key Vault and to Azure Container Registry readmeforgeacr.azurecr.io.
    5. Deploy the current release images of all six components to the new Container Apps environment through the GitHub Actions release workflow, selecting the new location.
    6. Verify the health endpoint at https://prod-<location>.readmeforge.example/healthz and run the smoke test suite against it.
    7. In Azure Front Door, add the new location as an origin in the origin group og-api with a low weight and confirm the health probe passes.
    8. Increase the weight of the origin in steps, watching the API availability and 5xx rate for 30 minutes at each step.
    9. Add the location to the release order after prod-jio-west and to the Azure Monitor alerts, availability tests and Grafana dashboards.
    10. Update the environments documentation and the on-call runbook.
  - **Verification:** The new origin is healthy in Azure Front Door, smoke tests pass, monitoring dashboards show data for the new location, and the next weekly release deploys to it successfully.
  - **Escalation:** If the deployment or health probes fail, remove the origin from Azure Front Door and escalate to the Platform team lead; open an Azure support request for quota or regional issues.

**Notes:** Procedures are reviewed twice a year and after every P1 incident in which they were used. The failure and slowdown procedures are referenced by name from the Azure Monitor and Application Insights alerts. Commands are examples for the production subscription; always check the resource group and location before running them. Secrets are never written to tickets or chat.


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


## KPI Summary

**KPIs:**

| Name | Definition | Unit | Target | Current Value | Measurement Frequency | Owner | Data Source |
|---|---|---|---|---|---|---|---|
| Doc Change On-Time Delivery Rate | Percentage of documentation and internal-tooling change requests (docFactory templates, style-guide updates, model-schema docs) closed within their committed SLA due date, computed monthly from ticket open/close timestamps in the DevEx Jira project. | % | >= 90% | 87% | Monthly | DevEx Program Manager | Jira DevEx board - SLA report |
| docFactory Adoption Rate | Percentage of engineering teams with at least one repository that generated a document (BRD, SRS, SMTD or SOP) through docFactory in the trailing 30 days, computed monthly from docFactory's own generation logs. | % | >= 75% of onboarded teams | 61% | Monthly | DevEx Product Lead | docFactory generation-event log |
| Developer Hours Saved via Auto-Generated Docs | Estimated engineering hours saved per month by generating BRD/SRS/SMTD/SOP documents through docFactory instead of writing them by hand, computed by multiplying the number of documents generated by a per-document-type time estimate collected in the quarterly DevEx survey. | hours/month | >= 120 hours/month | 96 hours/month | Monthly | DevEx Product Lead | _N/A — The hours-saved figure is derived from a quarterly survey estimate multiplied against generation-log counts; there is no single dedicated dashboard for it yet._ |
| Internal CI/CD Platform Uptime | Percentage of scheduled availability of the internal CI/CD platform (build, test and deploy pipelines) over a calendar month, excluding announced maintenance windows, computed from the platform's own health-check monitoring. | % | >= 99.5% | 99.71% | Monthly | CI/CD Platform Reliability Lead | Grafana - CI/CD platform SLO dashboard |

**Notes:** Reviewed monthly by the DevEx leadership team; targets are re-baselined at the start of each fiscal year based on the previous year's actuals.
