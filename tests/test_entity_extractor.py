"""The LLM step of extraction with a scripted model: one fresh single-tool call per batch (Phase 3 redesign, step 2)."""
import json

from docfactory.agents.entity_extractor import PROMPT_FILE, EntityExtractor
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall

REQ = {"id": "FR-01", "title": "Register", "description": "Users register."}
BATCH = [DocChunk(chunk_no=4, heading="3. F > 3.1. Login", text="FR-01. | Users register.", text_hash="0" * 64)]


def call(**arguments):
    return ModelResponse(tool_calls=[ToolCall(id="c1", name="submit_extraction", arguments_json=json.dumps(arguments))])


def fake(*responses):
    client = FakeModelClient(list(responses))
    client.model = "fake"
    return client


def test_the_actor_is_set_by_code_and_the_prompt_loads():
    assert EntityExtractor(fake(), system="S").actor == "okf-extraction-agent/fake"
    assert "submit_extraction" in load_prompt(PROMPT_FILE)


def test_one_batch_is_one_call_that_sees_only_the_batch():
    client = fake(call(values={"requirements": [REQ]}, summary="Login."), ModelResponse(text="done"))
    stated, summary, note = EntityExtractor(client, system="S").extract_batch(FunctionalRequirements, "Acme/srs.pdf", BATCH)
    assert (stated, summary, note) == ({"requirements": [REQ]}, "Login.", "")
    system, messages, tools = client.requests[0]
    assert [t.name for t in tools] == ["submit_extraction"]
    assert "Entity: FunctionalRequirements" in messages[0].text and "[chunk 4] 3. F > 3.1. Login" in messages[0].text


def test_a_rejected_answer_is_fed_back_and_the_fix_accepted():
    client = fake(call(values={"requirements": [{**REQ, "id": "FR-9"}]}), call(values={"requirements": [REQ]}), ModelResponse(text="ok"))
    stated, _, _ = EntityExtractor(client, system="S").extract_batch(FunctionalRequirements, "Acme/srs.pdf", BATCH)
    assert stated == {"requirements": [REQ]}
    assert "FR-9" in client.requests[1][1][-1].text  # the tool error went back to the model


def test_a_failed_call_returns_a_note_not_an_exception():
    client = fake(ModelResponse(text=""), ModelResponse(text=""))
    stated, summary, note = EntityExtractor(client, system="S").extract_batch(FunctionalRequirements, "Acme/srs.pdf", BATCH)
    assert stated is None and summary is None and "empty reply" in note


def test_a_call_ending_without_an_answer_returns_a_note():
    stated, _, note = EntityExtractor(fake(ModelResponse(text="nothing here")), system="S").extract_batch(FunctionalRequirements, "p", BATCH)
    assert stated is None and "without an accepted" in note


def test_an_accepted_answer_survives_a_failing_closing_reply():
    client = fake(call(values={"requirements": [REQ]}), ModelResponse(text=""), ModelResponse(text=""))
    stated, _, note = EntityExtractor(client, system="S").extract_batch(FunctionalRequirements, "p", BATCH)
    assert stated == {"requirements": [REQ]} and note == ""
