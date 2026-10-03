from pathlib import Path

from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt as _load_prompt
from docfactory.db import PROJECT_ROOT
from docfactory.tools.ingestion_tools import ingestion_package
from docfactory.tools.tool_package import ToolPackage

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-ingestion-agent.md"
START_MESSAGE = "Ingest the files that are waiting in incoming/ now."


def load_prompt(path: Path = PROMPT_FILE) -> str:
    """The ingestion agent's system prompt: the markdown file without its YAML frontmatter."""
    return _load_prompt(path)


class IngestionAgent(AgentLoop):
    """The agent loop run with the ingestion tool package and the ingestion prompt."""

    def __init__(self, client: ModelClient, package: ToolPackage | None = None, system: str | None = None, max_turns: int = 40) -> None:
        super().__init__(client, package or ingestion_package(), system if system is not None else load_prompt(), START_MESSAGE, max_turns, "ingestion agent")
