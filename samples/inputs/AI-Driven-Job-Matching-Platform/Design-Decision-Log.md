# Design Decision Log

| Field | Value |
|---|---|
| Title | AI-Driven Job Matching Platform |
| Document ID | JM-ADR-014 |
| Version | 1.0 |
| Status | Approved |
| Owner | Chief Architect |
| Date | 2026-08-30 |
| Classification | Sample document, fictional content created to test docFactory |

## ADR-001 Use RabbitMQ for asynchronous work

Status: Accepted. Context: parsing, matching and notifications are slow and must not block requests. Decision: use RabbitMQ with Celery workers. Consequences: we operate a broker cluster, but retries and dead-letter handling come for free.

## ADR-002 Use OpenSearch for candidate retrieval

Status: Accepted. Context: matching needs fast filtering plus vector similarity. Decision: use OpenSearch with k-NN. Consequences: one more cluster to operate; PostgreSQL stays the system of record.

## ADR-003 Run on private Kubernetes, not a public cloud

Status: Accepted. Context: government data residency rules. Decision: two private data centres with Kubernetes. Consequences: we own the hardware lifecycle and capacity planning.

## ADR-004 Keycloak for identity

Status: Accepted. Context: single sign-on for staff and public sign-up. Decision: Keycloak with OpenID Connect. Consequences: realm configuration is code-managed.
