# AI-Driven-Job-Matching-Platform SMTD: what is still needed

14 question(s) covering 42 gap(s); needs list: llm.

## product owner

1. How business-critical is the AI-Driven-Job-Matching-Platform and what is the impact if it becomes unavailable?
   - Covers: #1 `application_summary.business_criticality`

## architect

2. What is the overall architectural style of the platform, where is the architecture diagram stored, and is there any additional context to provide?
   - Covers: #2 `architecture.architecture_style`, #13 `architecture.diagram_reference`, #14 `architecture.notes`
3. For the 7 architectural components (e.g., Application servers, Database servers), what are their purposes, the technologies used, the owning teams/roles, and their dependencies?
   - Covers: #3 `architecture.components[].purpose` (missing in 7 of 7), #4 `architecture.components[].technology` (missing in 7 of 7), #5 `architecture.components[].owner` (missing in 7 of 7), #6 `architecture.components[].dependencies` (missing in 7 of 7)
4. Which data stores does the AI-Driven-Job-Matching-Platform use?
   - Covers: #7 `architecture.data_stores`
5. For the 7 integrations (e.g., Third-Party Job Portals, Government Databases), what is the purpose, direction (inbound/outbound/bidirectional), protocol/interface, data exchanged, and authentication method for each?
   - Covers: #8 `architecture.integrations[].direction` (missing in 7 of 7), #9 `architecture.integrations[].protocol` (missing in 4 of 7), #10 `architecture.integrations[].purpose` (missing in 2 of 7), #11 `architecture.integrations[].data_exchanged` (missing in 6 of 7), #12 `architecture.integrations[].authentication` (missing in 6 of 7)

## operations

6. For the 4 environments (Technical, Hardware, Software, etc.), what is the purpose, hosting location, base URL, and access control mechanism for each, and is there any additional context?
   - Covers: #15 `environments.environments[].purpose` (missing in 4 of 4), #16 `environments.environments[].hosting` (missing in 4 of 4), #17 `environments.environments[].url` (missing in 4 of 4), #18 `environments.environments[].access_control` (missing in 4 of 4), #19 `environments.notes`
7. Regarding deployment, what is the release process, the CI/CD tooling used, the release frequency, the rollback procedure for failed releases, and how are configurations and secrets managed?
   - Covers: #20 `deployment.release_process`, #21 `deployment.ci_cd_tooling`, #22 `deployment.release_frequency`, #23 `deployment.rollback_procedure`, #24 `deployment.configuration_management`
8. For the 2 monitoring alerts (NFR-44, NFR-134), what is the severity, the required response action, and the notification channel? Additionally, where are the application logs stored?
   - Covers: #25 `monitoring.alerts[].severity` (missing in 2 of 2), #26 `monitoring.alerts[].response_action` (missing in 2 of 2), #27 `monitoring.alerts[].notification_channel` (missing in 2 of 2), #28 `monitoring.log_locations`
9. What is the backup retention period for the platform?
   - Covers: #29 `backup_recovery.backup_retention`
12. Which standard operating procedures (SOPs) exist and is there any additional context for them?
   - Covers: #37 `standard_operating_procedures.procedures`, #38 `standard_operating_procedures.notes`

## service owner

10. How is support organized for the platform, including the support model, contact persons, escalation path, incident handling process, and available runbooks?
   - Covers: #30 `support.support_model`, #31 `support.contacts`, #32 `support.escalation_path`, #33 `support.incident_process`, #34 `support.runbooks`
11. Which known errors exist for the platform and is there any additional context regarding them?
   - Covers: #35 `known_errors.known_errors`, #36 `known_errors.notes`
13. Which service level objectives (SLOs) apply to the platform and is there any additional context?
   - Covers: #39 `service_levels.objectives`, #40 `service_levels.notes`
14. Which KPIs are tracked for the platform and how are they governed or reviewed?
   - Covers: #41 `kpi_summary.kpis`, #42 `kpi_summary.notes`

## Gaps

1. `application_summary.business_criticality`: How business-critical is the application and what happens if it is unavailable?
   - Source: `ApplicationOverview.business_criticality`
2. `architecture.architecture_style`: What is the overall architectural style?
   - Source: `Architecture.architecture_style`
3. `architecture.components[].purpose`: What is the purpose of this component?
   - Source: `Architecture.components[].purpose`, missing in 7 of 7 items
   - e.g. Application servers
   - e.g. Database servers
   - e.g. Storage systems
4. `architecture.components[].technology`: Which technology is this component built with?
   - Source: `Architecture.components[].technology`, missing in 7 of 7 items
   - e.g. Application servers
   - e.g. Database servers
   - e.g. Storage systems
5. `architecture.components[].owner`: Which team or role owns this component?
   - Source: `Architecture.components[].owner`, missing in 7 of 7 items
   - e.g. Application servers
   - e.g. Database servers
   - e.g. Storage systems
6. `architecture.components[].dependencies`: Which other components or services does this component depend on?
   - Source: `Architecture.components[].dependencies`, missing in 7 of 7 items
   - e.g. Application servers
   - e.g. Database servers
   - e.g. Storage systems
7. `architecture.data_stores`: Which data stores does the application use?
   - Source: `Architecture.data_stores`
