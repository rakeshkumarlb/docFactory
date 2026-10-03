from pydantic import model_validator

from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.message_role import MessageRole
from docfactory.models.tool_call import ToolCall


class ModelMessage(DocFactoryModel):
    """One message in a conversation with a model, provider-neutral: a user turn, an assistant turn (text and/or tool calls) or a tool result."""

    role: MessageRole = doc_field(
        description="Who authored the message: user, assistant or tool, e.g. MessageRole.USER.",
        question="Who authored this message?",
    )
    text: str = doc_field(
        default='',
        description="The message text; for a tool message the tool's result text, e.g. 'Classify the file test-file.txt.'.",
        question="What is the message text?",
    )
    tool_calls: list[ToolCall] = doc_field(
        default_factory=list,
        description="Tool calls requested by the model; allowed only on ASSISTANT messages (enforced), e.g. one call to 'list_incoming'. Empty when none.",
        question="Which tool calls did the assistant request, if any?",
    )
    tool_call_id: str | None = doc_field(
        default=None,
        description="Id of the ToolCall this result answers; required on TOOL messages and forbidden on all others (enforced), e.g. 'call_001'. None otherwise.",
        question="Which tool call does this tool result answer?",
    )

    @model_validator(mode="after")
    def _check_role_rules(self) -> "ModelMessage":
        if self.tool_calls and self.role != MessageRole.ASSISTANT:
            raise ValueError("tool_calls are allowed only when role is ASSISTANT")
        if self.role == MessageRole.TOOL:
            if not self.tool_call_id:
                raise ValueError("tool_call_id is required when role is TOOL")
        elif self.tool_call_id is not None:
            raise ValueError("tool_call_id is allowed only when role is TOOL")
        return self
