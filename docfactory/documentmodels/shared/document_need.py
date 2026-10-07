from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class DocumentNeed(DocFactoryModel):
    """One entry of a generated document's needs list: a question to put to a person who can answer it, covering one or more numbered gaps. Written by the needs-list LLM call (checked by code) or, when no LLM is used or it fails, one per gap by the fallback."""

    question: str = doc_field(
        description="The question to ask, phrased in the application's own terms; it may merge several related gaps, e.g. 'Which business criticality and which owning team apply to the Job Matching Platform?'. A good need is one concrete question a person can answer in a few sentences.",
        question="What should be asked to close the gaps this need covers?",
        min_length=1,
        binding="caller",
    )
    audience: str = doc_field(
        default='',
        description="Who can answer the question, e.g. 'architect', 'product owner' or 'operations'. Empty when not decided, which is what the fallback writes.",
        question="Who is the right person to answer this question?",
        binding="caller",
    )
    gaps: list[int] = doc_field(
        description="The numbers of the gaps (DocumentGap.number) this need covers, e.g. [1, 4]. Every need covers at least one gap, and every gap is covered by at least one need.",
        question="Which gap numbers does this need cover?",
        min_length=1,
        binding="caller",
    )
