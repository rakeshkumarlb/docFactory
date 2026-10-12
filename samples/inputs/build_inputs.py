"""Generates a set of invented "as built" documents for the AI-Driven Job Matching Platform: architecture, hosting, deployment, operations, support.

Run once (`python samples/inputs/build_inputs.py`); the outputs in `samples/inputs/AI-Driven-Job-Matching-Platform/` are committed. Needs reportlab and
python-docx (dev only). The real SRS in `bundle/` describes the application before it was built; these documents describe an imaginary finished
system so that ingestion, extraction and generation can be run against a realistic spread of formats (PDF, Word, HTML, Markdown).

Everything here is FICTIONAL test input, never knowledge: hosts end in `.example`, people and contacts are roles, figures are invented.
Each document block is rendered by the writer of its format; a block is ("h1", text), ("h2", text), ("p", text), ("bullets", [text]),
("steps", [text]) or ("table", header, rows).
"""
import html
from pathlib import Path

from docx import Document
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).parent / "AI-Driven-Job-Matching-Platform"
APP = "AI-Driven Job Matching Platform"
NOTE = "Sample document, fictional content created to test docFactory"


def control(doc_id: str, version: str, date: str, owner: str, with_title: bool = True) -> list:
    rows = [["Title", APP]] if with_title else []
    rows += [["Document ID", doc_id], ["Version", version], ["Status", "Approved"], ["Owner", owner], ["Date", date], ["Classification", NOTE]]
    return [("table", ["Field", "Value"], rows)]


# --------------------------------------------------------------------------------------------------------------------------------- writers
def pdf(path: Path, title: str, blocks: list) -> None:
    styles = getSampleStyleSheet()
    cell = styles["BodyText"].clone("cell", fontSize=8, leading=10)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 10)]
    for block in blocks:
        kind = block[0]
        if kind == "h1":
            story += [Spacer(1, 8), Paragraph(block[1], styles["Heading2"])]
        elif kind == "h2":
            story.append(Paragraph(block[1], styles["Heading3"]))
        elif kind == "p":
            story += [Paragraph(block[1], styles["BodyText"]), Spacer(1, 4)]
        elif kind in ("bullets", "steps"):
            story += [Paragraph(f"{'- ' if kind == 'bullets' else str(i) + '. '}{t}", styles["BodyText"]) for i, t in enumerate(block[1], 1)] + [Spacer(1, 4)]
        elif kind == "table":
            data = [[Paragraph(f"<b>{c}</b>", cell) for c in block[1]]] + [[Paragraph(str(c), cell) for c in row] for row in block[2]]
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story += [table, Spacer(1, 8)]
    SimpleDocTemplate(str(path), title=title, author="Platform Documentation Team (fictional)").build(story)


def word(path: Path, title: str, blocks: list) -> None:
    document = Document()
    document.core_properties.author = "Platform Documentation Team (fictional)"
    document.core_properties.title = title
    document.add_heading(title, 0)
    for block in blocks:
        kind = block[0]
        if kind == "h1":
            document.add_heading(block[1], 1)
        elif kind == "h2":
            document.add_heading(block[1], 2)
        elif kind == "p":
            document.add_paragraph(block[1])
        elif kind == "bullets":
            for text in block[1]:
                document.add_paragraph(text, style="List Bullet")
        elif kind == "steps":
            for text in block[1]:
                document.add_paragraph(text, style="List Number")
        elif kind == "table":
            table = document.add_table(rows=1, cols=len(block[1]))
            table.style = "Table Grid"
            for i, name in enumerate(block[1]):
                table.rows[0].cells[i].text = name
            for row in block[2]:
                cells = table.add_row().cells
                for i, value in enumerate(row):
                    cells[i].text = str(value)
    document.save(str(path))


def web(path: Path, title: str, blocks: list) -> None:
    out = [f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title>",
           "<meta name=\"author\" content=\"Platform Documentation Team (fictional)\"></head><body>", f"<h1>{html.escape(title)}</h1>"]
    for block in blocks:
        kind = block[0]
        if kind == "h1":
            out.append(f"<h2>{html.escape(block[1])}</h2>")
        elif kind == "h2":
            out.append(f"<h3>{html.escape(block[1])}</h3>")
        elif kind == "p":
            out.append(f"<p>{html.escape(block[1])}</p>")
        elif kind in ("bullets", "steps"):
            tag = "ul" if kind == "bullets" else "ol"
            out.append(f"<{tag}>" + "".join(f"<li>{html.escape(t)}</li>" for t in block[1]) + f"</{tag}>")
        elif kind == "table":
            head = "".join(f"<th>{html.escape(c)}</th>" for c in block[1])
            rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>" for row in block[2])
            out.append(f"<table border=\"1\"><tr>{head}</tr>{rows}</table>")
    out.append("</body></html>")
    path.write_text("\n".join(out), encoding="utf-8")


def markdown(path: Path, title: str, blocks: list) -> None:
    out = [f"# {title}", ""]
    for block in blocks:
        kind = block[0]
        if kind == "h1":
            out += [f"## {block[1]}", ""]
        elif kind == "h2":
            out += [f"### {block[1]}", ""]
        elif kind == "p":
            out += [block[1], ""]
        elif kind == "code":
            out += [f"```{block[1]}", block[2], "```", ""]
        elif kind == "bullets":
            out += [f"- {t}" for t in block[1]] + [""]
        elif kind == "steps":
            out += [f"{i}. {t}" for i, t in enumerate(block[1], 1)] + [""]
        elif kind == "table":
            out += ["| " + " | ".join(block[1]) + " |", "|" + "---|" * len(block[1])]
            out += ["| " + " | ".join(str(c).replace("|", "/") for c in row) + " |" for row in block[2]] + [""]
    path.write_text("\n".join(out), encoding="utf-8")


