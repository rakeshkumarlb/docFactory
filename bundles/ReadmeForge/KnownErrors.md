---
type: "Known Errors"
title: "ReadmeForge.KnownErrors"
generated: { by: "seed", at: 2026-10-03T12:30:22Z }
status: draft
fact_key: "ReadmeForge.KnownErrors"
version: 1
completeness: 100
---

# ReadmeForge.KnownErrors

## Known errors

- Item 1
  - **Cause:** GitHub redelivers a webhook when the webhook-receiver does not answer within 10 seconds. During load the receiver enqueues the scan job before responding, so redelivered deliveries create additional scan-jobs messages for the same commit.
  - **Error id:** KE-001
  - **Permanent fix:** Acknowledge the webhook immediately and de-duplicate on the X-GitHub-Delivery id and commit SHA in Azure Cache for Redis before enqueueing (planned for the webhook-receiver in release 2.14).
  - **Related ticket:** RF-1423
  - **Severity:** Medium
  - **Status:** Workaround available
  - **Symptoms:** A single push shows two or three scan runs for the same commit in the dashboard, and the maintainer receives duplicate README proposals for the same change.
  - **Title:** Duplicate scans triggered by GitHub webhook redelivery
  - **Workaround:** Reject the surplus proposals in the dashboard. Support can purge duplicate messages from the scan-jobs queue in Azure Service Bus Explorer if a backlog builds up.
- Item 2
  - **Cause:** The repo-scanner-worker performs a shallow clone and parses with tree-sitter within the container's ephemeral storage and a fixed 30-minute job lock. Repositories above roughly 2 GB exceed the storage or time budget.
  - **Error id:** KE-002
  - **Permanent fix:** Introduce sparse checkout of only the files relevant to entry points, dependencies, config and CI, and move snapshots to Azure Blob Storage to lift the size limit.
  - **Related ticket:** RF-1377
  - **Severity:** Medium
  - **Status:** Open
  - **Symptoms:** The scan for a large repository stays in Running and then fails after 30 minutes with the message 'Scan timed out'. No README proposal is created.
  - **Title:** Repositories larger than about 2 GB time out during scan
  - **Workaround:** The maintainer can exclude large directories (for example vendored dependencies or assets) with a .readmeforge-ignore file in the repository root and retrigger the scan from the dashboard.
- Item 3
  - **Cause:** Sessions are stored only in Azure Cache for Redis. A failover to the replica drops connections and, because replication is asynchronous, the most recent session writes are not present on the new primary.
  - **Error id:** KE-003
  - **Permanent fix:** Issue signed, short-lived session tokens that can be re-validated against PostgreSQL after a cache miss so that a Redis failover no longer ends the session.
  - **Related ticket:** RF-1290
  - **Severity:** Low
  - **Status:** Workaround available
  - **Symptoms:** During a Redis failover users are suddenly returned to the sign-in page and must sign in again with GitHub OAuth. Unsaved edits to a README proposal in the browser may be lost.
  - **Title:** Users are signed out when Azure Cache for Redis fails over
  - **Workaround:** Sign in again; the proposal itself is stored in PostgreSQL and is still available. Support informs affected users through the status page when a failover is announced.
- Item 4
  - **Cause:** The readme-builder-worker compares the regenerated README.md text with the committed file byte by byte, and does not normalize line endings before computing the diff.
  - **Error id:** KE-004
  - **Permanent fix:** N/A - The behaviour is accepted as low impact and the .gitattributes workaround is sufficient; no permanent fix is planned at this time.
  - **Related ticket:** N/A - The issue is documented only in the support knowledge base and no engineering ticket has been raised for it.
  - **Severity:** Low
  - **Status:** Accepted, no fix planned
  - **Symptoms:** A push that only converts line endings (CRLF to LF or the reverse) leads to a proposal in which large unchanged sections of README.md are shown as modified.
  - **Title:** CRLF-only changes produce noisy README diffs
  - **Workaround:** Reject the proposal in the dashboard. Repositories can add a .gitattributes file with 'README.md text eol=lf' so that line endings stay consistent.
- Item 5
  - **Cause:** The combined request rate of the readme-builder-worker replicas exceeds the requests-per-minute quota of the Anthropic API key held in Azure Key Vault, so calls are throttled and retried with exponential backoff.
  - **Error id:** KE-005
  - **Permanent fix:** Request a higher quota from the LLM provider and add a global token-bucket limiter with a priority queue so that Pro customers are drafted first.
  - **Related ticket:** RF-1451
  - **Severity:** Medium
  - **Status:** Open
  - **Symptoms:** README proposals stay in the Drafting state for tens of minutes, mostly on weekday mornings after the weekly release. The readme-builder-worker logs show repeated 429 responses from the Anthropic API.
  - **Title:** LLM rate limiting (HTTP 429) delays README proposals
  - **Workaround:** No action is needed from the customer, the proposal completes once capacity is available. Operations can follow 'SOP: Handle LLM API throttling' to lower readme-builder-worker concurrency.

## Notes

The known errors are reviewed at every weekly release and at the monthly operations review. Errors are closed when the permanent fix has been deployed to all four production locations. Support engineers use the workarounds when answering Pro customer tickets in Zendesk.
