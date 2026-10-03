from enum import StrEnum


class MessageRole(StrEnum):
    """Who authored a model message: USER (the caller), ASSISTANT (the model) or TOOL (a tool result answering a tool call)."""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
