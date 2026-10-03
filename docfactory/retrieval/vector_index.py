from abc import ABC, abstractmethod

from docfactory.models.retrieval_hit import RetrievalHit


class VectorIndex(ABC):
    """Similarity index over the frontmatter of the knowledge facts. Derived data: it can always be rebuilt from the database."""

    @abstractmethod
    def rebuild(self) -> tuple[int, int]:
        """Bring the index in step with KnowledgeFacts. Returns (facts embedded, facts removed); unchanged facts are not embedded again."""

    @abstractmethod
    def query(self, text: str, app_id: str | None = None, limit: int = 8, include_deprecated: bool = False) -> list[RetrievalHit]:
        """The facts closest to `text`, best first. With `app_id`, only that application's facts and the Shared ones."""
