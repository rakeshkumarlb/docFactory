---
app: kitchenhq
topic: repositories
summary: 
updated: 2026-09-23
---

# Repositories

## Layout

- [F-0118] There is no top-level package manager tying the three services together; each has its own `requirements.txt` (Python, pinned) or `package.json` (Node). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0119] The only genuinely cross-service code is `shared/constants.py` (day / meal-type vocabulary and ordering). — src: store/kitchenhq/docs/repo/CLAUDE.md
