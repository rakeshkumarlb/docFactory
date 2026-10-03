import re

from pydantic import field_validator

from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class EntitySignals(DocFactoryModel):
    """The tagging signals of one knowledge entity in the ingestion ontology. Ingestion splits an original document into chunks and tags each chunk with the entities it informs by matching these signals; an LLM is only a fallback."""

    entity: str = doc_field(
        description="Entity model name exactly as the class is named, e.g. FunctionalRequirements.",
        question="Which entity model (exact class name, e.g. FunctionalRequirements) do these signals belong to?",
        min_length=1,
    )
    heading_terms: list[str] = doc_field(
        default_factory=list,
        description="Lower-case phrases that, when found in a chunk's heading trail, are strong evidence for this entity; sub-sections inherit them, e.g. ['functional requirements', 'system features'].",
        question="Which lower-case heading phrases (e.g. 'functional requirements') signal this entity?",
    )
    id_patterns: list[str] = doc_field(
        default_factory=list,
        description="Python regular expressions matching the identifiers of this entity's items in the text, strong evidence, e.g. ['\\bFR-\\d+']. Every pattern must compile.",
        question="Which regular expressions (e.g. '\\bFR-\\d+') match the identifiers of this entity's items?",
    )
    keywords: list[str] = doc_field(
        default_factory=list,
        description="Lower-case words or phrases in the chunk text that are weak evidence for this entity, e.g. ['shall', 'use case'].",
        question="Which lower-case words or phrases (e.g. 'shall') in the text weakly signal this entity?",
    )

    @field_validator("id_patterns")
    @classmethod
    def _patterns_must_compile(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError(f"id_patterns entry {pattern!r} is not a valid regular expression: {error}") from error
        return patterns
