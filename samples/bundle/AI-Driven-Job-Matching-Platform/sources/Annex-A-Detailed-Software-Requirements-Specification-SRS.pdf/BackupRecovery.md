---
type: "Contribution"
title: "AI-Driven-Job-Matching-Platform.BackupRecovery from Annex-A-Detailed-Software-Requirements-Specification-SRS.pdf"
description: "Non-functional requirements for data backups, recovery objectives, and disaster recovery planning."
sources:
  - resource: "AI-Driven-Job-Matching-Platform/references/Annex-A-Detailed-Software-Requirements-Specification-SRS.pdf"
generated: { by: "okf-extraction-agent/gemma4:31b", at: "2026-10-10T12:10:51Z" }
fact_key: "AI-Driven-Job-Matching-Platform.BackupRecovery"
hashcode: "6a05c5c371d034a7aff64e872b81a0e4a1e6fda3916c532dd11c70ff88888314"
chunks_hash: "a55974b83ce460e09735e8be6744c43359b13b1139df9ab2aa825d32a9aca9c6"
---

# Value

```json
{
  "backup_location": "geographically separate locations from the primary system",
  "backup_schedule": "full backups at least weekly and incremental backups daily",
  "disaster_recovery_plan": "documented and tested disaster recovery plan",
  "restore_procedure": "document and test restoration procedures",
  "rpo": "1 hour",
  "rto": "4 hours for critical functions and 24 hours for non-critical functions"
}
```