# ----------------------------------------------------------------------------------------------------------------------------- the documents
def product_overview() -> list:
    return control("JM-OVW-001", "1.3", "2026-09-30", "Product Owner") + [
        ("h1", "1. Executive Summary"),
        ("p", "The AI-Driven Job Matching Platform (JobMatch) is the national web service that connects job seekers with employers. It reads job seeker "
              "profiles and employer vacancies, ranks the best matches with a machine-learning model and lets both sides act on them. It went live on "
              "2026-03-15 and is in production (release 1.3.2)."),
        ("h1", "2. Purpose"),
        ("p", "JobMatch reduces the time unemployed job seekers need to find suitable vacancies and gives employers a ranked shortlist instead of a pile of "
              "applications. It replaces the manual matching done by employment office staff."),
        ("h1", "3. Business Overview"),
        ("p", "JobMatch is run for the Employment Services Directorate (a fictional unit) as part of the national Labour Market Information programme. "
              "It is funded for three years; the operating budget covers hosting, a small engineering team and a service desk."),
        ("table", ["Item", "Detail"], [
            ["Business owner", "Director, Employment Services Directorate"],
            ["Business criticality", "High (tier 2): matching and applications are unavailable if the platform is down, but employment offices can fall back to manual lists for up to two days"],
            ["Lifecycle status", "Production"],
            ["Go-live date", "2026-03-15"],
            ["Current release", "1.3.2"],
        ]),
        ("h1", "4. Target Users"),
        ("bullets", ["Job seekers (about 180,000 registered, 22,000 active monthly)", "Employers and recruitment agencies (about 2,400 verified accounts)",
                     "Employment office staff acting on behalf of job seekers", "Platform administrators and the service desk"]),
        ("h1", "5. Key Capabilities"),
        ("bullets", ["Job seeker registration with CV upload and automatic CV parsing", "Employer vacancy posting and shortlist review",
                     "AI-driven ranking of vacancies for job seekers and of candidates for vacancies", "Application tracking with e-mail and SMS notifications",
                     "Synchronisation of vacancies with the jobs.ps partner portal", "Reporting for the Directorate (placements, time to first match)"]),
        ("h1", "6. Out of Scope"),
        ("bullets", ["Payment of any kind; JobMatch never handles money", "Job interview scheduling and video calls",
                     "Training course management", "Mobile native apps; the responsive web application is the only client"]),
        ("h1", "7. Technology Summary"),
        ("p", "A React single-page application talks to Python (FastAPI) services running on Kubernetes in a private data centre. PostgreSQL stores the "
              "data, OpenSearch serves search and candidate retrieval, RabbitMQ carries asynchronous work. See the Solution Architecture Document."),
        ("h1", "8. Related Systems"),
        ("bullets", ["jobs.ps partner job portal (vacancy synchronisation)", "National Civil Registry (identity verification)",
                     "Labour Market Information System, LMIS (reporting exchange)", "SMS gateway and e-mail relay (notifications)"]),
    ]


