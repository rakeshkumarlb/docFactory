---
type: "Backup Recovery"
title: "AI-Driven-Job-Matching-Platform backup recovery"
description: "Non-functional requirements for data backups, recovery objectives, and disaster recovery planning."
tags: ["backup-recovery", "extracted"]
sources:
  - resource: "AI-Driven-Job-Matching-Platform/references/Annex-A-Detailed-Software-Requirements-Specification-SRS.pdf"
    last_modified: 2026-10-10T12:10:17+00:00
generated: { by: "okf-extraction-agent/gemma4:31b", at: 2026-10-10T12:10:51Z }
status: draft
fact_key: "AI-Driven-Job-Matching-Platform.BackupRecovery"
version: 1
completeness: 85.7143
hashcode: "909551a8ce9854ddd26a994effdeb7dcba8f6eed4dff314e33db20f525aeffb2"
---

# Value

```json
{
  "backup_schedule": "full backups at least weekly and incremental backups daily",
  "backup_retention": null,
  "backup_location": "geographically separate locations from the primary system",
  "restore_procedure": "document and test restoration procedures",
  "rpo": "1 hour",
  "rto": "4 hours for critical functions and 24 hours for non-critical functions",
  "disaster_recovery_plan": "documented and tested disaster recovery plan"
}
```

# Open questions: AI-Driven-Job-Matching-Platform.BackupRecovery

These fields are not answered yet. Until someone answers them, the default shown is assumed.

1. `backup_retention`: How long are backups retained?
   Assumed until answered: none
