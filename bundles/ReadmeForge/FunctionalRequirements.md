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

## Out of scope

- Editing any file other than the README
- Generating documentation for repositories that are not connected through GitHub

## Requirements

- Item 1
  - **Acceptance criteria:**
    - A scan starts within 60 seconds of a push to the default branch
    - The scan result is visible in the dashboard
  - **Description:** The system shall start a scan of a connected repository whenever a commit is pushed to its default branch.
  - **Id:** FR-001
  - **Priority:** MUST
  - **Rationale:** Maintainers should not have to trigger README updates by hand.
  - **Title:** Scan a repository on push
- Item 2
  - **Acceptance criteria:**
    - A proposal is shown as a diff against the current README
    - The maintainer can accept or reject each proposal
  - **Description:** The system shall generate a proposed README update from the scan result and present it to the maintainer as a diff.
  - **Id:** FR-002
  - **Priority:** MUST
  - **Rationale:** A reviewable diff keeps the maintainer in control of what is published.
  - **Title:** Propose README changes
- Item 3
  - **Acceptance criteria:**
    - Paths listed in .readmeforge-ignore are not read during a scan
  - **Description:** The system shall let a maintainer exclude directories from scanning using a .readmeforge-ignore file in the repository root.
  - **Id:** FR-003
  - **Priority:** SHOULD
  - **Rationale:** N/A - The need is self-evident from FR-001 and no separate rationale has been recorded.
  - **Title:** Exclude paths from scanning

## Summary

ReadmeForge keeps a repository README current by scanning the repository after each push and proposing README updates that a maintainer reviews and accepts or rejects.