def architecture() -> list:
    return control("JM-ARC-002", "2.1", "2026-09-18", "Chief Architect") + [
        ("h1", "1. Architecture Overview"),
        ("p", "JobMatch is an event-driven, service-oriented system. A single API gateway fronts a set of small Python services; long-running work "
              "(CV parsing, matching, notifications, partner synchronisation) is handled asynchronously through a message broker. Every service is "
              "stateless and runs as a container on Kubernetes. Architecture style: service-oriented, event-driven, deployed as containers on Kubernetes."),
        ("h1", "2. Technology Stack"),
        ("table", ["Layer", "Technology"], [
            ["Web client", "React 18, TypeScript, Vite"], ["Services", "Python 3.12, FastAPI, Celery workers"],
            ["Machine learning", "scikit-learn and sentence-transformers embeddings, served by the Matching Engine"],
            ["Relational data", "PostgreSQL 16"], ["Search", "OpenSearch 2.13"], ["Cache and sessions", "Redis 7"],
            ["Messaging", "RabbitMQ 3.13"], ["Object storage", "MinIO (S3 compatible)"], ["Identity", "Keycloak 24 (OpenID Connect)"],
            ["Platform", "Kubernetes 1.30, NGINX Ingress, Helm 3"], ["Infrastructure as code", "Terraform 1.8, Ansible 9"],
            ["CI/CD", "GitLab CI with a private container registry"], ["Observability", "Prometheus, Grafana, Loki, Alertmanager"],
        ]),
        ("h1", "3. Components"),
        ("table", ["Component", "Purpose", "Technology", "Owner", "Depends on"], [
            ["Web Frontend", "Single-page application for job seekers, employers and staff", "React 18, TypeScript", "Frontend Team", "API Gateway, Identity Service"],
            ["API Gateway", "Single entry point: routing, rate limiting, token validation", "NGINX Ingress, Kong", "Platform Team", "Identity Service"],
            ["Identity Service", "Sign-in, single sign-on, roles and token issuing", "Keycloak 24", "Platform Team", "PostgreSQL"],
            ["Profile Service", "Job seeker profiles, CV metadata and consent records", "Python 3.12, FastAPI", "Core Services Team", "PostgreSQL, MinIO, RabbitMQ"],
            ["Employer Service", "Employer accounts, vacancies and applications", "Python 3.12, FastAPI", "Core Services Team", "PostgreSQL, RabbitMQ"],
            ["Resume Parser", "Extracts skills and experience from uploaded CVs", "Python 3.12, Celery, spaCy", "Matching Team", "MinIO, RabbitMQ"],
            ["Matching Engine", "Computes and ranks matches between profiles and vacancies", "Python 3.12, scikit-learn, sentence-transformers", "Matching Team", "OpenSearch, PostgreSQL, Redis"],
            ["Notification Service", "Sends e-mail and SMS notifications", "Python 3.12, Celery", "Core Services Team", "RabbitMQ, SMS gateway, e-mail relay"],
            ["Partner Sync Service", "Synchronises vacancies with partner portals", "Python 3.12, Celery", "Integrations Team", "Employer Service, jobs.ps API, RabbitMQ"],
            ["Reporting Service", "Aggregates statistics and exports reports", "Python 3.12, pandas", "Data Team", "PostgreSQL"],
            ["Admin Console", "Back-office screens for staff and administrators", "React 18, TypeScript", "Frontend Team", "API Gateway"],
        ]),
        ("h1", "4. Data Stores"),
        ("table", ["Data store", "Type", "Technology", "Contents"], [
            ["Primary database", "Relational database", "PostgreSQL 16 (primary with two replicas)", "Profiles, vacancies, applications, consent records, audit schema"],
            ["Search index", "Search engine", "OpenSearch 2.13 (three nodes)", "Searchable vacancy and candidate documents with embeddings"],
            ["Session cache", "In-memory cache", "Redis 7 (sentinel)", "Sessions, rate-limit counters, match result cache"],
            ["Message broker", "Message queue", "RabbitMQ 3.13 (three-node cluster)", "Work queues for parsing, matching, notifications and sync"],
            ["Document store", "Object storage", "MinIO (erasure coded)", "Uploaded CV files and generated report exports"],
        ]),
        ("h1", "5. Integrations"),
        ("table", ["Integration", "Direction", "Protocol", "Purpose", "Data exchanged", "Authentication"], [
            ["jobs.ps partner portal", "Bidirectional", "REST over HTTPS, JSON", "Publish vacancies and read application status", "Vacancy records and status events", "OAuth 2.0 client credentials"],
            ["National Civil Registry", "Outbound", "SOAP over HTTPS", "Verify the national ID of a registering job seeker", "National ID number and date of birth; yes/no result", "Mutual TLS with a client certificate"],
            ["Labour Market Information System (LMIS)", "Outbound", "REST over HTTPS, JSON", "Monthly statistics exchange", "Aggregated placement figures, no personal data", "OAuth 2.0 client credentials"],
            ["SMS gateway", "Outbound", "REST over HTTPS", "Send SMS notifications", "Phone number and message text", "API key in the Authorization header"],
            ["E-mail relay", "Outbound", "SMTP over TLS", "Send e-mail notifications", "Recipient, subject and body", "SMTP authentication with a service account"],
            ["Skills taxonomy service", "Inbound", "REST over HTTPS, JSON", "Fetch the standard skills list used by the parser", "Skill names and codes", "API key"],
        ]),
        ("h1", "6. Security Architecture"),
        ("bullets", ["All traffic is encrypted with TLS 1.2 or higher; internal service traffic uses mutual TLS inside the cluster.",
                     "Personal data is encrypted at rest (database volumes, object storage).", "Access is role based and every change to a profile is written to the audit schema."]),
        ("h1", "7. Diagram Reference"),
        ("p", "The component diagram is stored in the documentation repository at docs/architecture/jobmatch-components-v2.1.drawio."),
    ]


def environments() -> list:
    return control("JM-ENV-003", "1.4", "2026-09-22", "Platform Team Lead") + [
        ("h1", "1. Environments"),
        ("p", "JobMatch runs in four environments plus a disaster-recovery site. Every environment is built from the same Terraform and Helm code; only the "
              "size and the configuration values differ."),
        ("table", ["Environment", "Purpose", "Hosting", "URL", "Access control"], [
            ["Development", "Daily work of the engineering teams; unstable by design", "Shared non-production cluster jm-nonprod, namespace dev", "https://dev.jobmatch.example", "Engineers through VPN and SSO group jm-dev"],
            ["Test", "Automated and manual QA of each merged change", "Shared non-production cluster jm-nonprod, namespace qa", "https://qa.jobmatch.example", "Engineers and QA through VPN and SSO group jm-qa"],
            ["Staging", "Pre-production rehearsal and user acceptance testing with production-like data volumes (anonymised)", "Dedicated cluster jm-stage in data centre DC1", "https://uat.jobmatch.example", "Engineers, QA and business testers through VPN; SSO group jm-uat"],
            ["Production", "Live service for job seekers and employers", "Cluster jm-prod in data centre DC1 (primary)", "https://www.jobmatch.example", "Public for users; operations access only for the on-call team through a bastion host with multi-factor authentication"],
            ["Disaster recovery", "Warm standby that takes over if DC1 is lost", "Cluster jm-dr in data centre DC2", "https://dr.jobmatch.example (inactive until failover)", "Operations team only"],
        ]),
        ("h1", "2. Environment Notes"),
        ("p", "Production data never leaves production. Staging is refreshed every Sunday from an anonymised copy of production; the anonymisation job is "
              "owned by the Data Team."),
    ]


