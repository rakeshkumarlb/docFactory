from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.entity_evidence import EntityEvidence
from docfactory.models.entity_link import EntityLink


class EntityRecord(DocFactoryModel):
    """One entity of the entity graph of a scope (an entity concept file of the bundle): its canonical name, type, aliases, the places that discuss it and its relationships. Merged deterministically from the recognitions of all originals; written only by EntityStore. It identifies an item for extraction; the item's field values live in the facts."""

    entity_id: str = doc_field(
        description="Id of the entity within its scope, '<Type>/<slug of the name>', e.g. 'Component/matching-engine'. Also its file path under <scope>/entities/.",
        question="What is the id of this entity?",
        min_length=1,
    )
    scope: str = doc_field(
        description="Bundle folder of the application (or Shared) the entity belongs to, e.g. 'AI-Driven-Job-Matching-Platform'.",
        question="Which scope does the entity belong to?",
        min_length=1,
    )
    type: str = doc_field(
        description="Entity type, from the vocabulary or 'proposed:<PascalName>', e.g. 'Component'.",
        question="Which entity type is it?",
        min_length=1,
    )
    name: str = doc_field(
        description="Canonical display name, e.g. 'Matching Engine'.",
        question="What is the canonical name of the entity?",
        min_length=1,
    )
    aliases: list[str] = doc_field(
        default_factory=list,
        description="Other names the originals use for the entity, e.g. ['AI Engine'].",
        question="Which other names do the originals use?",
    )
    summary: str = doc_field(
        default='',
        description="One sentence saying what the entity is, from the newest original that described it, e.g. 'Ranks job seekers against vacancies.'.",
        question="What is the entity, in one sentence?",
    )
    evidence: list[EntityEvidence] = doc_field(
        default_factory=list,
        description="Every place that discusses the entity, in original and chunk order, e.g. chunk 12 of the architecture document.",
        question="Where is the entity discussed?",
    )
    links: list[EntityLink] = doc_field(
        default_factory=list,
        description="The entity's relationships to other entities, e.g. depends on DataStore/search-index.",
        question="How does the entity relate to other entities?",
    )
