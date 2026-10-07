import hashlib

import numpy as np

from docfactory import clock, db, facts
from docfactory.models.fact_status import FactStatus
from docfactory.models.retrieval_hit import RetrievalHit
from docfactory.retrieval.embedder import Embedder
from docfactory.retrieval.vector_index import VectorIndex
from docfactory.saver_resolution import ordered_value

STABLE_BOOST = 0.05  # a stable fact outranks a draft of nearly the same similarity


def _text_of(fact) -> str:
    """What is embedded for a fact: its OKF metadata (the frontmatter; the key for a fact saved before metadata existed) and its JSON
    value in model field order, so both the summary and the content words are searchable."""
    return f"{fact.frontmatter or fact.key}\n{ordered_value(fact.key, fact.value)}"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SqliteVectorIndex(VectorIndex):
    """VectorIndex over the FactIndex table: vectors as float32 blobs, cosine similarity in numpy."""

    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder

    def rebuild(self) -> tuple[int, int]:
        stored = {row["FactKey"]: row for row in db.list_index_rows()}
        current = {fact.key: _text_of(fact) for fact in facts.list_facts()}
        changed = [key for key, text in current.items()
                   if key not in stored or stored[key]["TextHash"] != _hash(text) or stored[key]["EmbedModel"] != self.embedder.model]
        removed = [key for key in stored if key not in current]
        vectors = self.embedder.embed([current[key] for key in changed]) if changed else []
        upserts = [(key, _hash(current[key]), self.embedder.model, len(vector), np.asarray(vector, dtype=np.float32).tobytes())
                   for key, vector in zip(changed, vectors)]
        db.replace_index(upserts, removed)
        return len(changed), len(removed)

    def query(self, text: str, app_id: str | None = None, limit: int = 8, include_deprecated: bool = False) -> list[RetrievalHit]:
        rows = [row for row in db.list_index_rows() if row["EmbedModel"] == self.embedder.model]
        if not rows:
            return []
        query = np.asarray(self.embedder.embed([text])[0], dtype=np.float32)
        query = query / (np.linalg.norm(query) or 1.0)
        now = clock.now_iso()
        hits = []
        for row in rows:
            fact = facts.get_fact(row["FactKey"])
            if fact is None or (app_id is not None and fact.app_id not in (None, app_id)):
                continue
            if fact.status == FactStatus.DEPRECATED and not include_deprecated:
                continue
            vector = np.frombuffer(row["Vector"], dtype=np.float32)
            if vector.shape != query.shape:
                continue
            score = float(vector @ query / (np.linalg.norm(vector) or 1.0))
            if fact.status == FactStatus.STABLE:
                score += STABLE_BOOST
            hits.append(RetrievalHit(
                key=fact.key, score=round(score, 6), title=fact.title or fact.key, type=fact.type or "", status=fact.status,
                stale=fact.stale_after is not None and now >= fact.stale_after, description=fact.description,
            ))
        return sorted(hits, key=lambda hit: (-hit.score, hit.key))[:limit]
