# AI-Driven-Job-Matching-Platform SOP: what is still needed

5 question(s) covering 12 gap(s); needs list: llm.

## service owner

1. How business-critical is the AI-Driven-Job-Matching-Platform and what is the impact if it becomes unavailable?
   - Covers: #1 `application_summary.business_criticality`

## operations

2. How is support organized for the platform, including the support model, contact details, incident handling process, and the escalation path?
   - Covers: #6 `support.support_model`, #7 `support.contacts`, #8 `support.escalation_path`, #9 `support.incident_process`
3. Which runbooks and standard operating procedures exist for the platform, and is there any additional context or notes regarding these procedures?
   - Covers: #10 `support.runbooks`, #11 `standard_operating_procedures.procedures`, #12 `standard_operating_procedures.notes`
4. For the 2 monitoring alerts (NFR-44, NFR-134), what are their severities, the required response actions when they fire, and their notification channels?
   - Covers: #2 `monitoring.alerts[].severity` (missing in 2 of 2), #3 `monitoring.alerts[].response_action` (missing in 2 of 2), #4 `monitoring.alerts[].notification_channel` (missing in 2 of 2)
5. Where are the application logs for the AI-Driven-Job-Matching-Platform stored?
   - Covers: #5 `monitoring.log_locations`

## Gaps

1. `application_summary.business_criticality`: How business-critical is the application and what happens if it is unavailable?
   - Source: `ApplicationOverview.business_criticality`
2. `monitoring.alerts[].severity`: What is the severity of this alert?
   - Source: `Monitoring.alerts[].severity`, missing in 2 of 2 items
   - e.g. NFR-44
   - e.g. NFR-134
3. `monitoring.alerts[].response_action`: What should be done when this alert fires?
   - Source: `Monitoring.alerts[].response_action`, missing in 2 of 2 items
   - e.g. NFR-44
   - e.g. NFR-134
4. `monitoring.alerts[].notification_channel`: Where is this alert delivered?
   - Source: `Monitoring.alerts[].notification_channel`, missing in 2 of 2 items
   - e.g. NFR-44
   - e.g. NFR-134
5. `monitoring.log_locations`: Where are the application logs stored?
   - Source: `Monitoring.log_locations`
6. `support.support_model`: How is support organised?
   - Source: `Support.support_model`
7. `support.contacts`: Who are the support contacts?
   - Source: `Support.contacts`
8. `support.escalation_path`: What is the escalation path?
   - Source: `Support.escalation_path`
9. `support.incident_process`: How are incidents handled?
   - Source: `Support.incident_process`
10. `support.runbooks`: Which runbooks exist?
   - Source: `Support.runbooks`
11. `standard_operating_procedures.procedures`: Which standard operating procedures exist?
   - Source: `Sop.procedures`
12. `standard_operating_procedures.notes`: Is there any additional context about these procedures?
   - Source: `Sop.notes`
