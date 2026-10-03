from abc import ABC, abstractmethod


class Embedder(ABC):
    """Turns texts into vectors. The only place that knows which embedding technology is used; the index depends on this interface."""

    model: str  # identifies the embedding model: an index built with another model is rebuilt

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """One vector per text, in order. All vectors have the same length."""
