---
type: "Application Overview"
title: "ReadmeForge.ApplicationOverview"
generated: { by: "seed", at: 2026-10-03T12:30:20Z }
status: draft
fact_key: "ReadmeForge.ApplicationOverview"
version: 3
completeness: 100
---

# ReadmeForge.ApplicationOverview

## Application name

ReadmeForge

## Purpose

Lets a developer connect a GitHub repository and have its README.md generated and kept up to date automatically: ReadmeForge scans every change pushed to the repository, rebuilds the README context (entry points, dependencies, configuration, CI setup) and proposes an updated README, so documentation no longer drifts out of sync with the code.

## Business overview

ReadmeForge is a subscription SaaS product with two plans. The Free plan links 1 repository and includes community support only. The Pro plan links up to 10 repositories and includes customer support through a support desk. It removes the recurring chore of writing and maintaining README files, shortens onboarding for new contributors and cuts the number of 'how do I run this' questions that maintainers answer by hand. Customer data stays in India.

## Business owner

Head of Developer Experience

## Target users

- Individual developers and open-source maintainers on the Free plan
- Engineering team leads and small teams on the Pro plan
- New contributors onboarding onto a connected repository
- ReadmeForge support engineers

## Key capabilities

- Connect a GitHub repository through the ReadmeForge GitHub App with read-only access
- Automatically detect pushed changes to a connected repository and re-scan it
- Extract structured facts about entry points, dependencies, configuration and CI pipelines
- Draft README.md content from those facts and show a suggested diff
- Let the maintainer accept, edit or reject each suggested README change before anything is committed
- Enforce plan limits: 1 linked repository on Free, up to 10 on Pro
- Provide customer support for Pro subscribers through a support desk

## Out of scope

- Hosting or generating any documentation other than the top-level README (for example API reference docs or wikis)
- Source hosting providers other than GitHub
- Writing code comments or docstrings inside source files
- Committing or opening pull requests without explicit maintainer approval

## Business criticality

Tier 2 - paying Pro customers rely on it for documentation updates, but an outage delays README updates only and does not stop any customer's production system.

## Lifecycle status

In production (generally available), hosted in four Azure locations in India

## Go live date

2025-04-14

## Technology summary

Python FastAPI backend and React dashboard running as Azure Container Apps in four Azure locations in India (Central, South, West and Jio India West), backed by Azure Database for PostgreSQL, Azure Service Bus, Redis and Blob Storage, with an LLM used to draft README prose.

## Related systems

- GitHub (GitHub App and OAuth sign-in)
- Anthropic API (LLM drafting)
- Stripe (Pro subscription billing)
- Zendesk (Pro customer support desk)
- PagerDuty (on-call paging)
- Azure Front Door (global entry point)