def hosting_markdown() -> list:
    return control("JM-HST-004", "1.6", "2026-10-02", "Platform Team Lead") + [
        ("h1", "1. Hosting Overview"),
        ("p", "JobMatch is hosted in two private data centres, DC1 (primary) and DC2 (disaster recovery). The production cluster jm-prod has 3 control-plane "
              "nodes and 9 worker nodes (16 vCPU, 64 GB each). Nodes run Ubuntu 22.04 LTS and are patched monthly."),
        ("h1", "2. Infrastructure Configuration Files"),
        ("p", "The files below are the actual configuration kept in the repository jobmatch-infra (values trimmed to the relevant lines)."),
        ("h2", "2.1 Terraform: production cluster"),
        ("code", "hcl", 'module "jm_prod" {\n  source        = "./modules/k8s-cluster"\n  name          = "jm-prod"\n  datacenter    = "dc1"\n  control_nodes = 3\n  worker_nodes  = 9\n  worker_flavor = "c16-m64"\n  k8s_version   = "1.30.4"\n}'),
        ("h2", "2.2 NGINX Ingress configuration"),
        ("code", "nginx", 'server {\n  listen 443 ssl http2;\n  server_name www.jobmatch.example;\n  ssl_certificate     /etc/tls/jobmatch.crt;\n  ssl_certificate_key /etc/tls/jobmatch.key;\n  ssl_protocols TLSv1.2 TLSv1.3;\n  client_max_body_size 12m;   # CV uploads\n  location /api/ { proxy_pass http://api-gateway:8080; }\n  location /     { proxy_pass http://web-frontend:8080; }\n}'),
        ("h2", "2.3 Helm values: production"),
        ("code", "yaml", 'replicaCount:\n  apiGateway: 3\n  profileService: 4\n  matchingEngine: 6\n  notificationService: 2\nresources:\n  matchingEngine:\n    requests: { cpu: "2", memory: 8Gi }\n    limits:   { cpu: "4", memory: 12Gi }\npostgres:\n  host: pg-primary.jm-prod.svc\n  poolSize: 40\nrabbitmq:\n  host: rabbit.jm-prod.svc\n  prefetch: 20\nredis:\n  sentinel: redis-sentinel.jm-prod.svc:26379'),
        ("h2", "2.4 docker-compose for local development"),
        ("code", "yaml", 'services:\n  postgres:\n    image: postgres:16\n    environment: { POSTGRES_PASSWORD: dev-only-password }\n  opensearch:\n    image: opensearchproject/opensearch:2.13.0\n  rabbitmq:\n    image: rabbitmq:3.13-management\n  redis:\n    image: redis:7'),
        ("h1", "3. Network and Firewall"),
        ("table", ["Rule", "Source", "Destination", "Port"], [
            ["Public web traffic", "Internet", "Ingress load balancers", "443"], ["Operations access", "Bastion host", "Cluster API", "6443"],
            ["Database replication", "DC1 PostgreSQL", "DC2 PostgreSQL", "5432 (TLS)"], ["Partner calls", "Partner Sync Service", "jobs.ps API", "443"],
        ]),
        ("h1", "4. Capacity"),
        ("p", "Production is sized for 800 concurrent users and 60 requests per second. Autoscaling adds up to 4 Matching Engine replicas when CPU stays above 70 percent for five minutes."),
    ]


def deployment() -> list:
    return control("JM-DEP-005", "1.5", "2026-09-26", "Release Manager") + [
        ("h1", "1. Release Process"),
        ("p", "Every change goes through merge request review, an automated pipeline and a promotion path of Development, Test, Staging and Production. "
              "Production releases are approved by the Release Manager and the Product Owner in the weekly release meeting and are executed in the "
              "release window on Tuesdays from 22:00 to 00:00 local time."),
        ("steps", ["The engineer opens a merge request; two reviewers approve it.", "The pipeline builds the container images, runs unit and integration tests and a vulnerability scan.",
                   "Merged changes are deployed automatically to Development and then to Test.", "Release candidates are tagged and deployed to Staging every Thursday for acceptance testing.",
                   "After sign-off, the Release Manager starts the production deployment job, which runs a Helm upgrade with a rolling update.",
                   "The deployment engineer runs the smoke tests and watches the dashboards for 30 minutes."]),
        ("h1", "2. CI/CD Tooling"),
        ("p", "GitLab CI runs the pipelines on dedicated runners. Container images are stored in the private registry registry.jobmatch.example and signed. "
              "Helm 3 performs deployments; Terraform and Ansible build and configure the infrastructure."),
        ("h1", "3. Release Frequency"),
        ("p", "Minor releases every two weeks; patch releases whenever a defect needs an out-of-cycle fix, with an emergency path that needs only the Release Manager's approval."),
        ("h1", "4. Rollback Procedure"),
        ("p", "If the smoke tests fail or error rate alerts fire within the first hour, the deployment engineer runs helm rollback to the previous release. A rollback takes "
              "about 10 minutes. Database migrations are written backward compatible (expand and contract), so the previous version always works with the migrated schema. "
              "If a migration cannot be undone, the incident commander decides on restoring from backup."),
        ("h1", "5. Configuration Management"),
        ("p", "Helm values for each environment live in the Git repository jobmatch-config. Secrets are kept in HashiCorp Vault and injected at start-up; no secret is stored in Git. "
              "Configuration changes follow the same merge request and pipeline path as code."),
    ]


