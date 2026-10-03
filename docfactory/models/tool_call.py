import json

from pydantic import field_validator

from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ToolCall(DocFactoryModel):
    """One tool call requested by the model: which tool to run and with which arguments, as text."""

    id: str = doc_field(
        description="Provider-assigned id of this call, echoed back on the tool result message, e.g. 'call_001'.",
        question="What is the provider-assigned id of this tool call?",
        min_length=1,
    )
    name: str = doc_field(
        description="Name of the tool the model wants to run, exactly as registered, e.g. 'list_incoming'.",
        question="Which tool does the model want to call?",
        min_length=1,
    )
    arguments_json: str = doc_field(
        default='{}',
        description="The call's arguments as the text of a JSON object (enforced: must parse as JSON and be an object, not an array, string or number), e.g. '{\"path\": \"test-file.txt\"}'. '{}' means no arguments.",
        question="What are the call's arguments as JSON object text?",
    )

    @field_validator("arguments_json")
    @classmethod
    def _arguments_must_be_json_object(cls, value: str) -> str:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"arguments_json must be valid JSON text: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"arguments_json must be a JSON object, got {type(parsed).__name__}")
        return value
