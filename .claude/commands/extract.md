---
description: Propose knowledge-base changes from new/changed store documents (needs your approval to apply)
argument-hint: [app or store path, optional]
---
Use the `knowledge-extractor` agent on documents pending extraction (`python tools/db.py pending-extraction`). Restrict to this app or path if given: $ARGUMENTS
Produce one proposal per document and present each for approval. Do not apply anything.
