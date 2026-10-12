# Hosting and Infrastructure Configuration

| Field | Value |
|---|---|
| Title | AI-Driven Job Matching Platform |
| Document ID | JM-HST-004 |
| Version | 1.6 |
| Status | Approved |
| Owner | Platform Team Lead |
| Date | 2026-10-02 |
| Classification | Sample document, fictional content created to test docFactory |

## 1. Hosting Overview

JobMatch is hosted in two private data centres, DC1 (primary) and DC2 (disaster recovery). The production cluster jm-prod has 3 control-plane nodes and 9 worker nodes (16 vCPU, 64 GB each). Nodes run Ubuntu 22.04 LTS and are patched monthly.

## 2. Infrastructure Configuration Files

The files below are the actual configuration kept in the repository jobmatch-infra (values trimmed to the relevant lines).

### 2.1 Terraform: production cluster

```hcl
module "jm_prod" {
  source        = "./modules/k8s-cluster"
  name          = "jm-prod"
  datacenter    = "dc1"
  control_nodes = 3
  worker_nodes  = 9
  worker_flavor = "c16-m64"
  k8s_version   = "1.30.4"
}
```

### 2.2 NGINX Ingress configuration

```nginx
server {
  listen 443 ssl http2;
  server_name www.jobmatch.example;
  ssl_certificate     /etc/tls/jobmatch.crt;
  ssl_certificate_key /etc/tls/jobmatch.key;
  ssl_protocols TLSv1.2 TLSv1.3;
  client_max_body_size 12m;   # CV uploads
  location /api/ { proxy_pass http://api-gateway:8080; }
  location /     { proxy_pass http://web-frontend:8080; }
}
```

### 2.3 Helm values: production

```yaml
replicaCount:
  apiGateway: 3
  profileService: 4
  matchingEngine: 6
  notificationService: 2
resources:
  matchingEngine:
    requests: { cpu: "2", memory: 8Gi }
    limits:   { cpu: "4", memory: 12Gi }
postgres:
  host: pg-primary.jm-prod.svc
  poolSize: 40
rabbitmq:
  host: rabbit.jm-prod.svc
  prefetch: 20
redis:
  sentinel: redis-sentinel.jm-prod.svc:26379
```

### 2.4 docker-compose for local development

```yaml
services:
  postgres:
    image: postgres:16
    environment: { POSTGRES_PASSWORD: dev-only-password }
  opensearch:
    image: opensearchproject/opensearch:2.13.0
  rabbitmq:
    image: rabbitmq:3.13-management
  redis:
    image: redis:7
```

## 3. Network and Firewall

| Rule | Source | Destination | Port |
|---|---|---|---|
| Public web traffic | Internet | Ingress load balancers | 443 |
| Operations access | Bastion host | Cluster API | 6443 |
| Database replication | DC1 PostgreSQL | DC2 PostgreSQL | 5432 (TLS) |
| Partner calls | Partner Sync Service | jobs.ps API | 443 |

## 4. Capacity

Production is sized for 800 concurrent users and 60 requests per second. Autoscaling adds up to 4 Matching Engine replicas when CPU stays above 70 percent for five minutes.
