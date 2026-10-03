from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class FactVerification(DocFactoryModel):
    """One verification event of a knowledge fact (an OKF verified[] entry): who confirmed it and when."""

    by: str = doc_field(
        description="The actor who verified the fact, per OKF: 'human:<id>', 'process:<id>' or '<producer>/<version>', e.g. human:test-user. Must not be empty.",
        question="Who verified this fact?",
        min_length=1,
    )
    at: str = doc_field(
        description="When the verification happened, ISO 8601 datetime with explicit UTC offset, e.g. 2026-06-30T14:00:00Z.",
        question="When was this fact verified?",
        pattern="^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$",
    )