def monitoring() -> list:
    return control("JM-MON-006", "1.8", "2026-09-29", "Platform Team Lead") + [
        ("h1", "1. Monitoring Tools"),
        ("bullets", ["Prometheus with the blackbox exporter for metrics and uptime probes", "Grafana for dashboards", "Loki and Promtail for logs",
                     "Alertmanager for alert routing to the on-call pager (Opsgenie) and the Slack channel #jm-alerts", "Sentry for front-end and back-end exceptions"]),
        ("h1", "2. Key Metrics"),
        ("bullets", ["API request rate, error rate (5xx) and 95th percentile latency", "Matching job duration and queue depth", "Partner synchronisation lag in minutes",
                     "Database connection pool usage and replication lag", "Node CPU, memory and disk usage", "Backup job success"]),
        ("h1", "3. Alerting"),
        ("table", ["Alert", "Condition", "Severity", "Response action", "Notification channel"], [
            ["HighApiErrorRate", "More than 2 percent of API requests return 5xx for 5 minutes", "Critical", "Follow runbook RB-01; roll back the latest release if it started after a deployment", "Pager (Opsgenie) to the on-call engineer"],
            ["DatabaseConnectionsExhausted", "Connection pool above 90 percent for 5 minutes", "Critical", "Follow runbook RB-02; find and stop the runaway query", "Pager (Opsgenie) to the on-call engineer"],
            ["MatchQueueBacklog", "More than 5000 messages waiting in the matching queue for 10 minutes", "Warning", "Follow runbook RB-03; scale the Matching Engine workers", "Slack #jm-alerts"],
            ["SyncLagHigh", "Partner synchronisation lag above 30 minutes", "Warning", "Follow runbook RB-04; run the partner sync backfill procedure", "Slack #jm-alerts"],
            ["BackupFailed", "A nightly backup job did not finish successfully", "Critical", "Follow runbook RB-05; rerun the job and check storage", "Pager (Opsgenie) to the on-call engineer"],
            ["CertificateExpiry", "A TLS certificate expires in less than 14 days", "Warning", "Rotate the certificate with the SOP Rotate TLS Certificates", "Slack #jm-alerts"],
            ["DiskUsageHigh", "A node or volume is more than 85 percent full", "Warning", "Clean up or extend the volume", "Slack #jm-alerts"],
        ]),
        ("h1", "4. Dashboards"),
        ("bullets", ["API Overview: traffic, errors and latency per route", "Matching Pipeline: queue depth, job duration, model version", "Partner Sync: lag and failures per partner",
                     "Infrastructure: nodes, volumes, databases"]),
        ("h1", "5. Log Locations"),
        ("p", "Application logs are written as JSON to standard output and collected by Promtail into Loki (retention 30 days). Audit logs are written to the audit schema "
              "of the primary database and archived monthly to object storage (retention 7 years). Ingress access logs are kept on the ingress nodes under /var/log/nginx for 14 days."),
    ]


def backup() -> list:
    return control("JM-BCP-007", "1.3", "2026-09-15", "Operations Manager") + [
        ("h1", "1. Backup Schedule"),
        ("table", ["Data", "Method", "Schedule"], [
            ["PostgreSQL", "Full base backup plus continuous WAL archiving", "Full backup every night at 01:00; WAL shipped every minute"],
            ["OpenSearch", "Snapshot to object storage", "Daily at 02:30"], ["MinIO documents", "Bucket replication to DC2", "Continuous"],
            ["Configuration and Vault", "Git mirror and Vault snapshot", "Daily at 03:00"],
        ]),
        ("h1", "2. Backup Retention"),
        ("p", "Nightly backups are kept for 35 days, month-end backups for 12 months and year-end backups for 7 years."),
        ("h1", "3. Backup Location"),
        ("p", "Backups are written to encrypted object storage in data centre DC2, with a second copy to an offsite vault operated by the infrastructure provider. "
              "Backup encryption keys are held in Vault and in a sealed envelope held by the Security Officer."),
        ("h1", "4. Restore Procedure"),
        ("p", "Restores are performed by the Platform Operations team using the SOP Restore PostgreSQL From Backup: restore the latest full backup to a new instance, "
              "replay the WAL up to the requested time, verify row counts and run the application smoke tests before switching traffic. A restore test is performed every quarter."),
        ("h1", "5. Recovery Objectives"),
        ("table", ["Objective", "Target"], [["Recovery point objective (RPO)", "15 minutes"], ["Recovery time objective (RTO)", "4 hours"]]),
        ("h1", "6. Disaster Recovery Plan"),
        ("p", "If data centre DC1 is lost, the Incident Commander declares a disaster. Platform Operations promotes the PostgreSQL replica in DC2, scales up the jm-dr cluster, "
              "switches the public DNS name www.jobmatch.example to DC2 and informs the service desk. After DC1 is restored, data is replicated back and traffic is returned in a "
              "planned maintenance window. The plan is rehearsed twice a year."),
    ]


