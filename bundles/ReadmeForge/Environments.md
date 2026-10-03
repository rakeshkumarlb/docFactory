---
type: "Environments"
title: "ReadmeForge.Environments"
generated: { by: "seed", at: 2026-10-03T12:30:22Z }
status: draft
fact_key: "ReadmeForge.Environments"
version: 1
completeness: 100
---

# ReadmeForge.Environments

## Environments

- Item 1
  - **Name:** dev
  - **Purpose:** Development and integration testing by engineers, including feature branches deployed as short-lived revisions.
  - **Hosting:** Azure Container Apps environment in Central India (Pune); ingress public IP 198.51.100.60, VNet 10.60.0.0/16
  - **Url:** https://dev.readmeforge.example
  - **Access control:** Engineering staff via Entra ID SSO group readmeforge-dev with Contributor rights; not reachable by customers.
  - **Notes:** Uses a small PostgreSQL instance and a GitHub App registered against test repositories only; data may be wiped at any time.
- Item 2
  - **Name:** staging
  - **Purpose:** Pre-production verification of each release, including the weekly release candidate, smoke tests and canary checks before production rollout.
  - **Hosting:** Azure Container Apps environment in Central India (Pune); ingress public IP 203.0.113.50, VNet 10.50.0.0/16
  - **Url:** https://staging.readmeforge.example
  - **Access control:** Engineering and QA via Entra ID SSO group readmeforge-staging; deployments only through the release pipeline.
  - **Notes:** First location in the rollout order; configuration mirrors production. Contains no customer data.
- Item 3
  - **Name:** prod-central-india
  - **Purpose:** Production location in Central India (Pune) serving customers and hosting the primary write database.
  - **Hosting:** Azure Container Apps environment in Central India (Pune); ingress public IP 203.0.113.10, VNet 10.10.0.0/16
  - **Url:** https://prod-central-india.readmeforge.example
  - **Access control:** Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only.
  - **Notes:** Primary write region for PostgreSQL. Second in the rollout order.
- Item 4
  - **Name:** prod-south-india
  - **Purpose:** Production location in South India (Chennai) serving customers and acting as the disaster-recovery region.
  - **Hosting:** Azure Container Apps environment in South India (Chennai); ingress public IP 203.0.113.20, VNet 10.20.0.0/16
  - **Url:** https://prod-south-india.readmeforge.example
  - **Access control:** Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only.
  - **Notes:** Paired disaster-recovery and geo-backup region; promoted to primary write region during a regional failure of Central India. Third in the rollout order.
- Item 5
  - **Name:** prod-west-india
  - **Purpose:** Production location in West India (Mumbai) serving customers.
  - **Hosting:** Azure Container Apps environment in West India (Mumbai); ingress public IP 198.51.100.30, VNet 10.30.0.0/16
  - **Url:** https://prod-west-india.readmeforge.example
  - **Access control:** Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only.
  - **Notes:** Fourth in the rollout order.
- Item 6
  - **Name:** prod-jio-west
  - **Purpose:** Production location in Jio India West (Jamnagar) serving customers.
  - **Hosting:** Azure Container Apps environment in Jio India West (Jamnagar); ingress public IP 198.51.100.40, VNet 10.40.0.0/16
  - **Url:** https://prod-jio-west.readmeforge.example
  - **Access control:** Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only.
  - **Notes:** Last in the rollout order.

## Notes

All environments run on Azure in India only, keeping data resident in India. Global traffic enters through Azure Front Door (https://app.readmeforge.example, API at https://api.readmeforge.example) with WAF enabled, which routes to the nearest healthy production location. Dev and staging are both in Central India.
