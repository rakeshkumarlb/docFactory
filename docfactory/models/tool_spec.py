import json

from pydantic import field_validator

from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ToolSpec(DocFactoryModel):
    """The description of one tool offered to the model: its name, what it does and the JSON schema of its arguments."""

    name: str = doc_field(
        description="Name of the tool as the model must call it, e.g. 'list_incoming'.",
        question="What is the tool's name?",
        min_length=1,
    )
    description: str = doc_field(
        description="What the tool does and when to use it, written for the model, e.g. 'List the files waiting in incoming/.'.",
        question="What does the tool do?",
        min_length=1,
    )
    input_schema_json: str = doc_field(
        description="JSON schema of the tool's arguments as the text of a JSON object (enforced: must parse as JSON and be an object, not an array, string or number), e.g. '{\"type\": \"object\", \"properties\": {}}'.",
        question="What is the JSON schema of the tool's arguments?",
        min_length=1,
    )

    @field_validator("input_schema_json")
    @classmethod
    def _schema_must_be_json_object(cls, value: str) -> str:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"input_schema_json must be valid JSON text: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"input_schema_json must be a JSON object, got {type(parsed).__name__}")
        return value
