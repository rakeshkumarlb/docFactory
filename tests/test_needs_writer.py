"""The needs-list LLM call with a scripted model (Phase 4 step 4): one fresh single-tool call, checked by code, never blocking."""
import json

import pytest

from docfactory import clock, db
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.agents.needs_writer import PROMPT_FILE, NeedsWriter
from docfactory.agents.prompt_file import load_prompt
from docfactory.generation import document_store
from docfactory.generation.generate_document import generate_document
from docfactory.documentmodels.document_gap import DocumentGap
from docfactory.documentmodels.missing_info import MissingInfo
from docfactory.entitysaver.functional_requirements_saver import FunctionalRequirementsSaver
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall

GAPS = [
    DocumentGap(number=1, field="functional_requirements.requirements[].rationale", question="Why does this requirement exist?",
                expected_source="FunctionalRequirements.requirements[].rationale", missing_in=2, item_count=2, example_items=["FR-01 | Login | The system SHALL ..."]),
    DocumentGap(number=2, field="service_levels.objectives", question="Which service level objectives apply?", expected_source="Slo.objectives"),
]
GOOD = [{"question": "Why do the 2 requirements exist?", "audience": "product owner", "gaps": [1]},
        {"question": "Which SLOs apply?", "audience": "service owner", "gaps": [2]}]


def submit(needs):
    return ModelResponse(tool_calls=[ToolCall(id="c1", name="submit_needs", arguments_json=json.dumps({"needs": needs}))])


def fake(*responses):
    return FakeModelClient(list(responses))


def test_the_prompt_loads_and_names_the_tool():
    assert "submit_needs" in load_prompt(PROMPT_FILE)


def test_one_call_sees_only_the_numbered_gaps_and_its_one_tool():
    client = fake(submit(GOOD), ModelResponse(text="done"))
    needs, note = NeedsWriter(client, system="S")("Acme", "Software Requirements Specification", GAPS)
    assert note == "" and [n.audience for n in needs] == ["product owner", "service owner"]
    system, messages, tools = client.requests[0]
    assert [t.name for t in tools] == ["submit_needs"] and len(client.requests) == 2
    text = messages[0].text
    assert "Application: Acme" in text and "#1 functional_requirements.requirements[].rationale (missing in 2 of 2 items)" in text
    assert "e.g. FR-01 | Login" in text and "#2 service_levels.objectives" in text


def test_a_refused_answer_is_fed_back_and_the_fix_accepted():
    client = fake(submit(GOOD[:1]), submit(GOOD), ModelResponse(text="done"))
    needs, note = NeedsWriter(client, system="S")("Acme", "SRS", GAPS)
    assert len(needs) == 2 and note == ""
    feedback = client.requests[1][1][-1].text
    assert "covered by no need: [2]" in feedback


def test_no_accepted_answer_returns_none_with_the_reason():
    needs, note = NeedsWriter(fake(ModelResponse(text="I cannot.")), system="S")("Acme", "SRS", GAPS)
    assert needs is None and "without an accepted submit_needs call" in note


def test_a_failing_model_returns_none_and_never_raises():
    needs, note = NeedsWriter(fake(), system="S")("Acme", "SRS", GAPS)  # no scripted response: the client raises
    assert needs is None and note


def test_an_accepted_answer_survives_a_failed_closing_reply():
    needs, note = NeedsWriter(fake(submit(GOOD)), system="S")("Acme", "SRS", GAPS)  # the closing reply raises
    assert len(needs) == 2 and note == ""


@pytest.fixture
def app(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-07T10:00:00Z")
    fr = {"requirements": [{"id": "FR-01", "title": "Login", "description": "The system SHALL let users log in.", "priority": "MUST"}]}
    assert FunctionalRequirementsSaver().save("Acme.FunctionalRequirements", fr).ok
    return "Acme"


class CoverAll:
    """A scripted client that answers with one need covering every gap it is shown, for one product owner."""

    def __init__(self):
        self.calls = 0

    def complete(self, system, messages, tools):
        self.calls += 1
        if len(messages) > 1:
            return ModelResponse(text="done")
        numbers = [int(line.split()[0][1:]) for line in messages[0].text.splitlines() if line.startswith("#")]
        return submit([{"question": "Please complete the document.", "audience": "product owner", "gaps": numbers}])


def test_generate_with_the_writer_saves_the_llm_list_and_skips_the_call_when_the_gaps_are_unchanged(app):
    client = CoverAll()
    writer = NeedsWriter(client, system="S")

    first = generate_document(app, "SRS", writer)
    second = generate_document(app, "SRS", writer)

    info = document_store.stored_model(MissingInfo, "Acme.Outputs.SRS.MissingInfo")
    assert first.needs_origin == "llm" and first.need_count == 1 and info.needs[0].gaps == [g.number for g in info.gaps]
    assert second.needs_skipped and client.calls == 2  # the call and its closing reply, both in the first run


def test_the_entry_point_uses_the_writer_unless_no_llm(app, monkeypatch, capsys):
    from docfactory import generate as entry
    client = CoverAll()
    monkeypatch.setattr(entry, "default_client", lambda: client)
    monkeypatch.setattr(entry, "load_env_file", lambda: None)

    assert entry.main([app, "SRS"]) == 0
    assert "(llm)" in capsys.readouterr().out and client.calls == 2
