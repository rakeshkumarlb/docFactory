from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.db import PROJECT_ROOT
from docfactory.retrieval.vector_index import VectorIndex
from docfactory.tools.generation_tools import generation_package
from docfactory.tools.tool_package import ToolPackage

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-document-generator-agent.md"


def start_message(app_id: str, doc_type: str) -> str:
    return (f"Generate the {doc_type} document body for the application '{app_id}' and save it under the key "
            f"'{app_id}.Outputs.{doc_type}' now.")


class GeneratorAgent(AgentLoop):
    """The agent loop run with the generator tool package and the generator prompt. `run(app_id, doc_type)` generates one document body."""

    def __init__(self, client: ModelClient, index: VectorIndex, package: ToolPackage | None = None, system: str | None = None,
                 max_turns: int = 60) -> None:
        super().__init__(client, package or generation_package(index), system if system is not None else load_prompt(PROMPT_FILE),
                         "", max_turns, "document generator agent")

    def run(self, app_id: str, doc_type: str) -> str:
        """Generate and save one document body (type as get_document_schema lists it) and return the agent's summary."""
        return super().run(start_message(app_id, doc_type))
