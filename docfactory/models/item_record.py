from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ItemRecord(DocFactoryModel):
    """One stored item of a fact's list (a requirement, an environment, an alert, ...): its own concept file in the bundle, with its own hash, version and completeness. The fact (aggregate) is assembled from its parent concept plus these items."""

    parent_key: str = doc_field(
        description="The key of the fact the item belongs to, e.g. AI-Driven-Job-Matching-Platform.FunctionalRequirements.",
        question="Which fact does this item belong to?",
        min_length=1,
    )
    field: str = doc_field(
        description="The list field of the fact the item sits in, e.g. requirements.",
        question="Which list of the fact does this item belong to?",
        min_length=1,
    )
    item_id: str = doc_field(
        description="The item's identifier, the value of its identity field (its first mandatory field), e.g. FR-01 or 'Login service'.",
        question="What identifies this item?",
    )
    position: int = doc_field(
        description="Place of the item in its list, counting from 1, e.g. 3. Restores the list order when the fact is assembled.",
        question="At which position is this item in its list?",
        ge=1,
    )
    value: str = doc_field(
        description="The canonical JSON text of the validated item.",
        question="What is the stored JSON value of the item?",
    )
    hashcode: str = doc_field(
        description="SHA-256 hex of the canonical item value, 64 hex characters.",
        question="What is the hash of the item value?",
        pattern="^[0-9a-f]{64}$",
    )
    version: int = doc_field(
        description="Number of changes to the item, starting at 1, e.g. 2.",
        question="Which version is the item?",
        ge=1,
    )
    completeness: float = doc_field(
        description="How much of the item has been answered, 0 to 100, e.g. 75.",
        question="How complete is the item?",
    )
    relpath: str = doc_field(
        default="",
        description="Bundle-relative path of the item's concept file with forward slashes, e.g. 'Acme/FunctionalRequirements/requirements/FR-01.md'. Empty before it is written.",
        question="Where is the item's concept file?",
    )
