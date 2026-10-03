import os

from docfactory.agents.ollama_model_client import OllamaModelClient
from docfactory.retrieval.embedder import Embedder

EMBED_MODEL_ENV = "DOCFACTORY_EMBED_MODEL"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
BATCH_SIZE = 32


class OllamaEmbedder(Embedder):
    """Embedder over Ollama's /api/embed. Host, API key and retry behaviour come from the OllamaModelClient (OLLAMA_HOST, OLLAMA_API_KEY)."""

    def __init__(self, model: str | None = None, client: OllamaModelClient | None = None) -> None:
        self.model = model or os.environ.get(EMBED_MODEL_ENV) or DEFAULT_EMBED_MODEL
        self._client = client or OllamaModelClient()

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start:start + BATCH_SIZE]
            data = self._client.post_json("/api/embed", {"model": self.model, "input": batch})
            embeddings = data.get("embeddings")
            if not embeddings or len(embeddings) != len(batch):
                raise RuntimeError(f"Ollama returned {len(embeddings or [])} embeddings for {len(batch)} texts (model {self.model!r}); is it an embedding model?")
            vectors += embeddings
        return vectors
