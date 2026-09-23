---
description: Show pipeline status - pending extraction, pending proposals, open conflicts, stale outputs
---
Run `python tools/db.py status`, `python tools/db.py stale-outputs`, and for each app folder in `knowledge/` run `python tools/kb.py stats <app>`. Summarize in a few lines: what needs the user's attention (unclassified files, pending proposals, open conflicts, files flagged "split suggested", outputs whose sources changed) and the command to run next.
