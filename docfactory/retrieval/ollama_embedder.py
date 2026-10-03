import os

from docfactory.agents.ollama_model_client import OllamaModelClient
from docfactory.retrieval.embedder import Embedder

EMBED_MODEL_ENV = "DOCFACTORY_EMBED_MODEL"
EMBED_HOST_ENV = "DOCFACTORY_EMBED_HOST"
EMBED_API_KEY_ENV = "DOCFACTORY_EMBED_API_KEY"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
BATCH_SIZE = 32


class OllamaEmbedder(Embedder):
    """Embedder over Ollama's /api/embed. Retry behaviour comes from the OllamaModelClient.

    Host and key default to the chat settings (OLLAMA_HOST, OLLAMA_API_KEY). Ollama Cloud serves no embedding models, so
    DOCFACTORY_EMBED_HOST (e.g. http://localhost:11434) points the embedder at another server; the chat key is then not sent to it
    (DOCFACTORY_EMBED_API_KEY, if that server needs one).
    """

    def __init__(self, model: str | None = None, client: OllamaModelClient | None = None) -> None:
        self.model = model or os.environ.get(EMBED_MODEL_ENV) or DEFAULT_EMBED_MODEL
        self._client = client or self._default_client()

    @staticmethod
    def _default_client() -> OllamaModelClient:
        host = os.environ.get(EMBED_HOST_ENV)
        if not host:
            return OllamaModelClient()
        client = OllamaModelClient(host=host)
        client.api_key = os.environ.get(EMBED_API_KEY_ENV) or None  # never the chat key: it belongs to another server
        return client

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
