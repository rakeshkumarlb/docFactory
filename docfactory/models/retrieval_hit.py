from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.fact_status import FactStatus


class RetrievalHit(DocFactoryModel):
    """One knowledge fact found by a vector search over the OKF frontmatter, with its similarity score and the lifecycle flags a caller needs to judge it."""

    key: str = doc_field(
        description="The fact key of the hit, <Scope>.<Name>, e.g. ReadmeForge.Architecture.",
        question="What is the key of the fact that was found?",
        min_length=1,
    )
    score: float = doc_field(
        description="Cosine similarity of the query to the fact after the stable-over-draft boost, e.g. 0.82. Higher is more relevant.",
        question="What is the similarity score of this hit?",
    )
    title: str = doc_field(
        description="The title from the fact's frontmatter, e.g. ReadmeForge architecture.",
        question="What is the title of the fact?",
    )
    type: str = doc_field(
        description="The OKF type from the fact's frontmatter, e.g. Application Overview.",
        question="What is the OKF type of the fact?",
    )
    status: FactStatus = doc_field(
        description="Lifecycle status of the fact: draft, stable or deprecated, e.g. stable.",
        question="What is the lifecycle status of the fact?",
    )
    stale: bool = doc_field(
        default=False,
        description="True when the current time is at or after the fact's stale_after instant, e.g. False for a fresh fact.",
        question="Is the fact stale?",
    )
    file_path: str | None = doc_field(
        default=None,
        description="Path of the OKF bundle file under bundles/, forward slashes, e.g. ReadmeForge/Architecture.md. None when unknown.",
        question="Where is the bundle file of the fact?",
    )
    description: str | None = doc_field(
        default=None,
        description="The description from the fact's frontmatter, e.g. How ReadmeForge is built. None when it has none.",
        question="What is the description of the fact?",
    )
