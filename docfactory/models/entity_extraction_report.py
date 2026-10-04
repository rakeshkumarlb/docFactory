from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.save_action import SaveAction
from docfactory.models.save_error import SaveError


class EntityExtractionReport(DocFactoryModel):
    """The report of extracting one entity from one DocStore file: what happened, how many chunks and LLM calls it took, what was saved, and what a human should review (missing answers, ungrounded values, conflicts, failed batches, save errors)."""

    entity: str = doc_field(
        description="The entity that was extracted, as its model name, e.g. FunctionalRequirements.",
        question="Which entity was extracted?",
        min_length=1,
    )
    outcome: ExtractionOutcome = doc_field(
        description="What happened to this entity in this file, e.g. SAVED. See ExtractionOutcome for the meaning of each value.",
        question="What was the outcome of extracting this entity?",
    )
    key: str | None = doc_field(
        default=None,
        description="The fact key the result belongs to, e.g. AI-Driven-Job-Matching-Platform.FunctionalRequirements. None when no key applies (SKIPPED_SCOPE).",
        question="Which fact key does this extraction belong to?",
    )
    reason: str = doc_field(
        default='',
        description="Why the entity was skipped, removed, rejected or failed, in one sentence, e.g. 'no batch gave an accepted answer'. Empty when it was saved.",
        question="Why was this entity not saved?",
    )
    chunks_used: int = doc_field(
        default=0,
        description="Number of chunks of this file tagged with the entity that were read, e.g. 28.",
        question="How many chunks of this file were tagged with the entity?",
    )
    batches: int = doc_field(
        default=0,
        description="Number of LLM calls made, one per batch of chunks, e.g. 6. 0 when the entity was skipped.",
        question="How many LLM calls (batches) were made?",
    )
    failed_batches: int = doc_field(
        default=0,
        description="Number of batches that gave no accepted answer, e.g. 1.",
        question="How many batches gave no accepted answer?",
    )
    contributions: int = doc_field(
        default=0,
        description="Number of files whose contributions were merged into the fact, e.g. 2.",
        question="How many files' contributions were merged into the fact?",
    )
    items: int = doc_field(
        default=0,
        description="Number of list items in the merged fact (for example requirements), e.g. 85.",
        question="How many list items does the merged fact hold?",
    )
    priorities_from_keywords: int = doc_field(
        default=0,
        description="How many requirement priorities code filled from the requirement's own obligation keyword (SHALL/MUST -> MUST, SHOULD -> SHOULD, MAY -> COULD) because the extraction left them empty, e.g. 140. Zero when none were filled.",
        question="How many requirement priorities were filled from keywords?",
    )
    action: SaveAction | None = doc_field(
        default=None,
        description="The saver's action for the merged fact (CREATED, UPDATED, UNCHANGED or REJECTED), e.g. UPDATED. None when nothing was saved.",
        question="What did the saver do with the merged fact?",
    )
    version: int | None = doc_field(
        default=None,
        description="The fact's version after saving, e.g. 2. None when nothing was saved.",
        question="What is the fact's version after saving?",
    )
    completeness: float | None = doc_field(
        default=None,
        description="The fact's completeness from 0 to 100 after saving, e.g. 62.5. None when nothing was saved.",
        question="What is the fact's completeness after saving?",
    )
    missing_questions: list[str] = doc_field(
        default_factory=list,
        description="Questions for fields the merged fact still leaves unanswered, e.g. 'requirements[].priority: What is the priority of the requirement? (missing in 20 of 28)'.",
        question="Which questions remain open for the merged fact?",
    )
    ungrounded_values: list[str] = doc_field(
        default_factory=list,
        description="Extracted text values not found in the chunk text, listed for human review, e.g. \"summary: 'Invented text'\".",
        question="Which extracted values were not found in the source text?",
    )
    conflicts: list[str] = doc_field(
        default_factory=list,
        description="Values on which sources or batches disagreed, with the kept value, e.g. \"purpose: kept 'X' from a.pdf; b.pdf says 'Y'\".",
        question="Which values did sources or batches disagree on?",
    )
    batch_notes: list[str] = doc_field(
        default_factory=list,
        description="What went wrong in failed batches, e.g. 'batch 3 (chunks 40-44): model returned an empty reply twice'.",
        question="What went wrong in the failed batches?",
    )
    save_errors: list[SaveError] = doc_field(
        default_factory=list,
        description="The saver's errors when the merged fact was REJECTED, each with path, message, field description and question, e.g. a mandatory field no document states yet; empty otherwise.",
        question="Which errors did the saver report for the merged fact?",
    )
