"""Type proposals: a kind of knowledge the ontology has no entity for becomes a pending proposal, then a model on request (redesign step 5)."""
import json
import subprocess
import sys

import pytest
from pydantic import ValidationError

from docfactory.agents.apply_type_proposal import _add_signals, apply_proposal, main as apply_main
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.agents.type_proposer import TypeProposer
from docfactory.bundle.paths import bundle_root
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.proposal_pipeline import format_proposals, propose_types
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.ingest.retag_entity import retag_entity
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.entity_signals import EntitySignals
from docfactory.models.model_response import ModelResponse
from docfactory.models.proposal_field import ProposalField
from docfactory.models.proposal_field_type import ProposalFieldType
from docfactory.models.tool_call import ToolCall
from docfactory.models.type_proposal import TypeProposal
from docfactory.ontology.proposal_checks import proposal_errors, similar_to, snake
from docfactory.ontology.proposal_spec import fact_spec, item_spec, signals_entry
from docfactory.ontology.proposal_store import APPLIED, PENDING, ProposalStore
from docfactory.project_root import PROJECT_ROOT
from docfactory.tools.proposal_tools import PROPOSAL_TOOL_NAMES, proposal_package

APP = "Acme/references/srs.md"
TEXTS = ["Cover page.", "FR-01. The system SHALL log in.", "Risk register. RISK-1 Payment provider delay. Likelihood high. Mitigation: pick a provider.", "Page 3"]

FIELD = {"name": "summary", "type": "str", "description": "What the register says overall, e.g. 'Three risks, one high.'", "question": "What does the register say overall?"}
ITEM_ID = {"name": "name", "type": "str", "description": "Short name of the risk, e.g. 'Payment provider delay'.", "question": "What is the risk called?"}
LIKELIHOOD = {"name": "likelihood", "type": "str", "description": "How likely the risk is, e.g. 'high'.", "question": "How likely is the risk?"}
RISKS = {
    "entity": "Risks", "doc": "The risks of an application with their likelihood and mitigation.", "fields": [FIELD],
    "list_name": "risks", "item_entity": "RiskEntry", "item_doc": "One risk with its likelihood and mitigation.", "item_fields": [ITEM_ID, LIKELIHOOD],
    "heading_terms": ["risk register"], "id_patterns": ["\\bRISK-\\d+"], "keywords": ["likelihood", "mitigation"],
    "sample_chunks": [3], "rationale": "Monitoring covers alerts, not project risks.",
}


def proposal(**changes):
    return TypeProposal.model_validate(RISKS | changes)


def store_source():
    original = bundle_root() / APP
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("".join(f"## Section {n}\n{t}\n\n" for n, t in enumerate(TEXTS, 1)), encoding="utf-8")
    chunks = chunk_file(original)
    SourceStore().write(APP, file_sha256(original), "2026-10-01T00:00:00Z", chunks, [ChunkTag(chunk_no=2, entity="FunctionalRequirements", origin="rule", score=4, evidence="t")])


def answer(proposals):
    return [ModelResponse(tool_calls=[ToolCall(id="c", name="submit_type_proposal", arguments_json=json.dumps({"proposals": proposals}))]), ModelResponse(text="done")]


def proposer(*answers):
    client = FakeModelClient([r for a in answers for r in a])
    client.model = "fake"
    return TypeProposer(client, system="S")


