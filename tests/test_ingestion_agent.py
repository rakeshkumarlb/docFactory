import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from docfactory import db
from docfactory.agents.anthropic_model_client import AnthropicModelClient
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.agents.ingestion_agent import IngestionAgent, load_prompt
from docfactory.ingest.paths import DOCSTORE_ENV, INCOMING_ENV
from docfactory.models.message_role import MessageRole
from docfactory.models.model_message import ModelMessage
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall
from docfactory.models.tool_spec import ToolSpec

CORPUS = Path(__file__).parent / "corpus" / "incoming"


@pytest.fixture
def dirs(tmp_db, tmp_path, monkeypatch):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    monkeypatch.setenv(INCOMING_ENV, str(incoming))
    monkeypatch.setenv(DOCSTORE_ENV, str(tmp_path / "DocStore"))
    return incoming


def call(id, name, **arguments):
    return ModelResponse(tool_calls=[ToolCall(id=id, name=name, arguments_json=json.dumps(arguments))])


def test_prompt_loads_without_frontmatter():
    prompt = load_prompt()
    assert prompt.startswith("You are the") and "---" not in prompt.splitlines()[0]


def test_happy_path_stores_and_defers(dirs):
    shutil.copyfile(CORPUS / "readmeforge-runbooks.html", dirs / "runbooks.html")
    shutil.copyfile(CORPUS / "notes.txt", dirs / "notes.txt")
    fake = FakeModelClient([
        call("1", "list_incoming"),
        call("2", "compare_with_docstore", incoming_path="runbooks.html", target_path="ReadmeForge/runbooks.html"),
        call("3", "store_file", incoming_path="runbooks.html", target_path="ReadmeForge/runbooks.html"),
        call("4", "defer_file", path="notes.txt", reason="personal notes"),
        ModelResponse(text="done"),
    ])
    agent = IngestionAgent(fake, system="SYS")
    assert agent.run() == "done"
    assert db.get_docstore_row("ReadmeForge/runbooks.html")["Version"] == 1
    assert (dirs / "notes.txt").is_file() and not (dirs / "runbooks.html").exists()
    system, messages, tools = fake.requests[0]
    assert system == "SYS" and [t.name for t in tools] == agent.package.tool_names()
    assert messages[0].role == MessageRole.USER
    # the second request carries the assistant call and its tool result
    roles = [m.role for m in fake.requests[1][1]]
    assert roles == [MessageRole.USER, MessageRole.ASSISTANT, MessageRole.TOOL]
    assert fake.requests[1][1][2].tool_call_id == "1"


def test_tool_outside_the_package_is_refused_not_run(dirs):
    fake = FakeModelClient([call("1", "run_shell", command="rm -rf /"), ModelResponse(text="ok")])
    agent = IngestionAgent(fake, system="SYS")
    assert agent.run() == "ok"
    result = json.loads(agent.messages[2].text)
    assert result["ok"] is False and "not in the ingestion package" in result["error"]


def test_bad_arguments_come_back_as_errors(dirs):
    fake = FakeModelClient([
        call("1", "store_file", incoming_path="x.txt"),  # missing target_path
        call("2", "store_file", incoming_path="x.txt", target_path="a/x.txt", bogus=1),  # unknown argument
        ModelResponse(text="gave up"),
    ])
    agent = IngestionAgent(fake, system="SYS")
    agent.run()
    results = [json.loads(m.text) for m in agent.messages if m.role == MessageRole.TOOL]
    assert len(results) == 2 and all(r["ok"] is False for r in results)


def test_invalid_argument_json_cannot_become_a_tool_call():
    with pytest.raises(ValueError):
        ToolCall(id="1", name="store_file", arguments_json="{not json")


def test_turn_cap_raises(dirs):
    fake = FakeModelClient([call(str(i), "list_incoming") for i in range(5)])
    with pytest.raises(RuntimeError):
        IngestionAgent(fake, system="SYS", max_turns=3).run()


class _StubMessages:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(content=[
            SimpleNamespace(type="text", text="thinking"),
            SimpleNamespace(type="tool_use", id="tu_1", name="list_incoming", input={}),
        ])


def test_anthropic_client_translates_both_ways():
    stub = SimpleNamespace(messages=_StubMessages())
    client = AnthropicModelClient(model="m", client=stub)
    messages = [
        ModelMessage(role=MessageRole.USER, text="go"),
        ModelMessage(role=MessageRole.ASSISTANT, text="", tool_calls=[ToolCall(id="a", name="x", arguments_json='{"p": 1}'),
                                                                        ToolCall(id="b", name="y")]),
        ModelMessage(role=MessageRole.TOOL, tool_call_id="a", text="ra"),
        ModelMessage(role=MessageRole.TOOL, tool_call_id="b", text="rb"),
    ]
    spec = ToolSpec(name="x", description="d", input_schema_json='{"type": "object"}')
    response = client.complete("SYS", messages, [spec])
    sent = stub.messages.kwargs
    assert sent["model"] == "m" and sent["system"] == "SYS"
    assert sent["tools"] == [{"name": "x", "description": "d", "input_schema": {"type": "object"}}]
    assert [m["role"] for m in sent["messages"]] == ["user", "assistant", "user"]
    assert sent["messages"][1]["content"][0] == {"type": "tool_use", "id": "a", "name": "x", "input": {"p": 1}}
    assert [b["tool_use_id"] for b in sent["messages"][2]["content"]] == ["a", "b"]
    assert response.text == "thinking" and response.tool_calls[0].id == "tu_1"
