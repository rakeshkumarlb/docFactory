from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.tool_call import ToolCall


class ModelResponse(DocFactoryModel):
    """What a model returned for one turn, provider-neutral: its text and any tool calls it wants run."""

    text: str = doc_field(
        default='',
        description="The assistant's text for this turn, e.g. 'The file belongs to ReadmeForge.'. Empty when it only called tools.",
        question="What text did the model answer with?",
    )
    tool_calls: list[ToolCall] = doc_field(
        default_factory=list,
        description="Tool calls the model wants run next, e.g. one call to 'compare_with_docstore'. Empty means the model is done.",
        question="Which tool calls does the model want run, if any?",
    )
