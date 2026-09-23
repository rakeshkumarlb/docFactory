---
app: kitchenhq
topic: dr
summary: 
updated: 2026-09-23
---

# Dr

## Backup

- [F-0105] `python dbmcp/scripts/backup_db.py` takes an online-backup snapshot of the database into `dbmcp/backups/`, keeping the last 14. — src: store/kitchenhq/docs/repo/README.md
- [F-0106] The backup script is safe under concurrent writers because it uses the SQLite online-backup API. — src: store/kitchenhq/docs/repo/README.md
- [F-0107] The README advises scheduling the backup script daily via cron / Task Scheduler. — src: store/kitchenhq/docs/repo/README.md
- [F-0108] SQLite has no replication; only local timestamped snapshots exist. — src: store/kitchenhq/docs/repo/README.md
- [F-0297] An example daily backup schedule is the cron entry `0 3 * * * KITCHEN_DB_PATH=/path/to/kitchen.db python /path/to/dbmcp/scripts/backup_db.py` (or Windows Task Scheduler). — src: store/kitchenhq/docs/repo/dbmcp/README.md
