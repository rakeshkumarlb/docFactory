---
description: Approve (apply) or reject a knowledge proposal, or resolve a conflict
argument-hint: <proposal-id | conflict-id> [reject | keep new | keep existing]
---
The user is explicitly deciding on: $ARGUMENTS

- Proposal id (`P-...`): show it (`python tools/kb.py show <id>`) if the user has not just seen it, then apply with `python tools/kb.py apply <id> --approved-by <user's name from git config or "user">`. If they said reject: `python tools/kb.py reject <id> --by <name> --note "<their reason>"`.
- Conflict id (`C-...`): `python tools/kb.py resolve <id> --app <app> --keep new|existing --by <name>`.
- `all` means every pending proposal listed by `python tools/db.py status`; still apply them one at a time and report each result.
Only run apply/reject/resolve because the user asked for it in this message.
