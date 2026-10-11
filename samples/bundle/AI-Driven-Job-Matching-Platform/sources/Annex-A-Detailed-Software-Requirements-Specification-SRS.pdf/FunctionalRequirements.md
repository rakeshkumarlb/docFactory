---
type: "Contribution"
title: "AI-Driven-Job-Matching-Platform.FunctionalRequirements from Annex-A-Detailed-Software-Requirements-Specification-SRS.pdf"
description: "Functional requirements for job seeker registration and profile management."
sources:
  - resource: "AI-Driven-Job-Matching-Platform/references/Annex-A-Detailed-Software-Requirements-Specification-SRS.pdf"
generated: { by: "okf-extraction-agent/gemma4:31b", at: "2026-10-10T12:12:53Z" }
fact_key: "AI-Driven-Job-Matching-Platform.FunctionalRequirements"
hashcode: "fe8437f70fd8fc4cb5a08188b7dc48871a45cdd2dd77876dbf594aacfd21471a"
chunks_hash: "446bfdd85d50e611369816de89a8138207aa557ef53aa5bee7c708413c0b49ab"
---

# Value

```json
{
  "requirements": [
    {
      "description": "The system SHALL provide a self-registration process for job seekers.",
      "id": "FR-01",
      "priority": "MUST",
      "title": "self-registration process for job seekers"
    },
    {
      "description": "The system SHALL support account activation by user mobile number",
      "id": "FR-02",
      "priority": "MUST",
      "title": "account activation by user mobile number"
    },
    {
      "description": "The system SHALL collect the following information from job seekers through a multi-level onboarding process (via mobile/email): - Level 1: First and last name, email, mobile number, password, gender - Level 2: Education, work experience, skills, training, certificates, recent salary (optional), current address, permanent address/residence - Level 3 (optional): Social media links (e.g., LinkedIn, IEEE, X), personal statement, bio",
      "id": "FR-03",
      "priority": "MUST",
      "title": "multi-level onboarding process"
    },
    {
      "description": "The system SHALL support resume/CV upload in common formats (PDF, DOCX, TXT).",
      "id": "FR-04",
      "priority": "MUST",
      "title": "resume/CV upload"
    },
    {
      "description": "The system SHALL offer the CV to AI engine to automatically extract information from uploaded resumes/CVs using AI parsing technology and add the extracted information to the profile.",
      "id": "FR-05",
      "priority": "MUST",
      "title": "AI parsing technology for CVs"
    },
    {
      "description": "The system SHALL allow job seekers to build their profiles using a staged, stepwise form with popup prompts for the following sections: - Education: Degree, institution - Experience: Company, role, duration - Skills: Primary/secondary; soft/hard - Preferences: Job type, desired salary, preferred location",
      "id": "FR-06",
      "priority": "MUST",
      "title": "staged, stepwise profile building"
    },
    {
      "description": "The system SHALL allow job seekers to edit and update their profiles at any time.",
      "id": "FR-07",
      "priority": "MUST",
      "title": "edit and update profiles"
    },
    {
      "description": "The system SHALL provide a recommendation to encourage job seekers to complete their profiles and to explore opportunities aligned with their broader skills, interests, and experiences beyond formal education and training.",
      "id": "FR-08",
      "priority": "MUST",
      "title": "profile completion recommendations"
    },
    {
      "description": "The system SHALL allow job seekers to set job preferences including job type, industry, location, salary expectations, and work arrangements.",
      "id": "FR-09",
      "priority": "MUST",
      "title": "set job preferences"
    },
    {
      "description": "The system SHALL provide privacy controls that allow job seekers to set visibility preferences for their profile (public or private), and request account deactivation or deletion.",
      "id": "FR-10",
      "priority": "MUST",
      "title": "privacy controls"
    },
    {
      "description": "The system SHALL generate a shareable public profile URL/QR Code for each job seeker, if activated by the user.",
      "id": "FR-11",
      "priority": "MUST",
      "title": "shareable public profile URL/QR Code"
    },
    {
      "description": "The system SHALL allow the job seeker to upload supplementary documents (i.e. certificate )",
      "id": "FR-12",
      "priority": "MUST",
      "title": "upload supplementary documents"
    },
    {
      "description": "The system SHALL provide a stepwise registration process for employers: - Level 1: Company name, email, mobile number, company ID, and registration number (if registered) - Level 2: Website, industry, company size, address, company description, and attachments for supplementary documents",
      "id": "FR-13",
      "priority": "MUST",
      "title": "stepwise registration process for employers"
    },
    {
      "description": "The system SHALL require account activation through a one-time password (OTP) sent to the registered mobile number.",
      "id": "FR-14",
      "priority": "MUST",
      "title": "account activation through a one-time password (OTP)"
    },
    {
      "description": "The system SHALL provide an employer verification process that includes automatic verification using official information such as the employer’s registration number, VAT number, and registered mobile number as recorded in government databases.",
      "id": "FR-15",
      "priority": "MUST",
      "title": "employer verification process"
    },
    {
      "description": "If automatic verification fails, the Ministry of Labor (MoL) SHALL be able to manually verify the employer’s account based on submitted registration details and/or direct contact.",
      "id": "FR-16",
      "priority": "MUST",
      "title": "manual verification by the Ministry of Labor (MoL)"
    },
    {
      "description": "The system SHALL display a (cid:33061)(cid:57281) Verified Employer badge next to the names of verified companies to enhance trust for job seekers and provide added value to employers who complete the verification process.",
      "id": "FR-17",
      "priority": "MUST",
      "title": "Verified Employer badge"
    },
    {
      "description": "The system SHALL provide a company profile page that showcases the employer's information, job openings, and company background.",
      "id": "FR-18",
      "priority": "MUST",
      "title": "company profile page"
    },
    {
      "description": "The system SHALL allow employers to upload company logo, and images to enhance their profile. In addition to documents such as company registration and manage uploaded documents",
      "id": "FR-19",
      "priority": "MUST",
      "title": "upload company logo, and images"
    },
    {
      "description": "The system SHALL provide a dashboard for employers to manage job postings, view matched job seekers, create shortlists of interested or qualified candidates, and track key metrics.",
      "id": "FR-20",
      "priority": "MUST",
      "title": "dashboard for employers"
    },
    {
      "description": "The system SHALL allow the employer to upload supplementary documents (i.e. company registration certificate)",
      "id": "FR-21",
      "priority": "MUST",
      "title": "upload supplementary documents"
    },
    {
      "description": "The system SHALL provide a registration and onboarding process for external job sites.",
      "id": "FR-22",
      "priority": "MUST",
      "title": "Registration and onboarding process for external job sites"
    },
    {
      "description": "The system SHOULD issue a unique API key or token to each partner for secure access, with support for optional IP whitelisting, usage limits, and token expiration management to ensure controlled and secure integration.",
      "id": "FR-23",
      "priority": "SHOULD",
      "title": "Unique API key or token for secure access"
    },
    {
      "description": "The system SHOULD support job posting via a secure RESTful Push API, allowing external platforms to submit job opportunities directly to the job matching system.",
      "id": "FR-24",
      "priority": "SHOULD",
      "title": "Job posting via secure RESTful Push API"
    },
    {
      "description": "The system SHALL allow external job sites to configure data mapping between their system and the platform, provide the sites with the standard schema to successfully integrate with the platform",
      "id": "FR-25",
      "priority": "MUST",
      "title": "Data mapping and standard schema configuration"
    },
    {
      "description": "The system SHOULD provide a testing environment for external job sites to validate their integration.",
      "id": "FR-26",
      "priority": "SHOULD",
      "title": "Testing environment for integration validation"
    },
    {
      "description": "The system SHOULD implement comprehensive error handling and response logging by providing clear API response codes with descriptive messages for success, failure, duplicates, and validation errors.",
      "id": "FR-27",
      "priority": "SHOULD",
      "title": "Comprehensive error handling and response logging"
    },
    {
      "description": "The system SHOULD grant external platforms access to view submission logs for monitoring and troubleshooting purposes.",
      "id": "FR-28",
      "priority": "SHOULD",
      "title": "Access to submission logs"
    },
    {
      "description": "The system SHOULD return a unique job ID as a confirmation response after a job is successfully pushed via the API, enabling accurate record-keeping and integration synchronization for external systems.",
      "id": "FR-29",
      "priority": "SHOULD",
      "title": "Unique job ID confirmation response"
    },
    {
      "description": "The system SHALL automatically tag each job post with the name of the source platform (e.g., “Source: samplejobsite.ps”) and include a backlink to the original job advertisement.",
      "id": "FR-30",
      "priority": "MUST",
      "title": "Automatic source platform tagging and backlinking"
    },
    {
      "description": "The system SHOULD support job synchronization of updates via the API, enabling external job sites to modify job details—such as deadline extensions, description edits, or early closure/deletion/deactivation—using the assigned job ID.",
      "id": "FR-31",
      "priority": "SHOULD",
      "title": "Job synchronization of updates via API"
    },
    {
      "description": "The system SHOULD provide an optional sync dashboard—a lightweight web interface or endpoint—that allows partners to review the status of jobs posted via the API, including indicators for synced, failed, pending, and archived records.",
      "id": "FR-32",
      "priority": "SHOULD",
      "title": "Optional sync dashboard"
    },
    {
      "description": "The system SHOULD also offer periodic or real-time access to integration usage statistics—such as the number of jobs submitted, matched, and viewed—for transparency, performance tracking, and reporting purposes.",
      "id": "FR-33",
      "priority": "SHOULD",
      "title": "Integration usage statistics access"
    },
    {
      "description": "The system SHOULD provide access to the up-to-date API schema (e.g., via Swagger) and detailed field validation rules to ensure proper formatting and structure of job postings submitted through the API.",
      "id": "FR-34",
      "priority": "SHOULD",
      "title": "Access to API schema and validation rules"
    },
    {
      "description": "The system SHOULD provide an option for source platforms to configure whether their attribution (e.g., source platform name) appears publicly on job postings or is only visible within the admin panel and system logs.",
      "id": "FR-35",
      "priority": "SHOULD",
      "title": "Attribution visibility configuration"
    },
    {
      "description": "The system SHOULD maintain an audit trail at the job level, recording which external job site created or modified each posting, and display this information within the MoL admin dashboard for traceability and accountability.",
      "id": "FR-36",
      "priority": "SHOULD",
      "title": "Job-level audit trail"
    },
    {
      "description": "The system SHALL provide a comprehensive user management interface for administrators.",
      "id": "FR-37",
      "priority": "MUST",
      "title": "comprehensive user management interface for administrators"
    },
    {
      "description": "The system SHALL allow authorized administrators to add and manage core entities on the platform, including job seekers, employers, and job offerings (opportunities).",
      "id": "FR-38",
      "priority": "MUST",
      "title": "add and manage core entities on the platform"
    },
    {
      "description": "The system SHALL provide user management capabilities for administrators, including the ability to view, approve, ban, or deactivate user accounts, reset account credentials, and monitor account statuses.",
      "id": "FR-39",
      "priority": "MUST",
      "title": "user management capabilities for administrators"
    },
    {
      "description": "The system SHALL provide tools for administrators to assist users with account recovery and technical issues, view pending employer registrations and approve them based on submitted profile information.",
      "id": "FR-40",
      "priority": "MUST",
      "title": "tools for administrators to assist users and approve employer registrations"
    },
    {
      "description": "The system SHALL maintain an audit log of all administrative actions for security and accountability.",
      "id": "FR-41",
      "priority": "MUST",
      "title": "audit log of all administrative actions"
    },
    {
      "description": "The system SHALL allow authorized administrators to define and update system settings if needed.",
      "id": "FR-42",
      "priority": "MUST",
      "title": "define and update system settings"
    },
    {
      "description": "The system SHALL allow authorized administrators to view and manage static reference files, including skills, jobs, trainings, and other related datasets.",
      "id": "FR-43",
      "priority": "MUST",
      "title": "view and manage static reference files"
    },
    {
      "description": "The system SHALL allow authorized administrators to manage system taxonomies such as the skills list, occupations catalog, training programs, and other platform constants or reference values.",
      "id": "FR-44",
      "priority": "MUST",
      "title": "manage system taxonomies"
    },
    {
      "description": "The system SHALL allow administrators to oversee job offerings by viewing active and inactive postings, changes in posts, and to suspend or remove job offerings that are deemed inappropriate or violate platform policies.",
      "id": "FR-45",
      "priority": "MUST",
      "title": "oversee job offerings"
    },
    {
      "description": "The system SHALL provide comprehensive statistics and reporting features, allowing administrators to download reports on job postings by sector, region, or industry; user registrations; top searches from both job seekers and employers; user interactions with job offers; and overall system metrics.",
      "id": "FR-46",
      "priority": "MUST",
      "title": "comprehensive statistics and reporting features"
    },
    {
      "description": "The system SHALL implement secure authentication mechanisms including username/password, email verification, and multi-factor authentication options.",
      "id": "FR-49",
      "priority": "MUST",
      "title": "secure authentication mechanisms"
    },
    {
      "description": "The system SHALL enforce strong password policies with configurable parameters.",
      "id": "FR-50",
      "priority": "MUST",
      "title": "strong password policies"
    },
    {
      "description": "The system SHALL implement role-based access control to restrict access to features and data based on user roles.",
      "id": "FR-51",
      "priority": "MUST",
      "title": "role-based access control"
    },
    {
      "description": "The system SHALL provide session management with configurable timeout settings.",
      "id": "FR-52",
      "priority": "MUST",
      "title": "session management"
    },
    {
      "description": "The system SHALL maintain detailed access logs for security monitoring and auditing.",
      "id": "FR-53",
      "priority": "MUST",
      "title": "detailed access logs"
    },
    {
      "description": "The system SHALL provide a structured job posting form for employers to create job listings.",
      "id": "FR-54",
      "priority": "MUST",
      "title": "Structured job posting form"
    },
    {
      "description": "The system SHALL provide a structured job posting form that allows employers to add new job opportunities with the following fields: - Job title, summary, and required skills (with support for file upload or copy/paste input) - Contract type (e.g., full-time, part-time, training, project-based) - Required education level - Application deadline with an optional auto-close feature - Work format selection (Physical with employment location, Online, or Hybrid) - Gender, number of employees, etc - Required languages and proficiency levels - Link to the job if available. - More detailed features on the job post to be provided.",
      "id": "FR-55",
      "priority": "MUST",
      "title": "Job posting form fields"
    },
    {
      "description": "The system SHALL support standardized job categories, skills, and qualifications to facilitate accurate matching. For this requirement, the system SHALL ensure that all input data complies with the Schema.org JobPosting standard for semantic compatibility and structured data integrity.",
      "id": "FR-56",
      "priority": "MUST",
      "title": "Standardized job categories and Schema.org compliance"
    },
    {
      "description": "The system SHALL allow employers to manage their job postings by editing job details, extending application deadlines, and set job posting visibility (public, private, or targeted) posts when necessary.",
      "id": "FR-57",
      "priority": "MUST",
      "title": "Job posting management"
    },
    {
      "description": "The system SHALL support job posting expiration and renewal processes.",
      "id": "FR-58",
      "priority": "MUST",
      "title": "Job posting expiration and renewal"
    },
    {
      "description": "The system SHALL provide a comprehensive search interface for job seekers to find relevant opportunities.",
      "id": "FR-59",
      "priority": "MUST",
      "title": "Comprehensive search interface"
    },
    {
      "description": "The search interface SHALL support both basic (search by single keyword) and advanced search modes based on employer-defined attributes.",
      "id": "FR-60",
      "priority": "MUST",
      "title": "Basic and advanced search modes"
    },
    {
      "description": "The system SHALL provide semantic search capabilities that understand the intent behind search queries.",
      "id": "FR-61",
      "priority": "MUST",
      "title": "Semantic search capabilities"
    },
    {
      "description": "The system SHALL provide a search engine with advanced filtering capabilities, allowing job seekers to search for jobs using the following criteria: - Keywords (text) - Location - Salary range - Employment type - Date posted - Application deadline - Job-specific requirements (e.g., skills, education, training, years of experience) - Company sector/industry (e.g., IT, Health, NGO, Construction)",
      "id": "FR-62",
      "priority": "MUST",
      "title": "Advanced filtering capabilities"
    },
    {
      "description": "The system SHALL display search results with relevance/skills-matching ranking and sorting options. In addition, when user login the system SHALL display recommended jobs based on results generated by AI matching engine.",
      "id": "FR-63",
      "priority": "MUST",
      "title": "Search results ranking and AI recommendations"
    },
    {
      "description": "The system SHALL also include a favorites feature (e.g., heart button ) for users to save jobs of interest.",
      "id": "FR-64",
      "priority": "MUST",
      "title": "Favorites feature"
    },
    {
      "description": "The system SHALL support saved searches with notification options for new matching jobs.",
      "id": "FR-65",
      "priority": "MUST",
      "title": "Saved searches and notifications"
    },
    {
      "description": "The system SHALL allow job seekers to bookmark and save jobs by adding them to an “Interested List ”, and to save custom search filters for future use.",
      "id": "FR-66",
      "priority": "MUST",
      "title": "Bookmark and save jobs"
    },
    {
      "description": "The system SHALL provide employers with tools to manage the status of job postings.",
      "id": "FR-67",
      "priority": "MUST",
      "title": "Job posting status management tools"
    },
    {
      "description": "The system SHALL support the following job posting statuses: draft, active, paused, expired, and archived.",
      "id": "FR-68",
      "priority": "MUST",
      "title": "Job posting statuses"
    },
    {
      "description": "The system SHALL maintain a history of status changes for audit and reporting purposes.",
      "id": "FR-69",
      "priority": "MUST",
      "title": "Status change history"
    },
    {
      "description": "The system SHALL implement AI-driven matching algorithms to connect job seekers with relevant job opportunities.",
      "id": "FR-70",
      "priority": "MUST",
      "title": "AI-driven matching algorithms"
    },
    {
      "description": "The system SHALL use a scoring algorithm to calculate a match score between job seekers and job postings minimally based on the following criteria: - Skill overlap - Education match - Training match - Location match - Experience range - Salary expectation range",
      "id": "FR-71",
      "priority": "MUST",
      "title": "Scoring algorithm"
    },
    {
      "description": "The system SHALL generate shortlists of top-matching candidates (e.g., top 100) for each job posting to assist employers in the selection process.",
      "id": "FR-72",
      "priority": "MUST",
      "title": "Shortlists of top-matching candidates"
    },
    {
      "description": "The system SHALL use natural language processing (NLP) to understand the semantic meaning of job descriptions and resumes beyond keyword matching.",
      "id": "FR-73",
      "priority": "MUST",
      "title": "Natural language processing (NLP)"
    },
    {
      "description": "The system SHALL perform keyword and semantic analysis on posted job descriptions to identify key attributes such as required skills, experience levels, and job categories.",
      "id": "FR-74",
      "priority": "MUST",
      "title": "Keyword and semantic analysis"
    },
    {
      "description": "The system SHALL allow administrators to define and adjust a minimum match threshold (e.g., 60%) that determines which job matches are displayed to users.",
      "id": "FR-75",
      "priority": "MUST",
      "title": "Minimum match threshold"
    },
    {
      "description": "The system SHALL rank/order job postings for each job seeker based on their individual match percentage, displaying the most relevant opportunities first.",
      "id": "FR-76",
      "priority": "MUST",
      "title": "Rank/order job postings"
    },
    {
      "description": "The system SHALL support two-way matching, where job seekers receive ranked job opportunities based on match percentage, and employers receive reverse matches with ranked lists of suitable job seekers for their postings.",
      "id": "FR-77",
      "priority": "MUST",
      "title": "Two-way matching"
    },
    {
      "description": "The system SHALL allow configuration of matching parameters to adjust the importance of different factors.",
      "id": "FR-78",
      "priority": "MUST",
      "title": "Configuration of matching parameters"
    },
    {
      "description": "The system SHALL implement AI-powered resume parsing to extract structured information from uploaded documents.",
      "id": "FR-79",
      "priority": "MUST",
      "title": "AI-powered resume parsing"
    },
    {
      "description": "The system SHALL extract the following information from resumes: personal details, contact information, education history, work experience, skills, certifications, and achievements.",
      "id": "FR-80",
      "priority": "MUST",
      "title": "Information extraction from resumes"
    },
    {
      "description": "The system SHALL support multiple languages in resume parsing, with primary focus on Arabic and English.",
      "id": "FR-81",
      "priority": "MUST",
      "title": "Multiple languages in resume parsing"
    },
    {
      "description": "The system SHALL identify and standardize skills mentioned in resumes to facilitate matching.",
      "id": "FR-82",
      "priority": "MUST",
      "title": "Standardize skills"
    },
    {
      "description": "The system SHALL provide confidence scores for extracted information and highlight areas that may need manual verification.",
      "id": "FR-83",
      "priority": "MUST",
      "title": "Confidence scores for extracted information"
    },
    {
      "description": "The system SHALL allow job seekers to review and correct parsed information.",
      "id": "FR-84",
      "priority": "MUST",
      "title": "Review and correct parsed information"
    },
    {
      "description": "The system SHALL provide personalized job recommendations for job seekers based on their profile, preferences, and platform activity.",
      "id": "FR-85",
      "priority": "MUST",
      "title": "Personalized job recommendations"
    },
    {
      "description": "The system SHALL recommend suitable job seekers to employers based on job requirements and matching criteria.",
      "id": "FR-86",
      "priority": "MUST",
      "title": "Recommend suitable job seekers"
    },
    {
      "description": "The system SHALL use collaborative filtering to recommend jobs based on similar user behaviors and preferences.",
      "id": "FR-87",
      "priority": "MUST",
      "title": "Collaborative filtering"
    },
    {
      "description": "The system SHALL incorporate content-based filtering to recommend jobs similar to those the user has shown interest in.",
      "id": "FR-88",
      "priority": "MUST",
      "title": "Content-based filtering"
    },
    {
      "description": "The system SHALL consider location, salary expectations, and work arrangement preferences in recommendations.",
      "id": "FR-89",
      "priority": "MUST",
      "title": "Recommendation considerations"
    },
    {
      "description": "The system SHALL provide employers with candidate recommendations for their job postings.",
      "id": "FR-90",
      "priority": "MUST",
      "title": "Candidate recommendations for employers"
    },
    {
      "description": "The system SHALL rank candidates based on match quality, highlighting the strengths and potential gaps of each candidate.",
      "id": "FR-91",
      "priority": "MUST",
      "title": "Rank candidates based on match quality"
    },
    {
      "description": "The system SHALL allow employers to set minimum qualification thresholds for automatic candidate filtering.",
      "id": "FR-92",
      "priority": "MUST",
      "title": "Minimum qualification thresholds for filtering"
    },
    {
      "description": "The system SHALL allow employers to search the candidate database using advanced filtering options.",
      "id": "FR-93",
      "priority": "MUST",
      "title": "Advanced filtering for candidate search"
    },
    {
      "description": "The system SHALL respect candidate privacy settings when making recommendations to employers.",
      "id": "FR-94",
      "priority": "MUST",
      "title": "Respect candidate privacy settings"
    },
    {
      "description": "The system SHALL provide insights on candidate availability, salary expectations, and potential fit.",
      "id": "FR-95",
      "priority": "MUST",
      "title": "Candidate insights"
    },
    {
      "description": "The system SHALL allow employers to save promising candidates to talent pools for future opportunities (add to shortlist).",
      "id": "FR-96",
      "priority": "MUST",
      "title": "Save candidates to talent pools"
    },
    {
      "description": "The system SHALL support integration with external job sites based on recommendations by MoL and PEF.",
      "id": "FR-97",
      "priority": "MUST",
      "title": "External job site integration support"
    },
    {
      "description": "The system SHOULD provide APIs for real-time job data synchronization with external job sites.",
      "id": "FR-98",
      "priority": "SHOULD",
      "title": "APIs for real-time job data synchronization"
    },
    {
      "description": "The system SHOULD implement data mapping and transformation to standardize job postings from different sources.",
      "id": "FR-99",
      "priority": "SHOULD",
      "title": "Data mapping and transformation for standardization"
    },
    {
      "description": "The system SHOULD support both pull (importing jobs from external sites) and push (exporting jobs to external sites) integration models.",
      "id": "FR-100",
      "priority": "SHOULD",
      "title": "Pull and push integration models"
    },
    {
      "description": "The system SHOULD maintain synchronization logs and provide error handling for failed integrations.",
      "id": "FR-101",
      "priority": "SHOULD",
      "title": "Synchronization logs and error handling"
    },
    {
      "description": "The system SHOULD support scheduled and on-demand synchronization options.",
      "id": "FR-102",
      "priority": "SHOULD",
      "title": "Scheduled and on-demand synchronization"
    },
    {
      "description": "The system SHOULD provide a dashboard to monitor integration status and data flow with external job sites.",
      "id": "FR-103",
      "priority": "SHOULD",
      "title": "Integration monitoring dashboard"
    },
    {
      "description": "The system SHOULD integrate with relevant government databases for data verification and enrichment.",
      "id": "FR-104",
      "priority": "SHOULD",
      "title": "Government database integration for verification"
    },
    {
      "description": "The system SHOULD support integration with the MoL and PEF existing databases and systems.",
      "id": "FR-105",
      "priority": "SHOULD",
      "title": "MoL and PEF database integration"
    },
    {
      "description": "The system SHOULD support verification of educational credentials through integration with educational institution databases.",
      "id": "FR-106",
      "priority": "SHOULD",
      "title": "Educational credential verification"
    },
    {
      "description": "The system SHOULD provide options for identity verification through government ID systems.",
      "id": "FR-107",
      "priority": "SHOULD",
      "title": "Identity verification through government ID systems"
    },
    {
      "description": "The system SHOULD maintain audit trails of all data exchanges with government systems.",
      "id": "FR-108",
      "priority": "SHOULD",
      "title": "Audit trails for government data exchanges"
    },
    {
      "description": "The system SHOULD respect data privacy regulations when accessing and using government data.",
      "id": "FR-109",
      "priority": "SHOULD",
      "title": "Respect data privacy regulations for government data"
    },
    {
      "description": "The system SHOULD provide a comprehensive API framework for integration with external systems.",
      "id": "FR-110",
      "priority": "SHOULD",
      "title": "Comprehensive API framework"
    },
    {
      "description": "The system SHOULD implement RESTful APIs with JSON data format as the primary integration method.",
      "id": "FR-111",
      "priority": "SHOULD",
      "title": "RESTful APIs with JSON format"
    },
    {
      "description": "The system SHOULD provide detailed API documentation with examples and testing tools.",
      "id": "FR-112",
      "priority": "SHOULD",
      "title": "Detailed API documentation"
    },
    {
      "description": "The system SHOULD implement OAuth 2.0 for API authentication and authorization.",
      "id": "FR-113",
      "priority": "SHOULD",
      "title": "OAuth 2.0 for API authentication"
    },
    {
      "description": "The system SHOULD support API versioning to ensure backward compatibility.",
      "id": "FR-114",
      "priority": "SHOULD",
      "title": "API versioning for backward compatibility"
    },
    {
      "description": "The system SHALL track and record user activities for analysis and reporting.",
      "id": "FR-115",
      "priority": "MUST",
      "title": "Track and record user activities"
    },
    {
      "description": "The system SHALL monitor job seeker activities including profile views, job searches, applications, and interactions.",
      "id": "FR-116",
      "priority": "MUST",
      "title": "Monitor job seeker activities"
    },
    {
      "description": "The system SHALL TRACK employer activities including job postings, candidate searches.",
      "id": "FR-117",
      "priority": "MUST",
      "title": "Track employer activities"
    },
    {
      "description": "The system SHALL implement data retention policies for activity logs in compliance with regulations.",
      "id": "FR-118",
      "priority": "MUST",
      "title": "Data retention policies for activity logs"
    },
    {
      "description": "MOL Life dashboard should include current logins, number of current logins and last sessions, with links to these users profiles",
      "id": "FR-119",
      "priority": "SHOULD",
      "title": "MOL Life dashboard user session details"
    },
    {
      "description": "The system SHOULD generate employment statistics and labor market insights from platform data.",
      "id": "FR-120",
      "priority": "SHOULD",
      "title": "generate employment statistics and labor market insights from platform data"
    },
    {
      "description": "The system SHOULD track key metrics including job posting trends, application rates, hiring rates, and time-to-fill.",
      "id": "FR-121",
      "priority": "SHOULD",
      "title": "track key metrics including job posting trends, application rates, hiring rates, and time-to-fill"
    },
    {
      "description": "The system SHOULD provide industry-specific analytics on job market demand and supply.",
      "id": "FR-122",
      "priority": "SHOULD",
      "title": "provide industry-specific analytics on job market demand and supply"
    },
    {
      "description": "The system SHOULD analyze skill demand trends to identify emerging requirements and skill gaps.",
      "id": "FR-123",
      "priority": "SHOULD",
      "title": "analyze skill demand trends to identify emerging requirements and skill gaps"
    },
    {
      "description": "The system SHOULD generate geographic distribution reports for jobs and candidates.",
      "id": "FR-124",
      "priority": "SHOULD",
      "title": "generate geographic distribution reports for jobs and candidates"
    },
    {
      "description": "The system SHOULD provide salary range analytics by industry, position, and location.",
      "id": "FR-125",
      "priority": "SHOULD",
      "title": "provide salary range analytics by industry, position, and location"
    },
    {
      "description": "The system SHOULD track employment outcomes and career progression where data is available.",
      "id": "FR-126",
      "priority": "SHOULD",
      "title": "track employment outcomes and career progression where data is available"
    },
    {
      "description": "The system SHOULD generate periodic labor market reports for government stakeholders.",
      "id": "FR-127",
      "priority": "SHOULD",
      "title": "generate periodic labor market reports for government stakeholders"
    },
    {
      "description": "The system SHOULD monitor and report on system performance metrics.",
      "id": "FR-128",
      "priority": "SHOULD",
      "title": "monitor and report on system performance metrics"
    },
    {
      "description": "The system SHOULD track matching algorithm performance including accuracy, precision, recall, and user satisfaction.",
      "id": "FR-129",
      "priority": "SHOULD",
      "title": "track matching algorithm performance including accuracy, precision, recall, and user satisfaction"
    },
    {
      "description": "The system SHOULD monitor system usage patterns including peak times, popular features, and user engagement.",
      "id": "FR-130",
      "priority": "SHOULD",
      "title": "monitor system usage patterns including peak times, popular features, and user engagement"
    },
    {
      "description": "The system SHOULD track technical performance metrics including response times, resource utilization, and error rates.",
      "id": "FR-131",
      "priority": "SHOULD",
      "title": "track technical performance metrics including response times, resource utilization, and error rates"
    },
    {
      "description": "The system SHOULD provide dashboards for administrators to monitor system health and performance.",
      "id": "FR-132",
      "priority": "SHOULD",
      "title": "provide dashboards for administrators to monitor system health and performance"
    },
    {
      "description": "The system SHOULD generate alerts for performance issues or anomalies.",
      "id": "FR-133",
      "priority": "SHOULD",
      "title": "generate alerts for performance issues or anomalies"
    },
    {
      "description": "The system SHOULD maintain historical performance data for trend analysis and capacity planning.",
      "id": "FR-134",
      "priority": "SHOULD",
      "title": "maintain historical performance data for trend analysis and capacity planning"
    },
    {
      "description": "The system SHOULD provide a flexible reporting framework for generating custom reports through seamless integration with existing and available reporting tools such as Microsoft Power BI.",
      "id": "FR-135",
      "priority": "SHOULD",
      "title": "provide a flexible reporting framework for generating custom reports through seamless integration with existing and available reporting tools such as Microsoft Power BI"
    },
    {
      "description": "The system SHOULD allow administrators to define report templates with configurable parameters.",
      "id": "FR-136",
      "priority": "SHOULD",
      "title": "allow administrators to define report templates with configurable parameters"
    },
    {
      "description": "The system SHOULD support various report formats including tabular data, charts, and visualizations.",
      "id": "FR-137",
      "priority": "SHOULD",
      "title": "support various report formats including tabular data, charts, and visualizations"
    },
    {
      "description": "The system SHOULD allow scheduling of recurring reports with automated distribution.",
      "id": "FR-138",
      "priority": "SHOULD",
      "title": "allow scheduling of recurring reports with automated distribution"
    },
    {
      "description": "The system SHOULD support export of reports in common formats (PDF, Excel, CSV).",
      "id": "FR-139",
      "priority": "SHOULD",
      "title": "support export of reports in common formats (PDF, Excel, CSV)"
    },
    {
      "description": "The system SHOULD provide a report builder interface for users with appropriate permissions.",
      "id": "FR-140",
      "priority": "SHOULD",
      "title": "provide a report builder interface for users with appropriate permissions"
    },
    {
      "description": "The system SHOULD maintain a library of saved reports for quick access.",
      "id": "FR-141",
      "priority": "SHOULD",
      "title": "maintain a library of saved reports for quick access"
    },
    {
      "description": "The system SHOULD implement access controls to ensure users can only view reports appropriate to their role.",
      "id": "FR-142",
      "priority": "SHOULD",
      "title": "implement access controls to ensure users can only view reports appropriate to their role"
    },
    {
      "description": "The system SHALL send email notifications for important events and updates.",
      "id": "FR-143",
      "priority": "MUST",
      "title": "send email notifications for important events and updates"
    },
    {
      "description": "The system SHALL support customizable email templates with dynamic content.",
      "id": "FR-144",
      "priority": "MUST",
      "title": "support customizable email templates with dynamic content"
    },
    {
      "description": "The system SHALL allow users to configure their email notification preferences.",
      "id": "FR-145",
      "priority": "MUST",
      "title": "allow users to configure their email notification preferences"
    },
    {
      "description": "The system SHALL support both immediate and digest email notifications.",
      "id": "FR-146",
      "priority": "MUST",
      "title": "support both immediate and digest email notifications"
    },
    {
      "description": "The system SHALL log all emails notifications.",
      "id": "FR-147",
      "priority": "MUST",
      "title": "log all emails notifications"
    },
    {
      "description": "The system SHALL comply with anti-spam regulations and best practices.",
      "id": "FR-148",
      "priority": "MUST",
      "title": "comply with anti-spam regulations and best practices"
    },
    {
      "description": "The system SHALL provide an in-app notification center for users.",
      "id": "FR-149",
      "priority": "MUST",
      "title": "In-app notification center"
    },
    {
      "description": "The system SHALL display real-time notifications for important events and updates.",
      "id": "FR-150",
      "priority": "MUST",
      "title": "Real-time notifications"
    },
    {
      "description": "The system SHALL provide weekly job recommendations to job seekers based on their search history and profile information.",
      "id": "FR-151",
      "priority": "MUST",
      "title": "Weekly job recommendations"
    },
    {
      "description": "The system SHALL maintain a notification history for users to review past notifications.",
      "id": "FR-152",
      "priority": "MUST",
      "title": "Notification history"
    },
    {
      "description": "The system SHALL allow users to configure their in-app notification preferences.",
      "id": "FR-153",
      "priority": "MUST",
      "title": "In-app notification preferences"
    },
    {
      "description": "The system SHALL support different notification types with appropriate visual indicators.",
      "id": "FR-154",
      "priority": "MUST",
      "title": "Notification types and visual indicators"
    },
    {
      "description": "The system SHALL provide notification management tools for users to mark as read, delete, or take action on notifications.",
      "id": "FR-155",
      "priority": "MUST",
      "title": "Notification management tools"
    },
    {
      "description": "The system SHALL provide SMS notifications for critical updates and time- sensitive information (byt the integration with SMS service providers (gateway)). Such as welcoming SMS with a code for user registration, employer registration, and SMS for resetting the password.",
      "id": "FR-156",
      "priority": "MUST",
      "title": "SMS notifications"
    },
    {
      "description": "The system SHALL allow users to opt-in to SMS notifications and provide their mobile number.",
      "id": "FR-157",
      "priority": "MUST",
      "title": "SMS opt-in"
    },
    {
      "description": "The system SHALL limit SMS notifications to essential communications to avoid overwhelming users.",
      "id": "FR-158",
      "priority": "MUST",
      "title": "Limit SMS notifications"
    },
    {
      "description": "The system SHALL track SMS delivery status for monitoring and troubleshooting. + loging as sms messages",
      "id": "FR-159",
      "priority": "MUST",
      "title": "SMS delivery status tracking"
    },
    {
      "description": "The system SHALL comply with telecommunications regulations regarding SMS messaging.",
      "id": "FR-160",
      "priority": "MUST",
      "title": "SMS telecommunications compliance"
    },
    {
      "description": "The system SHALL provide a content management system (CMS) for publishing news and updates.",
      "id": "FR-161",
      "priority": "MUST",
      "title": "Content management system (CMS)"
    },
    {
      "description": "The system SHALL allow administrators to create, edit, and publish articles and announcements.",
      "id": "FR-162",
      "priority": "MUST",
      "title": "Admin content management"
    },
    {
      "description": "The system SHALL support rich text formatting, images, and embedded media in content.",
      "id": "FR-163",
      "priority": "MUST",
      "title": "Rich text and media support"
    },
    {
      "description": "The system SHALL provide content categorization and tagging for organization.",
      "id": "FR-164",
      "priority": "MUST",
      "title": "Content categorization and tagging"
    },
    {
      "description": "The system SHALL display relevant news and updates on user dashboards based on their profile.",
      "id": "FR-165",
      "priority": "MUST",
      "title": "Profile-based news display"
    },
    {
      "description": "The system SHALL maintain an archive of past news and updates with search functionality.",
      "id": "FR-166",
      "priority": "MUST",
      "title": "News and updates archive"
    },
    {
      "description": "The system SHALL provide a comprehensive FAQ and help center. In addition, list of laws, regulations and contract types regulations.",
      "id": "FR-167",
      "priority": "MUST",
      "title": "FAQ and help center"
    },
    {
      "description": "The system SHALL organize help content by topic and user role for easy navigation.",
      "id": "FR-168",
      "priority": "MUST",
      "title": "Help content organization"
    },
    {
      "description": "The system SHALL implement a search function for help content.",
      "id": "FR-169",
      "priority": "MUST",
      "title": "Help content search"
    },
    {
      "description": "The system SHALL provide context-sensitive help throughout the platform.",
      "id": "FR-170",
      "priority": "MUST",
      "title": "Context-sensitive help"
    },
    {
      "description": "The system SHALL allow administrators to update help content as the system evolves.",
      "id": "FR-171",
      "priority": "MUST",
      "title": "Admin help content updates"
    },
    {
      "description": "The system SHALL collect user feedback on help content effectiveness.",
      "id": "FR-172",
      "priority": "MUST",
      "title": "Help content feedback"
    },
    {
      "description": "The system SHALL provide guided tours and tutorials for new users.",
      "id": "FR-173",
      "priority": "MUST",
      "title": "Guided tours and tutorials"
    },
    {
      "description": "The system SHALL support multimedia help content including videos and interactive guides.",
      "id": "FR-174",
      "priority": "MUST",
      "title": "Multimedia help content"
    },
    {
      "description": "The system shall provide user interfaces for the following user types: 1) Job Seeker - Registration and profile management interface - Job search and application interface - Dashboard for tracking applications and recommendations - Notification and messaging interface 2) Employers - Registration and company profile management interface - Job posting and management interface - Candidate search and evaluation interface - Recruitment workflow management interface 3) External Job Sites - Integration configuration interface - Data mapping and synchronization interface - Monitoring and reporting interface 4) Administrators - User\\roles\\permissions management interface - System configuration interface - Content management interface Reporting and analytics interface",
      "id": "The system shall provide user interfaces for the following user types",
      "priority": "MUST",
      "title": "User interfaces for user types"
    },
    {
      "description": "The system SHALL allow unregistered (guest) users to browse available job listings using basic filters such as location, sector, and date posted.",
      "id": "The system SHALL allow unregistered (guest) users to browse available job listings",
      "priority": "MUST",
      "title": "Guest user browsing"
    },
    {
      "description": "The system SHALL prompt guest users to register or log in when they attempt to apply for a job, save listings, or subscribe to notifications.",
      "id": "The system SHALL prompt guest users to register or log in",
      "priority": "MUST",
      "title": "Guest user registration prompt"
    },
    {
      "description": "The system SHALL ensure that privacy policies and cookie consent banners are clear, guest- friendly, and fully compliant with GDPR and applicable local data protection laws, providing transparency in data collection and usage.",
      "id": "The system SHALL ensure that privacy policies and cookie consent banners are clear",
      "priority": "MUST",
      "title": "Privacy and cookie compliance"
    },
    {
      "description": "The system SHALL have a user-friendly UX/UI dynamic interface that showcases the latest job postings, featured opportunities, and relevant sector-based news or career advice, all presented in a visually engaging and user-friendly layout - Responsive design for desktop and mobile devices - Multilingual support (Arabic and English) and different AI functions and techniques for both Arab and English to be utilized - Implement Web Content Accessibility Guidelines (WCAG 2.1 or later) to ensure accessibility and inclusivity for users with disabilities, including support for screen readers, appropriate color contrast, and keyboard navigation. - Consistent navigation and design patterns - Display dynamic homepage content, including the latest job postings, featured opportunities, and relevant sector-based news or career advice, presented in an engaging and easy-to-navigate layout. - Context-sensitive help and guidance - All public pages must be SEO-optimized",
      "id": "The system SHALL have a user-friendly UX/UI dynamic interface",
      "priority": "MUST",
      "title": "UX/UI dynamic interface requirements"
    },
    {
      "description": "The system shall support the migration of existing data from MoL and PEF systems into the new platform. This includes: 1) Data Mapping and Transformation - Mapping of existing data structures to new system schema - Transformation of data to meet new system requirements - Validation of migrated data for accuracy and completeness 2) Migration Process - Phased migration approach to minimize disruption - Testing procedures for migrated data - Rollback procedures in case of migration issues 3) Data Cleansing - Identification and resolution of data quality issues - Deduplication of records - Standardization of data formats",
      "id": "The system shall support the migration of existing data from MoL and PEF systems",
      "priority": "MUST",
      "title": "Data migration from MoL and PEF systems"
    },
    {
      "description": "The system shall include provisions for training different user groups: 1) Administrator Training - System configuration and management - User administration - Security management - Troubleshooting and support 2) End-User Training - Job seeker training materials - Employer training materials - External job site integration training - Self-service training resources 3) Training Delivery - Online training modules - In-person training sessions - Train-the-trainer programs - Ongoing training for system updates",
      "id": "The system shall include provisions for training different user groups",
      "priority": "MUST",
      "title": "Training provisions for user groups"
    }
  ]
}
```
