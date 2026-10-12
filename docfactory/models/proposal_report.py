from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ProposalReport(DocFactoryModel):
    """The report of looking for new entity types in the chunks of one ingested original that are in no knowledge fact: how many chunks and calls it took and which proposals were stored."""

    path: str = doc_field(
        description="Bundle path of the original, e.g. 'Acme/references/srs.pdf'.",
        question="Which original was looked at?",
        min_length=1,
    )
    chunks_asked: int = doc_field(
        default=0,
        description="Number of chunks shown to the model, e.g. 3.",
        question="How many chunks were shown?",
    )
    batches: int = doc_field(
        default=0,
        description="Number of LLM calls made, e.g. 1. Zero when the chunks were unchanged or nothing was left.",
        question="How many calls were made?",
    )
    failed_batches: int = doc_field(
        default=0,
        description="Number of single-chunk calls that gave no accepted answer, e.g. 0.",
        question="How many calls failed?",
    )
    saved: list[str] = doc_field(
        default_factory=list,
        description="Entities of the proposals stored as new, e.g. ['Risks'].",
        question="Which proposals were stored?",
    )
    already_known: list[str] = doc_field(
        default_factory=list,
        description="Entities that were proposed again but already have a stored proposal, e.g. ['Risks'].",
        question="Which proposals already existed?",
    )
    reason: str = doc_field(
        default="",
        description="Why nothing was asked or stored, e.g. 'the chunks are unchanged since the last look'. Empty when proposals were stored.",
        question="Why was nothing stored?",
    )
    batch_notes: list[str] = doc_field(
        default_factory=list,
        description="What went wrong in a batch, one line each, e.g. 'chunks 4-4: the model ended without an accepted answer'.",
        question="What went wrong in a batch?",
    )
