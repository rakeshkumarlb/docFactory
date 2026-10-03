"""The embedder the entry points use. Tests pass a FakeEmbedder instead."""
from docfactory.retrieval.embedder import Embedder


def default_embedder() -> Embedder:
    """The Ollama embedder (model from DOCFACTORY_EMBED_MODEL)."""
    from docfactory.retrieval.ollama_embedder import OllamaEmbedder

    return OllamaEmbedder()
