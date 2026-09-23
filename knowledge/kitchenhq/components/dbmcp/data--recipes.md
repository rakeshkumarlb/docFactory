---
app: kitchenhq
topic: data--recipes
summary: 
updated: 2026-09-23
---

# Data  Recipes

## Recipes

- [F-0062] A `recipes` row holds the structured recipe, its embedding and its rating together. — src: store/kitchenhq/docs/repo/README.md
- [F-0063] `add_recipe` / `update_recipe` recompute the embedding synchronously, so `search_recipes` can never search a stale vector. — src: store/kitchenhq/docs/repo/README.md
- [F-0064] `search_recipes` is a hybrid keyword + semantic search with no external vector store. — src: store/kitchenhq/docs/repo/README.md

## Recipe tools

- [F-0184] Recipe tools `add_recipe`, `update_recipe`, `get_recipe`, `list_recipes`, `delete_recipe`, `rate_recipe`, `search_recipes` and `reindex_recipes` live in `dbmcp/kitchendb/tools/recipes.py` and store one JSON-structured recipe, its embedding vector and a household star rating on the same row. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0185] `reindex_recipes` is only a bulk-backfill / embedding-model-upgrade sweep, not the normal write path. — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0186] `search_recipes` combines keyword search (`kitchendb/keyword_search.py`, FTS-style field scoring) and semantic search (`kitchendb/embeddings.py`, cosine top-k). — src: store/kitchenhq/docs/repo/CLAUDE.md
- [F-0187] A recipe surfaces in `search_recipes` if either its keyword or semantic score clears `_MATCH_THRESHOLD` (0.65). — src: store/kitchenhq/docs/repo/CLAUDE.md
