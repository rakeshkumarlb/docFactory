from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.documentmodels.document_gap import DocumentGap
from docfactory.documentmodels.document_need import DocumentNeed
from docfactory.documentmodels.needs_origin import NeedsOrigin


class MissingInfo(DocFactoryModel):
    """The needs list of one generated document (row <App>.Outputs.<DocType>.MissingInfo): every gap the document has (a document field no fact fills, or a bound fact field still unanswered) and the needs, the questions that together cover all gaps. Never derived from knowledge facts: written by the generate process. Reused by every document type."""

    gaps: list[DocumentGap] = doc_field(
        default_factory=list,
        description="Every gap of the document, numbered 1..n in template order, e.g. one gap for application_summary.business_criticality. An empty list means the document lacks nothing.",
        question="What does this document still lack?",
        render_as="table",
    )
    needs: list[DocumentNeed] = doc_field(
        default_factory=list,
        description="The needs list, most important first (the list order is the priority), e.g. a first need asking the product owner for the business criticality. Together the needs cover every gap.",
        question="Which questions must be answered to close the gaps, most important first?",
    )
    gaps_hash: str = doc_field(
        description="SHA-256 hex of the canonical JSON of gaps; generate skips the LLM call when it is unchanged.",
        scored=False,
    )
    needs_origin: NeedsOrigin = doc_field(
        description="Where the needs came from: llm, fallback or no_llm.",
        scored=False,
    )
