from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class FactContribution(DocFactoryModel):
    """One row of the FactContributions table: what one DocStore file contributed to one knowledge fact. A fact is the deterministic merge of all its contributions, so re-extracting a changed file replaces only that file's contribution. Infrastructure; holds no application knowledge itself."""

    fact_key: str = doc_field(
        description="The fact key this contribution belongs to, e.g. AI-Driven-Job-Matching-Platform.FunctionalRequirements.",
        question="Which fact key does this contribution belong to?",
        min_length=1,
    )
    resource: str = doc_field(
        description="DocStore path of the file that contributed, e.g. AI-Driven-Job-Matching-Platform/Annex-A SRS.pdf, or (existing) for a fact value stored before any extraction (e.g. seed data), kept as the lowest-precedence contribution.",
        question="Which DocStore file made this contribution?",
        min_length=1,
    )
    value_json: str = doc_field(
        description="The partial fact value this file states, as canonical JSON text of the entity's fields (only the fields the file states), e.g. {\"requirements\":[{\"description\":\"...\",\"id\":\"FR-01\",\"title\":\"...\"}]}.",
        question="What partial fact value, as canonical JSON, does this file state?",
        min_length=1,
    )
    hashcode: str = doc_field(
        description="SHA-256 hex (64 lowercase hex characters) of value_json, e.g. the sha256_hex of the canonical JSON text.",
        question="What is the SHA-256 hex of value_json?",
        pattern="^[0-9a-f]{64}$",
    )
    chunks_hash: str | None = doc_field(
        default=None,
        description="SHA-256 hex of the entity's chunk headings and texts in this file at extraction time; an unchanged hash means the entity need not be extracted again, e.g. a 64-character hex string. None for the (existing) contribution.",
        question="What was the hash of the entity's chunks in this file at extraction time?",
    )
    description: str | None = doc_field(
        default=None,
        description="One sentence summarizing what this file says about the fact, submitted by the extraction call, e.g. Functional requirements for user management, job posting and matching. None when none was given.",
        question="What one sentence summarizes what this file says about the fact?",
    )
    generated_by: str = doc_field(
        description="The actor that produced the contribution, <producer>/<version>, e.g. okf-extraction-agent/gemma4:31b, or the stored fact's generated_by for an (existing) contribution.",
        question="Which actor produced this contribution?",
        min_length=1,
    )
    timestamp: str = doc_field(
        description="When the contribution was written, ISO 8601 with UTC offset, e.g. 2026-10-04T09:30:00+00:00.",
        question="When was this contribution written?",
        min_length=1,
    )
