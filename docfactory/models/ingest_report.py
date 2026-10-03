from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.ingest_outcome import IngestOutcome


class IngestReport(DocFactoryModel):
    """The report of ingesting one file: what happened to it (outcome), where it was stored, how it was chunked and tagged, and which entities need re-extraction."""

    file_name: str = doc_field(
        description="The original's file name, e.g. 'Annex-A SRS.pdf'. Never empty.",
        question="What is the file name of the ingested original?",
        min_length=1,
    )
    outcome: IngestOutcome = doc_field(
        description="What ingestion did with the file: NEW, CHANGED, SAME, REPAIRED or STAGED, e.g. NEW.",
        question="What was the outcome of ingesting this file?",
    )
    target_path: str | None = doc_field(
        default=None,
        description="DocStore path '<scope>/<file name>' when the file was stored, e.g. 'AI-Driven-Job-Matching-Platform/Annex-A SRS.pdf'. None when the file stayed in staging.",
        question="Under which DocStore path was the file stored?",
    )
    version: int | None = doc_field(
        default=None,
        description="DocStore version of the file after ingestion, e.g. 1. None when the file was not stored.",
        question="What DocStore version does the file have after ingestion?",
    )
    chunk_count: int = doc_field(
        default=0,
        description="Number of chunks stored for the file, e.g. 76. Zero when nothing was chunked.",
        question="How many chunks were stored for this file?",
    )
    entity_summary: list[str] = doc_field(
        default_factory=list,
        description="One line per tagged entity with its chunk count, e.g. ['FunctionalRequirements: 25 chunks'].",
        question="Which entities were tagged, and on how many chunks each?",
    )
    unmapped_chunks: list[int] = doc_field(
        default_factory=list,
        description="Chunk numbers on which no entity was tagged, e.g. [1, 39, 40]. These are the candidates for the LLM fallback.",
        question="Which chunk numbers have no entity tagged?",
    )
    changed_entities: list[str] = doc_field(
        default_factory=list,
        description="On CHANGED, the entities whose chunks changed and need re-extraction, e.g. ['FunctionalRequirements']. Empty for every other outcome.",
        question="Which entities have changed chunks and need re-extraction?",
    )
    reason: str = doc_field(
        default='',
        description="How the scope was decided, or why the file stayed in staging, e.g. \"document control row 'Title' -> 'AI-Driven Job Matching Platform'\".",
        question="How was the scope decided, or why did the file stay in staging?",
    )
