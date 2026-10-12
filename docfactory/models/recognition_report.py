from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.recognition_outcome import RecognitionOutcome


class RecognitionReport(DocFactoryModel):
    """The report of recognizing one ingested original: how many windows and calls, what was skipped or failed, how many entities and relationships were found, and notes for a human."""

    path: str = doc_field(
        description="Bundle path of the original, e.g. 'Acme/references/srs.pdf'.",
        question="Which original was recognized?",
        min_length=1,
    )
    outcome: RecognitionOutcome = doc_field(
        description="What happened, e.g. RECOGNIZED.",
        question="What was the outcome?",
    )
    windows: int = doc_field(
        default=0,
        description="Number of windows the original was cut into, e.g. 8.",
        question="How many windows did the original have?",
    )
    calls: int = doc_field(
        default=0,
        description="Number of recognition calls made, e.g. 8; 0 when every window was unchanged.",
        question="How many calls were made?",
    )
    skipped_windows: int = doc_field(
        default=0,
        description="Windows skipped because their chunks were unchanged, e.g. 3.",
        question="How many windows were skipped as unchanged?",
    )
    failed_windows: int = doc_field(
        default=0,
        description="Windows whose call gave no accepted answer, e.g. 1; they are retried on the next run.",
        question="How many windows failed?",
    )
    entities: int = doc_field(
        default=0,
        description="Number of entities recognized in the original, e.g. 24.",
        question="How many entities were recognized?",
    )
    relations: int = doc_field(
        default=0,
        description="Number of relationships recognized in the original, e.g. 15.",
        question="How many relationships were recognized?",
    )
    notes: list[str] = doc_field(
        default_factory=list,
        description="Problems and remarks for a human, one per line, e.g. ['window 3: the model ended without an accepted answer'].",
        question="What should a human know about this run?",
    )
