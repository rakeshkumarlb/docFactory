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
  - **Access control:** Engineering staff via Entra ID SSO group readmeforge-dev with Contributor rights; not reachable by customers.
  - **Hosting:** Azure Container Apps environment in Central India (Pune); ingress public IP 198.51.100.60, VNet 10.60.0.0/16
  - **Name:** dev
  - **Notes:** Uses a small PostgreSQL instance and a GitHub App registered against test repositories only; data may be wiped at any time.
  - **Purpose:** Development and integration testing by engineers, including feature branches deployed as short-lived revisions.
  - **Url:** https://dev.readmeforge.example
- Item 2
  - **Access control:** Engineering and QA via Entra ID SSO group readmeforge-staging; deployments only through the release pipeline.
  - **Hosting:** Azure Container Apps environment in Central India (Pune); ingress public IP 203.0.113.50, VNet 10.50.0.0/16
  - **Name:** staging
  - **Notes:** First location in the rollout order; configuration mirrors production. Contains no customer data.
  - **Purpose:** Pre-production verification of each release, including the weekly release candidate, smoke tests and canary checks before production rollout.
  - **Url:** https://staging.readmeforge.example
- Item 3
  - **Access control:** Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only.
  - **Hosting:** Azure Container Apps environment in Central India (Pune); ingress public IP 203.0.113.10, VNet 10.10.0.0/16
  - **Name:** prod-central-india
  - **Notes:** Primary write region for PostgreSQL. Second in the rollout order.
  - **Purpose:** Production location in Central India (Pune) serving customers and hosting the primary write database.
  - **Url:** https://prod-central-india.readmeforge.example
- Item 4
  - **Access control:** Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only.
  - **Hosting:** Azure Container Apps environment in South India (Chennai); ingress public IP 203.0.113.20, VNet 10.20.0.0/16
  - **Name:** prod-south-india
  - **Notes:** Paired disaster-recovery and geo-backup region; promoted to primary write region during a regional failure of Central India. Third in the rollout order.
  - **Purpose:** Production location in South India (Chennai) serving customers and acting as the disaster-recovery region.
  - **Url:** https://prod-south-india.readmeforge.example
- Item 5
  - **Access control:** Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only.
  - **Hosting:** Azure Container Apps environment in West India (Mumbai); ingress public IP 198.51.100.30, VNet 10.30.0.0/16
  - **Name:** prod-west-india
  - **Notes:** Fourth in the rollout order.
  - **Purpose:** Production location in West India (Mumbai) serving customers.
  - **Url:** https://prod-west-india.readmeforge.example
- Item 6
  - **Access control:** Read-only for on-call and application support engineers via Azure RBAC and just-in-time elevation (Privileged Identity Management); changes only through the release pipeline. Customers reach it through Azure Front Door only.
  - **Hosting:** Azure Container Apps environment in Jio India West (Jamnagar); ingress public IP 198.51.100.40, VNet 10.40.0.0/16
  - **Name:** prod-jio-west
  - **Notes:** Last in the rollout order.
  - **Purpose:** Production location in Jio India West (Jamnagar) serving customers.
  - **Url:** https://prod-jio-west.readmeforge.example

## Notes

All environments run on Azure in India only, keeping data resident in India. Global traffic enters through Azure Front Door (https://app.readmeforge.example, API at https://api.readmeforge.example) with WAF enabled, which routes to the nearest healthy production location. Dev and staging are both in Central India.