def sops() -> list:
    def proc(name, purpose, trigger, frequency, roles, prerequisites, steps, verification, escalation):
        return [("h2", name), ("table", ["Item", "Detail"], [["Purpose", purpose], ["Trigger", trigger], ["Frequency", frequency], ["Roles", roles],
                                                             ["Prerequisites", prerequisites], ["Verification", verification], ["Escalation", escalation]]), ("steps", steps)]
    return control("JM-SOP-008", "2.0", "2026-10-05", "Operations Manager") + [
        ("h1", "1. Standard Operating Procedures"),
        ("p", "These procedures are the approved way to perform recurring operations on JobMatch. Follow them exactly; if a step cannot be performed, stop and escalate."),
    ] + proc("1.1 Deploy a Release to Production", "Put an approved release into production without interrupting users", "A release approved in the weekly release meeting",
             "Every two weeks, Tuesday 22:00", "Release Manager, Deployment Engineer", "Approval recorded in the release ticket; staging tests passed; backup of the last night completed",
             ["Announce the start in #jm-ops.", "Start the production deployment job in GitLab with the release tag.", "Wait for the rolling update to finish.", "Run the smoke test job.",
              "Watch the API Overview dashboard for 30 minutes."], "All smoke tests pass and the error rate stays below 1 percent", "Roll back (SOP 1.2) and escalate to the Platform Team Lead") + \
    proc("1.2 Roll Back a Release", "Return to the previous release after a failed deployment", "Smoke test failure or HighApiErrorRate within an hour of a deployment",
         "On demand", "Deployment Engineer, Incident Commander", "Previous release still in the registry; Incident Commander agrees",
         ["Announce the rollback in #jm-ops.", "Run helm rollback for each changed chart to the previous revision.", "Check pod status until all pods are ready.", "Run the smoke test job."],
         "Smoke tests pass and the error alert clears", "Incident Commander; if the schema cannot be used, start the restore SOP 1.4") + \
    proc("1.3 Rotate TLS Certificates", "Replace a TLS certificate before it expires", "CertificateExpiry alert or the yearly schedule", "Yearly and on alert",
         "Platform Engineer, Security Officer", "New certificate issued by the certificate authority and delivered to Vault",
         ["Verify the new certificate chain and key match.", "Update the secret in Vault.", "Restart the ingress pods one at a time.", "Check the certificate from outside the network."],
         "The public site presents the new certificate with the new expiry date", "Security Officer") + \
    proc("1.4 Restore PostgreSQL From Backup", "Recover the database after data loss or corruption, or prove that backups work", "Data loss incident or the quarterly restore test",
         "Quarterly and on demand", "Database Administrator, Incident Commander", "Backup and WAL archive reachable; a free database instance of the same size",
         ["Create a new PostgreSQL instance from the Terraform module.", "Restore the latest full backup.", "Replay the WAL to the target time.", "Compare row counts of key tables with the source.",
          "Run the application smoke tests against the restored instance."], "Row counts match within the expected tolerance and smoke tests pass", "Operations Manager if the restore exceeds 2 hours") + \
    proc("1.5 Run Partner Sync Backfill", "Resend vacancies that failed to synchronise with the jobs.ps portal", "SyncLagHigh alert", "On demand",
         "Integrations Engineer", "Partner API reachable; no deployment in progress",
         ["Open the Partner Sync dashboard and note the failing vacancies.", "Run the backfill job with the time range of the lag.", "Check the job log for rejected records.",
          "Run the duplicate check job."], "Sync lag falls below 5 minutes and the duplicate check reports no duplicates", "Integrations Team lead") + \
    proc("1.6 Monthly Access Review", "Confirm that only the right people have administrative access", "Calendar reminder", "Monthly",
         "Security Officer, Platform Team Lead", "Export of the administrative groups from Keycloak and Vault",
         ["Export the group memberships.", "Ask each team lead to confirm their members.", "Remove access that is not confirmed.", "Record the result in the access review ticket."],
         "Every account is confirmed or removed and the ticket is closed", "Operations Manager")


def runbooks() -> list:
    def book(code, title, alert, symptoms, diagnosis, actions, escalate):
        return [("h1", f"{code} {title}"), ("p", f"Alert: {alert}. Symptoms: {symptoms}"), ("h2", "Diagnosis"), ("steps", diagnosis), ("h2", "Actions"), ("steps", actions),
                ("p", f"Escalate: {escalate}")]
    return control("JM-RUN-009", "1.7", "2026-10-06", "Platform Team Lead") + [
        ("h1", "On-Call Runbooks"),
        ("p", "These runbooks are for the on-call engineer. Acknowledge the page within 10 minutes and work through the steps in order."),
    ] + book("RB-01", "High API Error Rate", "HighApiErrorRate", "users see error pages or failed saves; 5xx rate above 2 percent",
             ["Check whether a deployment happened in the last hour.", "Open the API Overview dashboard and find the failing route.", "Check the logs of the failing service in Loki."],
             ["If a deployment caused it, roll back using the SOP Roll Back a Release.", "If one service is failing, restart its pods one at a time.", "If the database is the cause, continue with RB-02."],
             "Page the Platform Team Lead after 30 minutes without improvement") + \
    book("RB-02", "Database Connections Exhausted", "DatabaseConnectionsExhausted", "requests time out waiting for a connection",
         ["List the longest running queries in PostgreSQL.", "Check which service holds the most connections."],
         ["Cancel the runaway query.", "Restart the service that holds the connections.", "Raise the pool size temporarily only with the Platform Team Lead's approval."],
         "Page the Database Administrator") + \
    book("RB-03", "Matching Queue Backlog", "MatchQueueBacklog", "new matches appear late; queue depth rising",
         ["Open the Matching Pipeline dashboard.", "Check the worker count and the job duration."],
         ["Scale the Matching Engine workers up by 4 replicas.", "If one job type fails repeatedly, move its messages to the dead-letter queue."],
         "Notify the Matching Team in the morning if the backlog cleared; page them if it did not clear in one hour") + \
    book("RB-04", "Partner Sync Lag", "SyncLagHigh", "vacancies appear late on jobs.ps",
         ["Open the Partner Sync dashboard.", "Check whether the partner API returns errors."],
         ["If the partner API is down, wait and inform the service desk.", "Otherwise run the Run Partner Sync Backfill procedure."], "Integrations Team lead during business hours") + \
    book("RB-05", "Backup Failed", "BackupFailed", "a nightly backup job reports failure",
         ["Read the backup job log.", "Check free space on the backup storage."],
         ["Rerun the backup job.", "If storage is full, remove expired backups according to the retention policy and rerun."], "Operations Manager if two nights in a row fail")


