from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.save_action import SaveAction


class GenerationReport(DocFactoryModel):
    """The report of generating one document type for one application: what happened to the body row, the document version and revision entry, how many gaps and needs there are and where the needs came from, which files were written, and any save or render problems."""

    doc_type: str = doc_field(
        description="The document type that was generated, e.g. SRS.",
        question="Which document type was generated?",
        min_length=1,
    )
    body_key: str = doc_field(
        description="The key of the document body row, e.g. AI-Driven-Job-Matching-Platform.Outputs.SRS.",
        question="Which body row key does this report belong to?",
        min_length=1,
    )
    body_action: SaveAction | None = doc_field(
        default=None,
        description="What the body save did (CREATED, UPDATED, UNCHANGED or REJECTED), e.g. UPDATED. None when the body was not saved.",
        question="What did the body save do?",
    )
    body_version: int | None = doc_field(
        default=None,
        description="The body row's version after the save, e.g. 3. None when the body was not saved.",
        question="What is the body row's version after the save?",
    )
    body_completeness: float | None = doc_field(
        default=None,
        description="The body's completeness from 0 to 100 after the save, e.g. 71.4. None when the body was not saved.",
        question="What is the body's completeness after the save?",
    )
    document_version: str = doc_field(
        default='',
        description="The document's own version label after this run, e.g. '0.3'. Empty when not determined.",
        question="What is the document's version after this run?",
    )
    revision_added: str = doc_field(
        default='',
        description="The summary of the revision entry this run added, e.g. 'Changed sections: functional_requirements (from X.FunctionalRequirements v2).'. Empty when no entry was added.",
        question="Which revision entry did this run add?",
    )
    gap_count: int = doc_field(
        default=0,
        description="Number of gaps (unanswered bound fields) behind the needs list, e.g. 12.",
        question="How many gaps does the document have?",
    )
    need_count: int = doc_field(
        default=0,
        description="Number of needs in the needs list, e.g. 7.",
        question="How many needs does the needs list hold?",
    )
    needs_origin: str = doc_field(
        default='',
        description="Where the needs came from: llm, fallback or no_llm, e.g. 'no_llm'. Empty when no needs list was built.",
        question="Where did the needs list come from?",
    )
    needs_skipped: bool = doc_field(
        default=False,
        description="True when the gaps were unchanged, so no LLM call was made and the stored needs list was kept; e.g. True on a second run with unchanged facts.",
        question="Was the needs-list call skipped because the gaps were unchanged?",
    )
    needs_note: str = doc_field(
        default='',
        description="Why the needs list fell back to one need per gap, e.g. 'the model ended without an accepted submit_needs call'. Empty otherwise.",
        question="Why did the needs list fall back to one need per gap?",
    )
    output_files: list[str] = doc_field(
        default_factory=list,
        description="The files written or removed, as relative paths with forward slashes, e.g. ['output/AI-Driven-Job-Matching-Platform/SRS.md'].",
        question="Which output files were written or removed?",
    )
    errors: list[str] = doc_field(
        default_factory=list,
        description="Save rejections or render problems, one line each, e.g. 'AI-Driven-Job-Matching-Platform.Outputs.SRS.DocumentControl: REJECTED: title: ...'. Empty when everything was saved.",
        question="Which save or render problems occurred?",
    )
