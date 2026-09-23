---
app: kitchenhq
topic: cicd
summary: 
updated: 2026-09-23
---

# Cicd

## Drift check

- [F-0306] `python shared/sync.py --check` exits non-zero if a vendored copy has drifted; the README suggests wiring it into a pre-commit hook or running it before releasing. — src: store/kitchenhq/docs/repo/shared/README.md
- [F-0307] dbmcp's test suite also asserts that its copy matches `shared/constants.py`. — src: store/kitchenhq/docs/repo/shared/README.md
