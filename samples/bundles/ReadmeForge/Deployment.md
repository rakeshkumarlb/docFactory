---
type: "Deployment"
title: "ReadmeForge.Deployment"
generated: { by: "seed", at: 2026-10-03T12:30:22Z }
status: draft
fact_key: "ReadmeForge.Deployment"
version: 1
completeness: 100
---

# ReadmeForge.Deployment

## Release process

GitHub Actions builds and tests the container images and pushes them to Azure Container Registry (readmeforgeacr.azurecr.io). The pipeline then deploys each image as a new Container Apps revision using blue/green traffic splitting: 10% canary traffic for 30 minutes, then 100% if health checks and alerts stay clean. Locations roll out one at a time in the order staging, prod-central-india, prod-south-india, prod-west-india, prod-jio-west.

## Ci cd tooling

GitHub Actions for build, test and deployment; Bicep for infrastructure as code; Azure Container Registry for images; Azure Container Apps revisions for releases.

## Release frequency

Weekly on Tuesdays at 11:00 IST; hotfixes may be released on any day.

## Rollback procedure

Re-activate the previous Container Apps revision and shift 100% of traffic back to it, which takes under 5 minutes. Database migrations are backward-compatible (expand/contract), so the previous revision keeps working against the migrated schema.

## Configuration management

Container Apps secrets that reference Azure Key Vault hold all secrets. Environment-specific settings live in Bicep parameter files in the repository and are applied by the deployment pipeline.
