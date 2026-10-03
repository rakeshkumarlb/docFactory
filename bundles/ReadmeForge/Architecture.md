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

## Components

- Item 1
  - **Dependencies:**
    - api
  - **Name:** web-app
  - **Owner:** Frontend team
  - **Purpose:** React single-page dashboard where maintainers link repositories, review and accept, edit or reject README diff proposals, and manage their plan.
  - **Technology:** React single-page application served from Azure Container Apps
- Item 2
  - **Dependencies:**
    - Azure Database for PostgreSQL
    - Azure Cache for Redis
    - Azure Service Bus
    - billing-service
    - GitHub OAuth
    - Azure Key Vault
  - **Name:** api
  - **Owner:** Platform team
  - **Purpose:** REST API for authentication, repository linking, README proposals and tier-limit checks. Single backend entry point for the dashboard.
  - **Technology:** Python 3.12 / FastAPI
- Item 3
  - **Dependencies:**
    - Azure Service Bus
    - Azure Cache for Redis
    - Azure Key Vault
    - GitHub
  - **Name:** webhook-receiver
  - **Owner:** Platform team
  - **Purpose:** Receives GitHub App push webhooks, validates their signatures and enqueues scan jobs on the scan-jobs queue.
  - **Technology:** Python 3.12 / FastAPI
- Item 4
  - **Dependencies:**
    - Azure Service Bus
    - Azure Blob Storage
    - Azure Database for PostgreSQL
    - GitHub
  - **Name:** repo-scanner-worker
  - **Owner:** Scanner team
  - **Purpose:** Takes read-only shallow clones of linked repositories, parses them with tree-sitter and extracts structured facts (entry points, dependencies, configuration, CI setup). Scales on Service Bus queue depth.
  - **Technology:** Python 3.12 / tree-sitter
- Item 5
  - **Dependencies:**
    - Azure Service Bus
    - Azure Blob Storage
    - Azure Database for PostgreSQL
    - Anthropic API
    - Azure Key Vault
  - **Name:** readme-builder-worker
  - **Owner:** Scanner team
  - **Purpose:** Assembles the README context from extracted facts, calls the LLM to draft prose and produces the README diff proposal for maintainer review.
  - **Technology:** Python 3.12
- Item 6
  - **Dependencies:**
    - Azure Database for PostgreSQL
    - Stripe
    - Azure Key Vault
  - **Name:** billing-service
  - **Owner:** Platform team
  - **Purpose:** Enforces tier limits (Free 1 linked repository, Pro up to 10) and synchronises subscription state with Stripe.
  - **Technology:** Python 3.12 / FastAPI

## Data stores

- Item 1
  - **Contents:** Accounts, linked repositories, scan result metadata, README proposals and subscription state.
  - **Name:** ReadmeForge PostgreSQL database
  - **Store type:** relational database
  - **Technology:** Azure Database for PostgreSQL Flexible Server, zone-redundant, primary write region Central India (Pune)
- Item 2
  - **Contents:** User sessions, rate-limiting counters and scan job de-duplication keys. Holds no data that cannot be rebuilt.
  - **Name:** Redis cache
  - **Store type:** in-memory cache
  - **Technology:** Azure Cache for Redis
- Item 3
  - **Contents:** The scan-jobs queue with its dead-letter queue, and the proposal-events topic.
  - **Name:** Service Bus messaging
  - **Store type:** message queue and topic
  - **Technology:** Azure Service Bus (Standard)
- Item 4
  - **Contents:** Temporary repository snapshots (automatically deleted after 24 hours) and generated README artifacts.
  - **Name:** Blob Storage
  - **Store type:** object storage
  - **Technology:** Azure Blob Storage with RA-GRS replication
- Item 5
  - **Contents:** GitHub App private key, Stripe keys and the LLM API key.
  - **Name:** Key Vault
  - **Store type:** secrets store
  - **Technology:** Azure Key Vault

## Diagram reference

docs/architecture/readmeforge-azure.md

## Integrations

- Item 1
  - **Authentication:** GitHub App installation tokens (private key held in Key Vault); webhook payloads verified by HMAC signature
  - **Data exchanged:** Push event payloads inbound; read-only repository contents and metadata outbound.
  - **Direction:** bidirectional
  - **Name:** GitHub (GitHub App)
  - **Protocol:** Webhooks (inbound) and REST over HTTPS (outbound)
  - **Purpose:** Notifies ReadmeForge of repository pushes and lets it read repository contents for scanning.
- Item 2
  - **Authentication:** API key stored in Key Vault
  - **Data exchanged:** Extracted repository facts and prompt context outbound; drafted README text inbound.
  - **Direction:** outbound
  - **Name:** Anthropic API
  - **Protocol:** REST over HTTPS
  - **Purpose:** Drafts README prose from the structured facts extracted from a repository.
- Item 3
  - **Authentication:** Stripe secret API key in Key Vault outbound; Stripe webhook signing secret inbound
  - **Data exchanged:** Customer and subscription identifiers, plan and payment status; no card data is handled by ReadmeForge.
  - **Direction:** bidirectional
  - **Name:** Stripe
  - **Protocol:** REST over HTTPS (outbound) and webhooks (inbound)
  - **Purpose:** Bills Pro subscriptions and keeps subscription state in sync.
- Item 4
  - **Authentication:** Zendesk API token
  - **Data exchanged:** Ticket subject, description, requester email and account plan.
  - **Direction:** outbound
  - **Name:** Zendesk
  - **Protocol:** REST over HTTPS
  - **Purpose:** Creates and updates Pro customer support tickets.
- Item 5
  - **Authentication:** PagerDuty integration (routing) key
  - **Data exchanged:** Alert name, severity, affected environment and a link to the alert.
  - **Direction:** outbound
  - **Name:** PagerDuty
  - **Protocol:** Events API over HTTPS
  - **Purpose:** Pages the engineering on-call rotation when Azure Monitor alerts fire.
- Item 6
  - **Authentication:** OAuth client id and secret; client secret held in Key Vault
  - **Data exchanged:** Authorization code and access token exchange; GitHub user id, login and verified email.
  - **Direction:** inbound
  - **Name:** GitHub OAuth
  - **Protocol:** OAuth 2.0 authorization code flow over HTTPS
  - **Purpose:** Lets users sign in to ReadmeForge with their GitHub identity.

## Notes

All components run in Azure Container Apps, one Container Apps environment per location, with Azure Front Door routing traffic to the nearest healthy location. All data stays in India. The database has a single primary write region (Central India, Pune) with South India (Chennai) as the paired disaster-recovery region.

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