def support() -> list:
    return control("JM-SUP-010", "1.4", "2026-09-24", "Operations Manager") + [
        ("h1", "1. Support Model"),
        ("p", "JobMatch uses a three-level support model. Level 1 is the service desk (business days 08:00 to 17:00 local time) which logs and resolves simple issues. "
              "Level 2 is Platform Operations which diagnoses technical faults and is on call around the clock for critical incidents. Level 3 is the engineering team that owns the faulty component."),
        ("h1", "2. Support Contacts"),
        ("table", ["Role", "Team", "Contact channel", "Support hours", "Escalates to"], [
            ["Service Desk Agent", "Service Desk", "servicedesk@jobmatch.example, phone ext. 4100", "Business days 08:00-17:00", "Platform Operations Engineer"],
            ["Platform Operations Engineer", "Platform Operations", "Slack #jm-ops, pager (Opsgenie)", "24x7 on call for critical incidents", "Platform Team Lead"],
            ["Platform Team Lead", "Platform Team", "lead-platform@jobmatch.example", "Business days, on call for critical", "Operations Manager"],
            ["Matching Engineer", "Matching Team", "Slack #jm-matching", "Business days 08:00-17:00", "Matching Team Lead"],
            ["Integrations Engineer", "Integrations Team", "Slack #jm-integrations", "Business days 08:00-17:00", "Integrations Team Lead"],
            ["Security Officer", "Security", "security@jobmatch.example", "Business days; 24x7 for security incidents", "Chief Information Officer"],
        ]),
        ("h1", "3. Escalation Path"),
        ("p", "Service Desk Agent, then Platform Operations Engineer, then the owning engineering team lead, then the Platform Team Lead, then the Operations Manager, and finally the "
              "Director of the Employment Services Directorate for incidents that affect the public."),
        ("h1", "4. Incident Management"),
        ("table", ["Priority", "Definition", "Response target", "Resolution target"], [
            ["P1", "Service unavailable or personal data at risk", "15 minutes, 24x7", "4 hours"], ["P2", "Major function unusable, no workaround", "1 hour", "1 business day"],
            ["P3", "Function degraded, workaround exists", "4 hours", "5 business days"], ["P4", "Question or cosmetic issue", "1 business day", "Next release"],
        ]),
        ("p", "Every P1 and P2 incident has an Incident Commander (the senior Platform Operations Engineer on call), a written timeline and a post-incident review within five business days."),
        ("h1", "5. Runbooks"),
        ("p", "Operational runbooks are kept in the document On-Call Runbooks (RB-01 to RB-05) and in the Standard Operating Procedures."),
    ]


def known_issues() -> list:
    return control("JM-KNW-011", "1.9", "2026-10-08", "Product Owner") + [
        ("h1", "1. Known Issues"),
        ("table", ["ID", "Title", "Symptoms", "Cause", "Workaround", "Permanent fix", "Severity", "Status", "Ticket"], [
            ["KE-001", "Password-protected CVs fail to parse", "Upload stays on 'processing' and no skills are extracted", "The parser cannot open encrypted PDF files", "Ask the user to upload an unprotected copy", "Detect encryption and show a clear message; planned for release 1.4", "Medium", "Open", "JM-1423"],
            ["KE-002", "Arabic names with diacritics rank inconsistently in search", "The same name with and without diacritics returns different order", "The analyser does not normalise diacritics", "Search without diacritics", "Add a normalising analyser and reindex; planned for 1.4", "Low", "Open", "JM-1388"],
            ["KE-003", "Duplicate vacancies on jobs.ps after a timeout", "A vacancy appears twice on the partner portal", "Partner API commits the vacancy but times out before replying, and the retry creates a second one", "Run the duplicate check job from the Partner Sync procedure", "Idempotency key on partner calls; release 1.3.3", "High", "In progress", "JM-1510"],
            ["KE-004", "Notification e-mails delayed during queue backlog", "E-mails arrive up to 15 minutes late", "Notifications share a queue with matching jobs", "None needed; delay is temporary", "Separate notification queue; release 1.4", "Low", "Open", "JM-1456"],
            ["KE-005", "Dashboard layout breaks in Safari 15", "Cards overlap on the job seeker dashboard", "Unsupported CSS grid feature", "Use a current browser", "None; Safari 15 is out of the supported browser list", "Low", "Won't fix", "JM-1301"],
        ]),
        ("h1", "2. Limitations"),
        ("bullets", ["CV files larger than 10 MB are rejected.", "Each employer account can publish at most 200 active vacancies.", "The reporting export is limited to 100,000 rows."]),
    ]


def release_notes() -> list:
    def release(version, date, features, fixes):
        return [("h1", f"Release {version} ({date})"), ("h2", "Additions"), ("bullets", features), ("h2", "Fixes"), ("bullets", fixes)]
    return control("JM-REL-012", "1.3.2", "2026-10-07", "Release Manager") + [("p", "Release notes for JobMatch, newest first.")] + \
        release("1.3.2", "2026-10-07", ["Employer shortlist export to Excel"], ["Fixed wrong sort order in the candidate list", "Fixed a memory leak in the Resume Parser workers"]) + \
        release("1.3.1", "2026-09-23", ["Match score explanation shown to job seekers"], ["Fixed login loop when cookies were blocked", "Fixed Arabic text alignment in e-mails"]) + \
        release("1.3.0", "2026-09-09", ["SMS notifications for new matches", "Admin Console audit log viewer"], ["Fixed duplicate application e-mails"]) + \
        release("1.2.0", "2026-06-24", ["jobs.ps vacancy synchronisation", "Employer shortlist review screen"], ["Fixed slow search for common job titles"]) + \
        release("1.1.0", "2026-04-28", ["CV parsing for Word documents", "Reporting Service monthly exports"], ["Fixed profile photo upload on mobile browsers"]) + \
        release("1.0.0", "2026-03-15", ["First production release: registration, vacancy posting, AI matching, notifications"], ["Not applicable for the first release"])


