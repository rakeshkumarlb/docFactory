from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class SaveError(DocFactoryModel):
    """One reason a save was rejected: where the problem is, what Pydantic said, and what the field means and asks, so a caller can fix the payload or go and find the missing information."""

    path: str = doc_field(
        description="Dotted location of the offending field in the payload, e.g. environments.0.name. Use 'key' for a problem with the key itself.",
        question="Which field of the payload is wrong?",
        min_length=1,
    )
    message: str = doc_field(
        description="The validation message, e.g. 'Field required' or 'Input should be a valid string'.",
        question="What is wrong with the value?",
        min_length=1,
    )
    error_type: str = doc_field(
        description="Machine-readable error type, e.g. missing, string_type, extra_forbidden, key_pattern_mismatch.",
        question="What kind of error is it?",
        min_length=1,
    )
    received: str | None = doc_field(
        default=None,
        description="The value that was sent, as JSON text or plain text, e.g. '\"abc\"'. None when nothing was sent for the field.",
        question="What value was received?",
    )
    expected: str | None = doc_field(
        default=None,
        description="What would have been valid, as plain text, e.g. 'a valid string' or 'one of CREATED, UPDATED'. None when unknown.",
        question="What value was expected?",
    )
    field_description: str | None = doc_field(
        default=None,
        description="The model's description of the offending field, e.g. 'Base URL of the environment'. None when the field is unknown to the model.",
        question="What does the offending field mean?",
    )
    question: str | None = doc_field(
        default=None,
        description="The question to ask to get the missing or corrected value, e.g. 'What is the name of the environment?'. None when the field is unknown.",
        question="What should be asked to fix this?",
    )
