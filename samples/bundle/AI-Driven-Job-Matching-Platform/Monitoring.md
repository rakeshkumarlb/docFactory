---
type: "Monitoring"
title: "AI-Driven-Job-Matching-Platform monitoring"
description: "Requirements for user activity tracking, security monitoring, and general system health and performance monitoring."
tags: ["monitoring", "extracted"]
sources:
  - resource: "AI-Driven-Job-Matching-Platform/references/Annex-A-Detailed-Software-Requirements-Specification-SRS.pdf"
    last_modified: 2026-10-10T12:10:17+00:00
generated: { by: "okf-extraction-agent/gemma4:31b", at: 2026-10-10T12:13:01Z }
status: draft
fact_key: "AI-Driven-Job-Matching-Platform.Monitoring"
version: 1
completeness: 50
hashcode: "2db62a9b478574ee41feeede1db08f10237416f15afa5232d39fc6fcf2f8b408"
---

# Value

```json
{
  "monitoring_tools": [
    "NFR-137. log aggregation and analysis tools"
  ],
  "key_metrics": [
    "FR-116. job seeker activities including profile views, job searches, applications, and interactions",
    "FR-117. employer activities including job postings, candidate searches",
    "NFR-133. system health and performance"
  ],
  "alerts": [
    {
      "name": "NFR-44",
      "condition": "NFR-44. The system SHALL provide real-time monitoring and alerting for security incidents.",
      "severity": "",
      "response_action": "",
      "notification_channel": ""
    },
    {
      "name": "NFR-134",
      "condition": "NFR-134. The system SHALL generate alerts for critical system events and performance thresholds.",
      "severity": "",
      "response_action": "",
      "notification_channel": ""
    }
  ],
  "dashboards": [
    "FR-119. MOL Life dashboard should include current logins, number of current logins and last sessions, with links to these users profiles",
    "NFR-136. The system SHALL provide dashboards for monitoring system status and performance metrics."
  ],
  "log_locations": []
}
```

# Open questions: AI-Driven-Job-Matching-Platform.Monitoring

These fields are not answered yet. Until someone answers them, the default shown is assumed.

1. `alerts[].severity` (missing in 2 of 2 items): What is the severity of this alert?
   Assumed until answered: empty text
   Items:
   - NFR-44
   - NFR-134
2. `alerts[].response_action` (missing in 2 of 2 items): What should be done when this alert fires?
   Assumed until answered: empty text
   Items:
   - NFR-44
   - NFR-134
3. `alerts[].notification_channel` (missing in 2 of 2 items): Where is this alert delivered?
   Assumed until answered: empty text
   Items:
   - NFR-44
   - NFR-134
4. `log_locations`: Where are the application logs stored?
   Assumed until answered: empty list
