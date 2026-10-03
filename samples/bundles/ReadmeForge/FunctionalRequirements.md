---
type: "Functional Requirements"
title: "ReadmeForge.FunctionalRequirements"
generated: { by: "seed", at: 2026-10-03T12:30:21Z }
status: draft
fact_key: "ReadmeForge.FunctionalRequirements"
version: 2
completeness: 100
---

# ReadmeForge.FunctionalRequirements

## Summary

ReadmeForge keeps a repository README current by scanning the repository after each push and proposing README updates that a maintainer reviews and accepts or rejects.

## Requirements

- Item 1
  - **Id:** FR-001
  - **Title:** Scan a repository on push
  - **Description:** The system shall start a scan of a connected repository whenever a commit is pushed to its default branch.
  - **Priority:** MUST
  - **Rationale:** Maintainers should not have to trigger README updates by hand.
  - **Acceptance criteria:**
    - A scan starts within 60 seconds of a push to the default branch
    - The scan result is visible in the dashboard
- Item 2
  - **Id:** FR-002
  - **Title:** Propose README changes
  - **Description:** The system shall generate a proposed README update from the scan result and present it to the maintainer as a diff.
  - **Priority:** MUST
  - **Rationale:** A reviewable diff keeps the maintainer in control of what is published.
  - **Acceptance criteria:**
    - A proposal is shown as a diff against the current README
    - The maintainer can accept or reject each proposal
- Item 3
  - **Id:** FR-003
  - **Title:** Exclude paths from scanning
  - **Description:** The system shall let a maintainer exclude directories from scanning using a .readmeforge-ignore file in the repository root.
  - **Priority:** SHOULD
  - **Rationale:** N/A - The need is self-evident from FR-001 and no separate rationale has been recorded.
  - **Acceptance criteria:**
    - Paths listed in .readmeforge-ignore are not read during a scan

## Out of scope

- Editing any file other than the README
- Generating documentation for repositories that are not connected through GitHub
