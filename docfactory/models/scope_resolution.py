from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.resolution_group import ResolutionGroup


class ScopeResolution(DocFactoryModel):
    """The entity resolution decisions of one scope, per entity type: which entities are the same thing (a resolution concept file, written only by the resolution step). Kept with the hash of the entities each type's decision was based on, so an unchanged type is never asked again."""

    scope: str = doc_field(
        description="Bundle folder of the scope, e.g. 'AI-Driven-Job-Matching-Platform'.",
        question="Which scope do the decisions belong to?",
        min_length=1,
    )
    groups: list[ResolutionGroup] = doc_field(
        default_factory=list,
        description="Every accepted group of entities that are the same thing, e.g. one group keeping 'Component/matching-engine'. Empty when no duplicates were found.",
        question="Which entities are the same thing?",
    )
    asked: list[str] = doc_field(
        default_factory=list,
        description="One '<type>=<hash of its entities>' entry per type that was asked, e.g. ['Component=ab12...']; a type whose entities still have that hash is not asked again.",
        question="Which types were asked, with which entities?",
    )
    hashcode: str = doc_field(
        description="SHA-256 hex of the canonical JSON of groups and asked, 64 lower-case hex characters, e.g. the sha256_hex of that text; a file that no longer matches was edited outside the system.",
        question="What is the hash of the decisions?",
        pattern="^[0-9a-f]{64}$",
    )
    generated_by: str = doc_field(
        description="Actor that made the decisions, <producer>/<version>, e.g. 'okf-resolution-agent/gemma4:31b'.",
        question="Which actor made the decisions?",
        min_length=1,
    )
    timestamp: str = doc_field(
        description="When the decisions were written, ISO 8601 with UTC offset, e.g. '2026-10-12T09:30:00+00:00'.",
        question="When were the decisions written?",
        min_length=1,
    )
