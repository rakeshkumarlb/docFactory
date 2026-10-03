---
type: "Non Functional Requirements"
title: "ReadmeForge.NonFunctionalRequirements"
generated: { by: "seed", at: 2026-10-03T12:30:21Z }
status: draft
fact_key: "ReadmeForge.NonFunctionalRequirements"
version: 1
completeness: 100
---

# ReadmeForge.NonFunctionalRequirements

## Summary

The dashboard must feel responsive, the service must be available during working hours and access to repositories must be limited to what the user has authorised.

## Requirements

- Item 1
  - **Id:** NFR-001
  - **Category:** PERFORMANCE
  - **Statement:** The dashboard shall load its main page quickly for typical users.
  - **Target:** 95th percentile page load under 2 seconds
  - **Priority:** SHOULD
  - **Verification:** Monthly load test against the staging environment
- Item 2
  - **Id:** NFR-002
  - **Category:** AVAILABILITY
  - **Statement:** The dashboard and webhook receiver shall be available during working hours.
  - **Target:** 99.5% monthly availability
  - **Priority:** MUST
  - **Verification:** Availability reported from the monitoring dashboard each month
- Item 3
  - **Id:** NFR-003
  - **Category:** SECURITY
  - **Statement:** The system shall only read repositories that the signing-in user has authorised through GitHub OAuth.
  - **Target:** N/A - Access control is a yes-or-no property and has no numeric target.
  - **Priority:** MUST
  - **Verification:** Covered by the automated authorisation test suite on every release
