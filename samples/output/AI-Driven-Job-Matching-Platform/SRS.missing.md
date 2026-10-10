# AI-Driven-Job-Matching-Platform SRS: what is still needed

7 question(s) covering 11 gap(s); needs list: llm.

## product owner

1. For the 186 functional requirements of the AI-Driven Job Matching Platform, please provide the rationale, acceptance criteria, and (for 6 items) the priority (MUST, SHOULD, COULD, or WONT).
   - Covers: #3 `functional_requirements.requirements[].priority` (missing in 6 of 186), #4 `functional_requirements.requirements[].rationale` (missing in 186 of 186), #5 `functional_requirements.requirements[].acceptance_criteria` (missing in 186 of 186)
3. What is explicitly out of scope for the AI-Driven Job Matching Platform?
   - Covers: #6 `functional_requirements.out_of_scope`
5. How business-critical is the AI-Driven Job Matching Platform, and what is the impact if it becomes unavailable?
   - Covers: #1 `application_summary.business_criticality`
6. How would you summarize the functional requirements of the platform?
   - Covers: #2 `functional_requirements.summary`

## architect

2. For the 165 non-functional requirements, what are the measurable targets and the methods for verification?
   - Covers: #8 `non_functional_requirements.requirements[].target` (missing in 165 of 165), #9 `non_functional_requirements.requirements[].verification` (missing in 165 of 165)
7. How would you summarize the non-functional requirements of the platform?
   - Covers: #7 `non_functional_requirements.summary`

## service owner

4. Which service level objectives (SLOs) apply to the platform, and is there any additional context regarding them?
   - Covers: #10 `service_levels.objectives`, #11 `service_levels.notes`

## Gaps

1. `application_summary.business_criticality`: How business-critical is the application and what happens if it is unavailable?
   - Source: `ApplicationOverview.business_criticality`
2. `functional_requirements.summary`: How would you summarise the functional requirements?
   - Source: `FunctionalRequirements.summary`
3. `functional_requirements.requirements[].priority`: What is the priority (MUST, SHOULD, COULD or WONT) of this requirement?
   - Source: `FunctionalRequirements.requirements[].priority`, missing in 6 of 186 items
   - e.g. Responsive design for desktop and mobile devices | Responsive Design | Responsive design for desktop and mobile devices
   - e.g. Multilingual support (Arabic and English) and different AI functions and techniques for both Arab and English to be u...
   - e.g. Implement Web Content Accessibility Guidelines (WCAG 2.1 or later) to ensure accessibility and inclusivity for users...
4. `functional_requirements.requirements[].rationale`: Why does this requirement exist?
   - Source: `FunctionalRequirements.requirements[].rationale`, missing in 186 of 186 items
   - e.g. FR-01 | self-registration process for job seekers | The system SHALL provide a self-registration process for job seek...
   - e.g. FR-02 | account activation by user mobile number | The system SHALL support account activation by user mobile number
   - e.g. FR-03 | multi-level onboarding process | The system SHALL collect the following information from job seekers through...
5. `functional_requirements.requirements[].acceptance_criteria`: What are the acceptance criteria of this requirement?
   - Source: `FunctionalRequirements.requirements[].acceptance_criteria`, missing in 186 of 186 items
   - e.g. FR-01 | self-registration process for job seekers | The system SHALL provide a self-registration process for job seek...
   - e.g. FR-02 | account activation by user mobile number | The system SHALL support account activation by user mobile number
   - e.g. FR-03 | multi-level onboarding process | The system SHALL collect the following information from job seekers through...
6. `functional_requirements.out_of_scope`: What is explicitly out of scope?
   - Source: `FunctionalRequirements.out_of_scope`
7. `non_functional_requirements.summary`: How would you summarise the non-functional requirements?
   - Source: `NonFunctionalRequirements.summary`
8. `non_functional_requirements.requirements[].target`: What is the measurable target of this requirement?
   - Source: `NonFunctionalRequirements.requirements[].target`, missing in 165 of 165 items
   - e.g. NFR-01 | PERFORMANCE | The system SHALL provide page load times of less than 3 seconds for standard operations under...
   - e.g. NFR-02 | PERFORMANCE | The system SHALL provide search results within 2 seconds for standard search queries.
   - e.g. NFR-03 | PERFORMANCE | The system SHALL complete AI matching operations within 5 seconds for individual job-candidate...
9. `non_functional_requirements.requirements[].verification`: How is this requirement verified?
   - Source: `NonFunctionalRequirements.requirements[].verification`, missing in 165 of 165 items
   - e.g. NFR-01 | PERFORMANCE | The system SHALL provide page load times of less than 3 seconds for standard operations under...
   - e.g. NFR-02 | PERFORMANCE | The system SHALL provide search results within 2 seconds for standard search queries.
   - e.g. NFR-03 | PERFORMANCE | The system SHALL complete AI matching operations within 5 seconds for individual job-candidate...
10. `service_levels.objectives`: Which service level objectives apply?
   - Source: `Slo.objectives`
11. `service_levels.notes`: Is there any additional context about these SLOs?
   - Source: `Slo.notes`
