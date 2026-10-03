from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.save_action import SaveAction
from docfactory.models.save_error import SaveError


class SaveResult(DocFactoryModel):
    """The outcome of every save call. Bad input never raises: it returns ok=False, action REJECTED and the errors to fix."""

    ok: bool = doc_field(
        description="True when the payload was valid and the row is stored (CREATED, UPDATED or UNCHANGED), e.g. False for REJECTED.",
        question="Was the save successful?",
    )
    key: str = doc_field(
        description="The key the save was called with, e.g. KitchenHQ.ApplicationOverview.",
        question="Which key was saved?",
        min_length=1,
    )
    action: SaveAction = doc_field(
        description="What the save did: CREATED, UPDATED, UNCHANGED or REJECTED, e.g. CREATED for a first write.",
        question="What did the save do?",
    )
    version: int | None = doc_field(
        default=None,
        description="Version of the stored row after the save, e.g. 1 for a first write. None when rejected.",
        question="What is the stored version?",
    )
    hashcode: str | None = doc_field(
        default=None,
        description="SHA-256 hex of the canonical value of the payload, e.g. 64 hex characters. None when rejected.",
        question="What is the hash of the stored value?",
    )
    completeness: float | None = doc_field(
        default=None,
        description="How much of the object is answered, 0 to 100, e.g. 62.5. None when rejected.",
        question="How complete is the stored object?",
    )
    errors: list[SaveError] = doc_field(
        default_factory=list,
        description="Why the save was rejected, one entry per problem, e.g. a missing mandatory field. Empty when the save succeeded.",
        question="What must be fixed?",
        scored=False,
    )