8. `architecture.integrations[].direction`: Is the integration inbound, outbound or bidirectional?
   - Source: `Architecture.integrations[].direction`, missing in 7 of 7 items
   - e.g. Third-Party Job Portals Registration and Integration (i.e. jobs.ps)
   - e.g. External Job Site Integration
   - e.g. Government Database Integration
9. `architecture.integrations[].protocol`: Which protocol or interface does the integration use?
   - Source: `Architecture.integrations[].protocol`, missing in 4 of 7 items
   - e.g. External Job Site Integration
   - e.g. Government Database Integration
   - e.g. Email and SMS Gateways
10. `architecture.integrations[].purpose`: What is the purpose of this integration?
   - Source: `Architecture.integrations[].purpose`, missing in 2 of 7 items
   - e.g. external integrations
   - e.g. legacy system integration
11. `architecture.integrations[].data_exchanged`: What data is exchanged over this integration?
   - Source: `Architecture.integrations[].data_exchanged`, missing in 6 of 7 items
   - e.g. External Job Site Integration
   - e.g. Government Database Integration
   - e.g. Email and SMS Gateways
12. `architecture.integrations[].authentication`: How is this integration authenticated?
   - Source: `Architecture.integrations[].authentication`, missing in 6 of 7 items
   - e.g. External Job Site Integration
   - e.g. Government Database Integration
   - e.g. Email and SMS Gateways
13. `architecture.diagram_reference`: Where is the architecture diagram stored?
   - Source: `Architecture.diagram_reference`
14. `architecture.notes`: Is there any additional context about the architecture?
   - Source: `Architecture.notes`
15. `environments.environments[].purpose`: What is this environment used for?
   - Source: `Environments.environments[].purpose`, missing in 4 of 4 items
   - e.g. Technical Environment
   - e.g. Hardware Environment
   - e.g. Software Environment
16. `environments.environments[].hosting`: Where is this environment hosted?
   - Source: `Environments.environments[].hosting`, missing in 4 of 4 items
   - e.g. Technical Environment
   - e.g. Hardware Environment
   - e.g. Software Environment
17. `environments.environments[].url`: What is the base URL of this environment?
   - Source: `Environments.environments[].url`, missing in 4 of 4 items
   - e.g. Technical Environment
   - e.g. Hardware Environment
   - e.g. Software Environment
18. `environments.environments[].access_control`: Who has access to this environment and how is access controlled?
   - Source: `Environments.environments[].access_control`, missing in 4 of 4 items
   - e.g. Technical Environment
   - e.g. Hardware Environment
   - e.g. Software Environment
19. `environments.notes`: Is there any additional context about the environments?
   - Source: `Environments.notes`
20. `deployment.release_process`: How is a release performed?
   - Source: `Deployment.release_process`
21. `deployment.ci_cd_tooling`: Which CI/CD tooling is used?
   - Source: `Deployment.ci_cd_tooling`
22. `deployment.release_frequency`: How often is the application released?
   - Source: `Deployment.release_frequency`
23. `deployment.rollback_procedure`: How is a failed release rolled back?
   - Source: `Deployment.rollback_procedure`
24. `deployment.configuration_management`: How are configuration and secrets managed?
   - Source: `Deployment.configuration_management`
25. `monitoring.alerts[].severity`: What is the severity of this alert?
   - Source: `Monitoring.alerts[].severity`, missing in 2 of 2 items
   - e.g. NFR-44
   - e.g. NFR-134
26. `monitoring.alerts[].response_action`: What should be done when this alert fires?
   - Source: `Monitoring.alerts[].response_action`, missing in 2 of 2 items
   - e.g. NFR-44
   - e.g. NFR-134
27. `monitoring.alerts[].notification_channel`: Where is this alert delivered?
   - Source: `Monitoring.alerts[].notification_channel`, missing in 2 of 2 items
   - e.g. NFR-44
   - e.g. NFR-134
28. `monitoring.log_locations`: Where are the application logs stored?
   - Source: `Monitoring.log_locations`
29. `backup_recovery.backup_retention`: How long are backups retained?
   - Source: `BackupRecovery.backup_retention`
30. `support.support_model`: How is support organised?
   - Source: `Support.support_model`
31. `support.contacts`: Who are the support contacts?
   - Source: `Support.contacts`
32. `support.escalation_path`: What is the escalation path?
   - Source: `Support.escalation_path`
33. `support.incident_process`: How are incidents handled?
   - Source: `Support.incident_process`
34. `support.runbooks`: Which runbooks exist?
   - Source: `Support.runbooks`
35. `known_errors.known_errors`: Which known errors exist?
   - Source: `KnownErrors.known_errors`
36. `known_errors.notes`: Is there any additional context about the known errors?
   - Source: `KnownErrors.notes`
37. `standard_operating_procedures.procedures`: Which standard operating procedures exist?
   - Source: `Sop.procedures`
38. `standard_operating_procedures.notes`: Is there any additional context about these procedures?
   - Source: `Sop.notes`
39. `service_levels.objectives`: Which service level objectives apply?
   - Source: `Slo.objectives`
40. `service_levels.notes`: Is there any additional context about these SLOs?
   - Source: `Slo.notes`
41. `kpi_summary.kpis`: Which KPIs are tracked?
   - Source: `Kpis.kpis`
42. `kpi_summary.notes`: Is there any additional context about how these KPIs are governed or reviewed?
   - Source: `Kpis.notes`
