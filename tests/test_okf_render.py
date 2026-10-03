"""Deterministic OKF frontmatter and body rendering."""
import json

from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord
from docfactory.models.fact_source import FactSource
from docfactory.models.fact_status import FactStatus
from docfactory.models.fact_verification import FactVerification
from docfactory.okf_body import render_body
from docfactory.okf_frontmatter import render_frontmatter, type_name

yaml = __import__("pytest").importorskip("yaml")


def _record(**changes):
    base = dict(key="KitchenHQ.Architecture", value="{}", hashcode="h", completeness=62.5, version=3,
                generated_by="seed", generated_at="2026-10-03T10:00:00Z")
    return FactRecord(**{**base, **changes})


def test_type_is_the_model_name_in_words():
    assert type_name("ApplicationOverview") == "Application Overview"
    assert type_name("Slo") == "Slo"
    assert type_name("NonFunctionalRequirements") == "Non Functional Requirements"


def test_minimal_frontmatter_is_parseable_and_has_type_and_derived_title():
    text = render_frontmatter(_record(), "Architecture", FactMeta(generated_by="seed"))
    data = yaml.safe_load(text)
    assert data["type"] == "Architecture" and data["title"] == "KitchenHQ.Architecture"
    assert data["status"] == "draft" and data["fact_key"] == "KitchenHQ.Architecture"
    assert data["version"] == 3 and data["completeness"] == 62.5
    assert data["generated"]["by"] == "seed" and str(data["generated"]["at"]).startswith("2026-10-03")
    assert not {"description", "tags", "sources", "verified", "stale_after"} & set(data)  # empty families are left out


def test_full_frontmatter_carries_every_okf_family():
    meta = FactMeta(
        generated_by="okf-extraction-agent/m", title="Kitchen: \"HQ\" architecture", description="Three services.",
        tags=["architecture", "prod"], stale_after="2027-01-01T00:00:00Z",
        sources=[FactSource(resource="KitchenHQ/srs.pdf", id="srs", title="SRS", last_modified="2026-09-01T00:00:00Z"),
                 FactSource(resource="https://example.com/x")],
    )
    record = _record(stale_after=meta.stale_after, verified=[FactVerification(by="human:test-user", at="2026-10-04T08:00:00Z")],
                     status=FactStatus.STABLE)
    data = yaml.safe_load(render_frontmatter(record, "Architecture", meta))
    assert data["title"] == 'Kitchen: "HQ" architecture' and data["description"] == "Three services."
    assert data["tags"] == ["architecture", "prod"]
    assert data["sources"][0]["resource"] == "KitchenHQ/srs.pdf" and data["sources"][0]["id"] == "srs"
    assert data["sources"][1] == {"resource": "https://example.com/x"}
    assert data["verified"][0]["by"] == "human:test-user" and data["status"] == "stable"
    assert str(data["stale_after"]).startswith("2027-01-01")


def test_frontmatter_is_deterministic():
    meta = FactMeta(generated_by="seed", tags=["a"])
    assert render_frontmatter(_record(), "Architecture", meta) == render_frontmatter(_record(), "Architecture", meta)


def test_body_has_title_and_a_section_per_answered_field_and_leaves_empty_ones_out():
    value = json.dumps({"name": "KitchenHQ", "empty": "", "none": None, "no_items": [], "owners": ["Ana", "Bo"], "ok": True,
                        "unused": {"reason": "single tenant"}})
    body = render_body("Kitchen", value)
    assert body.startswith("# Kitchen\n\n## Name\n\nKitchenHQ\n")
    assert "## Owners\n\n- Ana\n- Bo" in body and "## Ok\n\nyes" in body and "## Unused\n\nN/A - single tenant" in body
    assert "Empty" not in body and "None" not in body and "No items" not in body


def test_body_renders_nested_items_as_indented_bullets_and_is_deterministic():
    value = json.dumps({"environments": [{"name": "prod", "regions": ["eu"], "owner": {"team": "ops"}}, {"name": "dev"}]})
    body = render_body("T", value)
    assert body == render_body("T", value)
    assert ("## Environments\n\n- Item 1\n  - **Name:** prod\n  - **Regions:**\n    - eu\n  - **Owner:**\n    - **Team:** ops\n- Item 2\n  - **Name:** dev\n") in body