def test_a_valid_proposal_has_no_errors_and_a_set_of_problems_is_named():
    assert proposal_errors(proposal(), {1, 2, 3}) == []
    assert any("nearly the same as" in e for e in proposal_errors(proposal(entity="Monitorings"), {3}))
    assert any("existing entity 'Architecture'" in e for e in proposal_errors(proposal(entity="Architecture"), {3}))
    assert any("not given to you" in e for e in proposal_errors(proposal(sample_chunks=[9]), {3}))
    assert any("already signals" in e for e in proposal_errors(proposal(heading_terms=["monitoring"]), {3}))
    assert any("lower case" in e for e in proposal_errors(proposal(keywords=["Likelihood"]), {3}))
    assert any("not a valid regular expression" in e for e in proposal_errors(proposal(id_patterns=["("]), {3}))
    assert any("'e.g.'" in e for e in proposal_errors(proposal(fields=[{**FIELD, "description": "A description that has no example at all."}]), {3}))
    assert any("kind 'str'" in e for e in proposal_errors(proposal(fields=[{**FIELD, "type": "bool"}]), {3}))
    assert any("needs all of" in e for e in proposal_errors(proposal(item_entity=""), {3}))
    assert any("identifies the item" in e for e in proposal_errors(proposal(item_fields=[{**ITEM_ID, "type": "bool"}]), {3}))
    assert any("nearly the same" in e for e in proposal_errors(proposal(item_entity="Environment"), {3}))
    assert similar_to("Risks", ["Architecture", "Risk"]) == "Risk" and snake("RiskEntry") == "risk_entry"


def test_the_models_validate_their_own_shape():
    with pytest.raises(ValidationError):
        proposal(entity="lower")
    with pytest.raises(ValidationError):
        proposal(scope="everywhere")
    with pytest.raises(ValidationError):
        proposal(heading_terms=[])
    with pytest.raises(ValidationError):
        ProposalField.model_validate({**FIELD, "question": "No question mark"})
    assert ProposalFieldType("list[str]") is ProposalFieldType.TEXT_LIST


def test_the_package_holds_one_tool_and_checks_before_accepting():
    assert PROPOSAL_TOOL_NAMES == ["submit_type_proposal"]
    accepted = []
    package = proposal_package({3}, accepted)
    assert [t.name for t in package.tools()] == ["submit_type_proposal"] and package.name == "type-proposal"
    assert "source_path" not in package.tools()[0].input_schema()["properties"]["proposals"]["items"]["properties"]
    refused = package.call("submit_type_proposal", {"proposals": [RISKS | {"entity": "Architecture"}]})
    assert refused["ok"] is False and accepted == []
    twice = package.call("submit_type_proposal", {"proposals": [RISKS, RISKS]})
    assert twice["ok"] is False and "proposed twice" in twice["errors"][0]
    assert package.call("submit_type_proposal", {"proposals": []}) == {"ok": True, "proposals": 0}
    assert package.call("submit_type_proposal", {"proposals": [RISKS]}) == {"ok": True, "proposals": 1} and accepted[1][0].entity == "Risks"


