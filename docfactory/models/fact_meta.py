from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.fact_source import FactSource


class FactMeta(DocFactoryModel):
    """The judgment fields a caller supplies when saving a knowledge fact (who produced it, how to title and summarize it, where it came from). Everything else in the OKF frontmatter is derived by code."""

    generated_by: str = doc_field(
        description="The actor that produced the fact, per OKF: '<producer>/<version>' for agents and tools, e.g. okf-extraction-agent/gemma4:31b, or seed for seed data. Must not be empty.",
        question="Which agent, tool or process produced this fact?",
        min_length=1,
    )
    title: str | None = doc_field(
        default=None,
        description="Display name of the fact, e.g. ReadmeForge Architecture. None lets the code derive it from the key.",
        question="What is the display name of this fact?",
    )
    description: str | None = doc_field(
        default=None,
        description="ONE sentence summarizing the fact, used for search snippets, e.g. Describes the three services that make up ReadmeForge. None when not yet written.",
        question="What is a one-sentence summary of this fact?",
    )
    tags: list[str] = doc_field(
        default_factory=list,
        description="Short cross-cutting categorization strings, e.g. ['architecture', 'production']. Empty when none apply.",
        question="Which short tags categorize this fact?",
    )
    sources: list[FactSource] = doc_field(
        default_factory=list,
        description="The DocStore files this fact was derived from, one entry per file. Empty only for seed data, e.g. one FactSource for 'ReadmeForge/ReadmeForge SRS v0.3.pdf'.",
        question="Which files did this fact come from?",
    )
    stale_after: str | None = doc_field(
        default=None,
        description="When the fact should be re-checked, ISO 8601 datetime with explicit UTC offset, e.g. 2026-12-31T00:00:00Z. None when it has no expiry.",
        question="After when should this fact be re-checked?",
        pattern="^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$",
    )