def risk_register() -> list:
    return control("JM-RSK-013", "1.2", "2026-09-28", "Product Owner") + [
        ("h1", "1. Risk Register"),
        ("table", ["Risk ID", "Risk", "Likelihood", "Impact", "Mitigation", "Owner", "Status"], [
            ["RSK-01", "The matching model drifts and quality falls", "Medium", "High", "Monthly evaluation against labelled data; retrain when precision drops 5 points", "Matching Team Lead", "Monitored"],
            ["RSK-02", "The jobs.ps API changes without notice", "Medium", "Medium", "Contract tests run nightly; contact person at the partner", "Integrations Team Lead", "Monitored"],
            ["RSK-03", "Loss of data centre DC1", "Low", "High", "Warm standby in DC2; twice-yearly rehearsal", "Operations Manager", "Mitigated"],
            ["RSK-04", "Personal data leak", "Low", "Critical", "Encryption, least privilege access, monthly access review, audit log", "Security Officer", "Mitigated"],
            ["RSK-05", "Key engineer leaves", "Medium", "Medium", "Pairing, runbooks, cross-training", "Platform Team Lead", "Open"],
        ]),
        ("h1", "2. Assumptions"),
        ("bullets", ["The Civil Registry service stays available during business hours.", "Employment offices keep manual lists as a fallback for two days.", "User growth stays below 30 percent per year."]),
    ]


def adrs() -> list:
    return control("JM-ADR-014", "1.0", "2026-08-30", "Chief Architect") + [
        ("h1", "ADR-001 Use RabbitMQ for asynchronous work"),
        ("p", "Status: Accepted. Context: parsing, matching and notifications are slow and must not block requests. Decision: use RabbitMQ with Celery workers. "
              "Consequences: we operate a broker cluster, but retries and dead-letter handling come for free."),
        ("h1", "ADR-002 Use OpenSearch for candidate retrieval"),
        ("p", "Status: Accepted. Context: matching needs fast filtering plus vector similarity. Decision: use OpenSearch with k-NN. Consequences: one more cluster to operate; "
              "PostgreSQL stays the system of record."),
        ("h1", "ADR-003 Run on private Kubernetes, not a public cloud"),
        ("p", "Status: Accepted. Context: government data residency rules. Decision: two private data centres with Kubernetes. Consequences: we own the hardware lifecycle and capacity planning."),
        ("h1", "ADR-004 Keycloak for identity"),
        ("p", "Status: Accepted. Context: single sign-on for staff and public sign-up. Decision: Keycloak with OpenID Connect. Consequences: realm configuration is code-managed."),
    ]


def service_levels() -> list:
    return [
        ("table", ["Field", "Value"], [["Document ID", "GDS-SLO-2026"], ["Version", "3.0"], ["Status", "Approved"], ["Owner", "Digital Government Office"], ["Date", "2026-01-12"],
                                      ["Classification", NOTE]]),
        ("h1", "1. Service Level Objectives"),
        ("p", "Every government digital service that is classified tier 2 or higher must meet these service level objectives."),
        ("table", ["Objective", "Definition", "Target", "Measurement window", "Measurement source", "Consequence of breach"], [
            ["Availability", "Share of minutes in which the public entry point answers health probes successfully", "99.5 percent", "Calendar month", "External uptime probe", "Service review with the Digital Government Office"],
            ["API latency", "95th percentile response time of read requests", "800 ms", "Rolling 7 days", "Gateway metrics", "Performance remediation plan within 30 days"],
            ["Error rate", "Share of requests that return a server error", "Below 1 percent", "Calendar month", "Gateway metrics", "Post-incident review"],
            ["Incident response", "Time from a critical alert to acknowledgement", "15 minutes", "Per incident", "Pager records", "Escalation to the service owner"],
            ["Recovery", "Time to restore service after a loss of the primary site", "4 hours", "Per incident", "Incident timeline", "Disaster recovery review"],
        ]),
        ("h1", "2. Key Performance Indicators"),
        ("table", ["KPI", "Definition", "Unit", "Target", "Current value", "Frequency", "Owner", "Data source"], [
            ["Time to first match", "Median time from registration to the first suggested vacancy", "hours", "24", "31", "Monthly", "Product Owner", "Platform analytics"],
            ["Match acceptance rate", "Share of suggested matches that the job seeker opens", "percent", "35", "29", "Monthly", "Product Owner", "Platform analytics"],
            ["Employer response time", "Median time for an employer to review a new application", "days", "3", "4.5", "Monthly", "Employment Services Director", "Platform analytics"],
            ["Service desk satisfaction", "Average rating of resolved tickets", "score out of 5", "4.2", "4.0", "Quarterly", "Operations Manager", "Ticket system survey"],
        ]),
    ]


JOBS = [
    ("Product-Overview.docx", word, "Product Overview and Business Case", product_overview),
    ("Solution-Architecture-Document.pdf", pdf, "Solution Architecture Document", architecture),
    ("Environment-Catalogue.docx", word, "Environment Catalogue", environments),
    ("Hosting-Configuration.md", markdown, "Hosting and Infrastructure Configuration", hosting_markdown),
    ("Deployment-and-Release-Guide.docx", word, "Deployment and Release Management Guide", deployment),
    ("Monitoring-and-Observability-Plan.pdf", pdf, "Monitoring and Observability Plan", monitoring),
    ("Backup-and-Disaster-Recovery-Plan.docx", word, "Backup and Disaster Recovery Plan", backup),
    ("Standard-Operating-Procedures.docx", word, "Standard Operating Procedures", sops),
    ("On-Call-Runbooks.html", web, "On-Call Runbooks", runbooks),
    ("Support-and-Escalation-Guide.html", web, "Support and Escalation Guide", support),
    ("Known-Issues-and-Limitations.html", web, "Known Issues and Limitations", known_issues),
    ("Release-Notes.html", web, "Release Notes", release_notes),
    ("Risk-Register.html", web, "Risk Register", risk_register),
    ("Design-Decision-Log.md", markdown, "Design Decision Log", adrs),
    ("Digital-Services-Service-Level-Standard.pdf", pdf, "Government Digital Services Service Level Standard", service_levels),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, writer, title, build in JOBS:
        writer(OUT / name, title, build())
        print("wrote", name)


if __name__ == "__main__":
    main()