def test_store_keeps_pending_proposals_and_what_was_asked(tmp_bundle, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_STAGING", str(tmp_bundle / "staging"))
    store = ProposalStore()
    assert store.list() == [] and store.get("Risks") is None and store.asked(APP) is None
    assert store.save(proposal()) is True and store.save(proposal()) is False
    assert store.get("Risks")[0] == PENDING and store.list()[0][1].entity == "Risks"
    store.mark_applied("Risks")
    assert store.get("Risks")[0] == APPLIED
    store.mark_asked(APP, "abc")
    assert store.asked(APP) == "abc"
    with pytest.raises(FileNotFoundError):
        store.mark_applied("Nope")


def test_the_pipeline_stores_a_proposal_once_and_does_not_ask_again(tmp_bundle, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_STAGING", str(tmp_bundle / "staging"))
    store_source()
    report = propose_types(APP, proposer(answer([RISKS | {"sample_chunks": [3]}])))
    assert report.saved == ["Risks"] and report.chunks_asked == 3 and report.batches == 1
    stored = ProposalStore().get("Risks")[1]
    assert stored.source_path == APP and stored.proposed_by == "okf-type-proposal-agent/fake"
    text = format_proposals(report)
    assert "proposed Risks (pending)" in text and "apply_type_proposal Risks" in text
    again = propose_types(APP, proposer())  # no scripted answers: a call would fail
    assert again.batches == 0 and again.reason.startswith("the chunks that are in no fact are unchanged")
    forced = propose_types(APP, proposer(answer([RISKS])), force=True)
    assert forced.saved == [] and forced.already_known == ["Risks"]


def test_a_failed_batch_is_reported_and_asked_again_next_time(tmp_bundle, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_STAGING", str(tmp_bundle / "staging"))
    store_source()
    report = propose_types(APP, proposer())
    assert report.failed_batches >= 1 and report.saved == [] and ProposalStore().asked(APP) is None
    assert "no new entity type" in report.reason and report.batch_notes


def test_nothing_to_propose_is_the_normal_answer(tmp_bundle, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_STAGING", str(tmp_bundle / "staging"))
    store_source()
    report = propose_types(APP, proposer(answer([])))
    assert report.saved == [] and report.reason == "no new entity type was proposed" and ProposalStore().asked(APP) is not None
    with pytest.raises(FileNotFoundError):
        propose_types("Acme/references/missing.md", proposer())


def test_specs_follow_the_proposal_and_pass_the_scaffold_scripts(tmp_path):
    spec = fact_spec(proposal())
    item = item_spec(proposal())
    assert [f["name"] for f in spec["fields"]] == ["summary", "risks"] and spec["fields"][1]["type"] == "list[RiskEntry]"
    assert spec["imports"] == ["from docfactory.entitymodels.items.risk_entry import RiskEntry"]
    assert [(f["name"], f["default"]) for f in item["fields"]] == [("name", "REQUIRED"), ("likelihood", "''")] and item["fields"][0]["min_length"] == 1
    assert item_spec(proposal(list_name="", item_entity="", item_doc="", item_fields=[])) is None
    entry = json.loads("[" + signals_entry(proposal()) + "]")[0]
    assert entry == {"entity": "Risks", "heading_terms": ["risk register"], "id_patterns": ["\\bRISK-\\d+"], "keywords": ["likelihood", "mitigation"]}
    for name, model_spec, options in (("item", item, []), ("fact", spec, ["--scope", "app"])):  # dry runs write nothing
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(model_spec), encoding="utf-8")
        done = subprocess.run([sys.executable, str(PROJECT_ROOT / ".claude" / "scripts" / "scaffold_model.py"), "entity-model", str(path), *options, "--dry-run"],
                              cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")
        assert done.returncode == 0, done.stdout + done.stderr
    assert not (PROJECT_ROOT / "docfactory" / "entitymodels" / "items" / "risk_entry.py").exists()


def test_signals_are_appended_in_the_files_own_layout():
    before = '[\n  {\n    "entity": "A",\n    "heading_terms": ["a"]\n  }\n]\n'
    after = _add_signals(before, signals_entry(proposal()))
    assert json.loads(after)[1]["entity"] == "Risks" and after.endswith("  }\n]\n") and after.startswith(before[:-3].rstrip()[:20])
    assert "\r\n" in _add_signals(before.replace("\n", "\r\n"), "  {}")


def test_retag_adds_only_the_new_entitys_tags_and_keeps_the_rest(tmp_bundle, monkeypatch):
    store_source()
    signals = EntitySignals(entity="Risks", heading_terms=["risk register"], id_patterns=[r"\bRISK-\d+"], keywords=["likelihood", "mitigation"])
    monkeypatch.setattr("docfactory.ingest.retag_entity.load_signals", lambda: [signals])
    outcomes = retag_entity("Risks")
    assert outcomes == {APP: "1 new tags"}
    tags = {(t.chunk_no, t.entity) for t in SourceStore().read(APP).tags}
    assert tags == {(2, "FunctionalRequirements"), (3, "Risks")}
    assert retag_entity("Risks") == {APP: "0 new tags"}
    with pytest.raises(ValueError, match="no tagging signals"):
        retag_entity("Nothing")


def test_applying_an_unknown_or_applied_proposal_is_refused_without_touching_anything(tmp_bundle, monkeypatch, capsys):
    monkeypatch.setenv("DOCFACTORY_STAGING", str(tmp_bundle / "staging"))
    with pytest.raises(FileNotFoundError):
        apply_proposal("Risks")
    ProposalStore().save(proposal())
    ProposalStore().mark_applied("Risks")
    assert apply_main(["Risks"]) == 1 and "applied already" in capsys.readouterr().out
    assert apply_main(["--list"]) == 0 and "Risks (applied)" in capsys.readouterr().out
    assert not (PROJECT_ROOT / "docfactory" / "entitymodels" / "facts" / "risks.py").exists()
