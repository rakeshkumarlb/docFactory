import hashlib
import math
import re

from docfactory.retrieval.embedder import Embedder

DIMENSIONS = 64


class FakeEmbedder(Embedder):
    """Deterministic test embedder: a normalised bag of hashed words, so texts that share words are close. Needs no server."""

    model = "fake-embedder"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        vector = [0.0] * DIMENSIONS
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vector[int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16) % DIMENSIONS] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]
