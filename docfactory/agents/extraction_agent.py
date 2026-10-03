from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.db import PROJECT_ROOT
from docfactory.tools.extraction_tools import extraction_package
from docfactory.tools.tool_package import ToolPackage

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-okf-extraction-agent.md"
ACTOR_PREFIX = "okf-extraction-agent"


def actor_of(client: ModelClient) -> str:
    """The OKF actor recorded as generated.by: okf-extraction-agent/<model>. Set by code, never by the model."""
    return f"{ACTOR_PREFIX}/{getattr(client, 'model', 'unknown')}"


def start_message(docstore_path: str) -> str:
    return f"Extract the knowledge in the DocStore file '{docstore_path}' and save it as facts now."


class ExtractionAgent(AgentLoop):
    """The agent loop run with the extraction tool package and the extraction prompt. `run(docstore_path)` extracts from one file."""

    def __init__(self, client: ModelClient, package: ToolPackage | None = None, system: str | None = None, max_turns: int = 40,
                 actor: str | None = None) -> None:
        self.actor = actor or actor_of(client)
        super().__init__(client, package or extraction_package(self.actor), system if system is not None else load_prompt(PROMPT_FILE),
                         "", max_turns, "extraction agent")

    def run(self, docstore_path: str) -> str:
        """Extract facts from one DocStore file (path as list_docstore shows it) and return the agent's summary."""
        return super().run(start_message(docstore_path))
