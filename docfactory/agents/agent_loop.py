import json

from docfactory.agents.model_client import ModelClient
from docfactory.models.message_role import MessageRole
from docfactory.models.model_message import ModelMessage
from docfactory.models.tool_spec import ToolSpec
from docfactory.tools.tool_package import ToolPackage

EMPTY_REPLY_NUDGE = "Your last reply was empty. Continue the task: call the tool you need, or answer in text if you are done."


class AgentLoop:
    """Thin agent loop: call the model, run the tool it asks for through its tool package, feed the result back, stop when it answers in text.

    It holds no business logic and can reach only the tools of the package it was given; any other call is answered with an error.
    """

    def __init__(self, client: ModelClient, package: ToolPackage, system: str, start_message: str, max_turns: int = 40, name: str = "agent") -> None:
        self.client = client
        self.package = package
        self.system = system
        self.start_message = start_message
        self.max_turns = max_turns
        self.name = name
        self.messages: list[ModelMessage] = []

    def run(self, start_message: str | None = None) -> str:
        """Run until the model stops calling tools and return its final text. Raises RuntimeError at the turn cap."""
        specs = [ToolSpec(name=t.name, description=t.description, input_schema_json=json.dumps(t.input_schema())) for t in self.package.tools()]
        self.messages = [ModelMessage(role=MessageRole.USER, text=start_message or self.start_message)]
        nudged = False
        for _ in range(self.max_turns):
            response = self.client.complete(self.system, self.messages, specs)
            self.messages.append(ModelMessage(role=MessageRole.ASSISTANT, text=response.text, tool_calls=response.tool_calls))
            if not response.tool_calls:
                if response.text.strip():
                    return response.text
                if nudged:  # an empty reply is a failure, never a silent finish
                    raise RuntimeError(f"{self.name} stopped: the model returned an empty reply twice")
                nudged = True
                self.messages.append(ModelMessage(role=MessageRole.USER, text=EMPTY_REPLY_NUDGE))
                continue
            for call in response.tool_calls:
                self.messages.append(ModelMessage(role=MessageRole.TOOL, tool_call_id=call.id, text=json.dumps(self._run_call(call.name, call.arguments_json))))
        raise RuntimeError(f"{self.name} stopped: still calling tools after {self.max_turns} turns")

    def _run_call(self, name: str, arguments_json: str):
        try:
            return self.package.call(name, json.loads(arguments_json))  # ToolCall guarantees a JSON object
        except PermissionError as exc:  # a tool outside the package: feedback for the model, never run
            return {"ok": False, "error": str(exc)}
