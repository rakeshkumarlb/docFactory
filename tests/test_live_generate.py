"""Opt-in live run of the needs-list call (Phase 4): `pytest -m live tests/test_live_generate.py`.

Generates an SRS over a small app whose facts leave gaps (requirements without rationale or acceptance criteria, no Shared.Slo), with
the real model phrasing the needs list. Uses default_client() (Ollama Cloud, local Ollama, or DOCFACTORY_PROVIDER=anthropic). Skipped
when the chosen server is not reachable.
"""
import json

import pytest

from docfactory import db
from docfactory.agents.model_client_factory import default_client
from docfactory.agents.needs_writer import NeedsWriter
from docfactory.documentmodels.shared.missing_info import MissingInfo
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.functional_requirements_saver import FunctionalRequirementsSaver
from docfactory.generation.generate_document import format_reports, generate
from tests.live_support import llm_available as _llm_available  # also loads .env

pytestmark = [pytest.mark.live, pytest.mark.skipif(not _llm_available(), reason="LLM server not reachable")]

APP = "ShiftPlanner"


def test_the_needs_list_of_an_srs_covers_every_gap(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_OUTPUT", str(tmp_path / "output"))
    assert ApplicationOverviewSaver().save(f"{APP}.ApplicationOverview", {
        "application_name": "ShiftPlanner", "purpose": "Lets hospital wards plan nurse shifts and swap them fairly.",
        "target_users": ["Ward managers", "Nurses"]}).ok
    assert FunctionalRequirementsSaver().save(f"{APP}.FunctionalRequirements", {"requirements": [
        {"id": "FR-01", "title": "Plan shifts", "description": "The system SHALL let ward managers plan shifts four weeks ahead.", "priority": "MUST"},
        {"id": "FR-02", "title": "Swap shifts", "description": "The system SHALL let nurses request a shift swap.", "priority": "MUST"},
        {"id": "FR-03", "title": "Notify", "description": "The system SHOULD notify nurses of changes to their shifts."},
    ]}).ok

    report = generate(APP, "SRS", NeedsWriter(default_client()))
    print(format_reports(APP, [report]))
    print((tmp_path / "output" / APP / "SRS.missing.md").read_text(encoding="utf-8"))

    info = MissingInfo.model_validate(json.loads(db.get_row("DocumentOutputs", f"{APP}.Outputs.SRS.MissingInfo")["Value"]))
    assert report.needs_origin == "llm", report.needs_note
    assert {n for need in info.needs for n in need.gaps} == {gap.number for gap in info.gaps}
    assert all(need.audience.strip() for need in info.needs)
    assert len(info.needs) <= len(info.gaps)
