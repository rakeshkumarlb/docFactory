---
type: "Architecture"
title: "ReadmeForge.Architecture"
generated: { by: "seed", at: 2026-10-03T12:30:21Z }
status: draft
fact_key: "ReadmeForge.Architecture"
version: 1
completeness: 100
---

# ReadmeForge.Architecture

## Architecture style

Event-driven microservices on Azure Container Apps: a React dashboard and a FastAPI REST API in front, with webhook-triggered scan and README-build workers decoupled through Azure Service Bus queues.

## Technology stack

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

## Components

- Item 1
  - **Name:** web-app
  - **Purpose:** React single-page dashboard where maintainers link repositories, review and accept, edit or reject README diff proposals, and manage their plan.
  - **Technology:** React single-page application served from Azure Container Apps
  - **Owner:** Frontend team
  - **Dependencies:**
    - api
- Item 2
  - **Name:** api
  - **Purpose:** REST API for authentication, repository linking, README proposals and tier-limit checks. Single backend entry point for the dashboard.
  - **Technology:** Python 3.12 / FastAPI
  - **Owner:** Platform team
  - **Dependencies:**
    - Azure Database for PostgreSQL
    - Azure Cache for Redis
    - Azure Service Bus
    - billing-service
    - GitHub OAuth
    - Azure Key Vault
- Item 3
  - **Name:** webhook-receiver
  - **Purpose:** Receives GitHub App push webhooks, validates their signatures and enqueues scan jobs on the scan-jobs queue.
  - **Technology:** Python 3.12 / FastAPI
  - **Owner:** Platform team
  - **Dependencies:**
    - Azure Service Bus
    - Azure Cache for Redis
    - Azure Key Vault
    - GitHub
- Item 4
  - **Name:** repo-scanner-worker
  - **Purpose:** Takes read-only shallow clones of linked repositories, parses them with tree-sitter and extracts structured facts (entry points, dependencies, configuration, CI setup). Scales on Service Bus queue depth.
  - **Technology:** Python 3.12 / tree-sitter
  - **Owner:** Scanner team
  - **Dependencies:**
    - Azure Service Bus
    - Azure Blob Storage
    - Azure Database for PostgreSQL
    - GitHub
- Item 5
  - **Name:** readme-builder-worker
  - **Purpose:** Assembles the README context from extracted facts, calls the LLM to draft prose and produces the README diff proposal for maintainer review.
  - **Technology:** Python 3.12
  - **Owner:** Scanner team
  - **Dependencies:**
    - Azure Service Bus
    - Azure Blob Storage
    - Azure Database for PostgreSQL
    - Anthropic API
    - Azure Key Vault
- Item 6
  - **Name:** billing-service
  - **Purpose:** Enforces tier limits (Free 1 linked repository, Pro up to 10) and synchronises subscription state with Stripe.
  - **Technology:** Python 3.12 / FastAPI
  - **Owner:** Platform team
  - **Dependencies:**
    - Azure Database for PostgreSQL
    - Stripe
    - Azure Key Vault

## Data stores

- Item 1
  - **Name:** ReadmeForge PostgreSQL database
  - **Store type:** relational database
  - **Technology:** Azure Database for PostgreSQL Flexible Server, zone-redundant, primary write region Central India (Pune)
  - **Contents:** Accounts, linked repositories, scan result metadata, README proposals and subscription state.
- Item 2
  - **Name:** Redis cache
  - **Store type:** in-memory cache
  - **Technology:** Azure Cache for Redis
  - **Contents:** User sessions, rate-limiting counters and scan job de-duplication keys. Holds no data that cannot be rebuilt.
- Item 3
  - **Name:** Service Bus messaging
  - **Store type:** message queue and topic
  - **Technology:** Azure Service Bus (Standard)
  - **Contents:** The scan-jobs queue with its dead-letter queue, and the proposal-events topic.
- Item 4
  - **Name:** Blob Storage
  - **Store type:** object storage
  - **Technology:** Azure Blob Storage with RA-GRS replication
  - **Contents:** Temporary repository snapshots (automatically deleted after 24 hours) and generated README artifacts.
- Item 5
  - **Name:** Key Vault
  - **Store type:** secrets store
  - **Technology:** Azure Key Vault
  - **Contents:** GitHub App private key, Stripe keys and the LLM API key.

## Integrations

- Item 1
  - **Name:** GitHub (GitHub App)
  - **Direction:** bidirectional
  - **Protocol:** Webhooks (inbound) and REST over HTTPS (outbound)
  - **Purpose:** Notifies ReadmeForge of repository pushes and lets it read repository contents for scanning.
  - **Data exchanged:** Push event payloads inbound; read-only repository contents and metadata outbound.
  - **Authentication:** GitHub App installation tokens (private key held in Key Vault); webhook payloads verified by HMAC signature
- Item 2
  - **Name:** Anthropic API
  - **Direction:** outbound
  - **Protocol:** REST over HTTPS
  - **Purpose:** Drafts README prose from the structured facts extracted from a repository.
  - **Data exchanged:** Extracted repository facts and prompt context outbound; drafted README text inbound.
  - **Authentication:** API key stored in Key Vault
- Item 3
  - **Name:** Stripe
  - **Direction:** bidirectional
  - **Protocol:** REST over HTTPS (outbound) and webhooks (inbound)
  - **Purpose:** Bills Pro subscriptions and keeps subscription state in sync.
  - **Data exchanged:** Customer and subscription identifiers, plan and payment status; no card data is handled by ReadmeForge.
  - **Authentication:** Stripe secret API key in Key Vault outbound; Stripe webhook signing secret inbound
- Item 4
  - **Name:** Zendesk
  - **Direction:** outbound
  - **Protocol:** REST over HTTPS
  - **Purpose:** Creates and updates Pro customer support tickets.
  - **Data exchanged:** Ticket subject, description, requester email and account plan.
  - **Authentication:** Zendesk API token
- Item 5
  - **Name:** PagerDuty
  - **Direction:** outbound
  - **Protocol:** Events API over HTTPS
  - **Purpose:** Pages the engineering on-call rotation when Azure Monitor alerts fire.
  - **Data exchanged:** Alert name, severity, affected environment and a link to the alert.
  - **Authentication:** PagerDuty integration (routing) key
- Item 6
  - **Name:** GitHub OAuth
  - **Direction:** inbound
  - **Protocol:** OAuth 2.0 authorization code flow over HTTPS
  - **Purpose:** Lets users sign in to ReadmeForge with their GitHub identity.
  - **Data exchanged:** Authorization code and access token exchange; GitHub user id, login and verified email.
  - **Authentication:** OAuth client id and secret; client secret held in Key Vault

## Diagram reference

docs/architecture/readmeforge-azure.md

## Notes

All components run in Azure Container Apps, one Container Apps environment per location, with Azure Front Door routing traffic to the nearest healthy location. All data stays in India. The database has a single primary write region (Central India, Pune) with South India (Chennai) as the paired disaster-recovery region.
