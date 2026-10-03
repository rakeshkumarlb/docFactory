import json
from pathlib import Path

from docfactory.agents.model_client import ModelClient
from docfactory.db import PROJECT_ROOT
from docfactory.models.message_role import MessageRole
from docfactory.models.model_message import ModelMessage
from docfactory.models.tool_spec import ToolSpec
from docfactory.tools.ingestion_tools import ingestion_package
from docfactory.tools.tool_package import ToolPackage

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-ingestion-agent.md"
START_MESSAGE = "Ingest the files that are waiting in incoming/ now."


def load_prompt(path: Path = PROMPT_FILE) -> str:
    """The agent's system prompt: the markdown file without its YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    return text.strip()


class IngestionAgent:
    """Thin agent loop: call the model, run the tool it asks for through its tool package, feed the result back, stop when it answers in text.

    It holds no business logic and can reach only the tools of the package it was given; any other call is answered with an error.
    """

    def __init__(self, client: ModelClient, package: ToolPackage | None = None, system: str | None = None, max_turns: int = 40) -> None:
        self.client = client
        self.package = package or ingestion_package()
        self.system = system if system is not None else load_prompt()
        self.max_turns = max_turns
        self.messages: list[ModelMessage] = []

    def run(self) -> str:
        """Run until the model stops calling tools and return its final text. Raises RuntimeError at the turn cap."""
        specs = [ToolSpec(name=t.name, description=t.description, input_schema_json=json.dumps(t.input_schema())) for t in self.package.tools()]
        self.messages = [ModelMessage(role=MessageRole.USER, text=START_MESSAGE)]
        for _ in range(self.max_turns):
            response = self.client.complete(self.system, self.messages, specs)
            self.messages.append(ModelMessage(role=MessageRole.ASSISTANT, text=response.text, tool_calls=response.tool_calls))
            if not response.tool_calls:
                return response.text
            for call in response.tool_calls:
                self.messages.append(ModelMessage(role=MessageRole.TOOL, tool_call_id=call.id, text=json.dumps(self._run_call(call.name, call.arguments_json))))
        raise RuntimeError(f"ingestion agent stopped: still calling tools after {self.max_turns} turns")

    def _run_call(self, name: str, arguments_json: str):
        try:
            return self.package.call(name, json.loads(arguments_json))  # ToolCall guarantees a JSON object
        except PermissionError as exc:  # a tool outside the package: feedback for the model, never run
            return {"ok": False, "error": str(exc)}
