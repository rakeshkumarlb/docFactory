---
type: "Backup Recovery"
title: "ReadmeForge.BackupRecovery"
generated: { by: "seed", at: 2026-10-03T12:30:22Z }
status: draft
fact_key: "ReadmeForge.BackupRecovery"
version: 1
completeness: 100
---

# ReadmeForge.BackupRecovery

## Backup location

PostgreSQL: geo-redundant backup stored in South India (Chennai), the paired disaster-recovery region. Blob Storage: RA-GRS, with the secondary copy in South India.

## Backup retention

PostgreSQL: point-in-time restore window of 14 days. Blob Storage: soft delete retention of 7 days. Redis is a cache and is not backed up.

## Backup schedule

PostgreSQL: automated continuous backups (a full snapshot daily plus continuous WAL archiving). Blob Storage: continuous through RA-GRS replication with soft delete enabled.

## Disaster recovery plan

On loss of Central India (Pune), promote South India (Chennai) as the primary write region for PostgreSQL, let Azure Front Door route traffic to the remaining healthy locations, and follow the database fail-over SOP at docs/runbooks/fail-over-database-to-south-india.md.

## Restore procedure

PostgreSQL: use point-in-time restore to a new Flexible Server in Central India (or promote South India for a regional failure), then repoint the api and workers via Key Vault-backed connection secrets. Blob Storage: undelete soft-deleted blobs within 7 days, or read from the RA-GRS secondary. Redis is rebuilt empty on restart; users simply sign in again.

## Rpo

15 minutes

## Rto

1 hour for regional failure
