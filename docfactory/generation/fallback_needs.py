"""The needs list when no LLM phrases it (--no-llm, or a failed call): one need per gap, in gap order, the gap's own question."""
from docfactory.documentmodels.shared.document_gap import DocumentGap
from docfactory.documentmodels.shared.document_need import DocumentNeed


def fallback_needs(gaps: list[DocumentGap]) -> list[DocumentNeed]:
    """One need per gap, asking the gap's question; no audience, since nothing decided who can answer."""
    return [DocumentNeed(question=gap.question, gaps=[gap.number]) for gap in gaps]
