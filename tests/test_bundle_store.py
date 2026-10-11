"""BundleStore: facts as OKF concept files (frontmatter + validated JSON), written only by the store."""
import json
from pathlib import Path

import pytest

from docfactory import clock
from docfactory.bundle import paths
from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.fact_file_parse import parse_fact_file
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_source import FactSource
from docfactory.models.save_action import SaveAction
from tests.test_samples import MODEL_BY_FOLDER, SAMPLE_FILES

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "json"
KEY = "ReadmeForge.ApplicationOverview"


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.ENV_VAR, str(tmp_path / "bundle"))
    return BundleStore()


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    times = iter(f"2026-10-{day:02d}T10:00:00Z" for day in range(1, 29))
    monkeypatch.setattr(clock, "now_iso", lambda: next(times))


def _payload(name="readmeforge_minimal.json"):
    return json.loads((SAMPLES / "application_overview" / name).read_text(encoding="utf-8"))


def _meta(**changes):
    return FactMeta(**{"generated_by": "okf-extraction-agent/m", "title": "ReadmeForge overview", "description": "What it is.",
                       "tags": ["overview"], "sources": [FactSource(resource="ReadmeForge/references/srs.pdf", id="srs")], **changes})


def _file(store, key=KEY):
    return store.root / paths.fact_relpath(key)


def test_created_fact_is_an_okf_concept_file(store):
    result = store.write_fact(KEY, _payload(), _meta())
    assert (result.ok, result.action, result.version) == (True, SaveAction.CREATED, 1)
    text = _file(store).read_text(encoding="utf-8")
    assert text.startswith("---\ntype: \"Application Overview\"\n")
    front = load_frontmatter(text.split("---\n")[1])
    assert front["fact_key"] == KEY and front["version"] == 1 and front["status"] == "draft"
    assert front["generated"] == {"by": "okf-extraction-agent/m", "at": "2026-10-01T10:00:00Z"}
    assert front["sources"][0]["resource"] == "ReadmeForge/references/srs.pdf"
    assert front["hashcode"] == result.hashcode
    assert "\n# Value\n\n```json\n" in text


def test_the_json_block_round_trips_to_the_same_hash(store):
    payload = _payload("readmeforge_full.json")
    result = store.write_fact(KEY, payload, _meta())
    record = store.read_fact(KEY)
    assert record.hashcode == result.hashcode == sha256_hex(record.value)
    assert record.value == canonical_json(json.loads(record.value))
    assert (record.version, record.type, record.app_id) == (1, "Application Overview", "ReadmeForge")
    assert record.generated_by == "okf-extraction-agent/m" and record.generated_at == "2026-10-01T10:00:00Z"
    assert record.sources[0].id == "srs" and record.tags == ["overview"]


@pytest.mark.parametrize("path", SAMPLE_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_every_sample_payload_round_trips_through_a_fact_file(store, path):
    entity = "".join(part.capitalize() for part in path.parent.name.split("_"))
    key = f"Shared.{entity}" if entity in ("Kpis", "Slo") else f"App.{entity}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = canonical_json(MODEL_BY_FOLDER[path.parent.name].model_validate(payload).model_dump(mode="json"))
    result = store.write_fact(key, payload)
    assert result.ok, result.errors
    record = store.read_fact(key)
    assert record.value == expected and record.hashcode == sha256_hex(expected) == result.hashcode


def test_same_payload_is_unchanged_and_writes_nothing(store):
    store.write_fact(KEY, _payload(), _meta())
    before = _file(store).read_bytes()
    log_before = (store.root / "log.md").read_bytes()
    again = store.write_fact(KEY, _payload(), _meta())
    assert (again.action, again.version) == (SaveAction.UNCHANGED, 1)
    assert _file(store).read_bytes() == before and (store.root / "log.md").read_bytes() == log_before


def test_changed_payload_is_updated_then_changing_back_is_a_new_change(store):
    store.write_fact(KEY, _payload("readmeforge_minimal.json"))
    assert store.write_fact(KEY, _payload("readmeforge_full.json")).version == 2
    assert store.write_fact(KEY, _payload("readmeforge_minimal.json")).version == 3


def test_new_value_is_a_fresh_unverified_draft(store):
    store.write_fact(KEY, _payload("readmeforge_minimal.json"), _meta())
    store.write_fact(KEY, _payload("readmeforge_full.json"), _meta(generated_by="okf-extraction-agent/other"))
    record = store.read_fact(KEY)
    assert (record.status.value, record.verified, record.generated_by) == ("draft", [], "okf-extraction-agent/other")
    assert record.generated_at == "2026-10-02T10:00:00Z"


def test_same_value_with_new_metadata_refreshes_in_place_without_a_version_bump(store):
    store.write_fact(KEY, _payload(), _meta())
    result = store.write_fact(KEY, _payload(), _meta(title="New title", tags=["a", "b"]))
    record = store.read_fact(KEY)
    assert (result.action, record.version, record.title, record.tags) == (SaveAction.UNCHANGED, 1, "New title", ["a", "b"])
    assert record.generated_at == "2026-10-01T10:00:00Z"


def test_a_deleted_file_is_a_deleted_fact_and_saving_again_creates_it(store):
    store.write_fact(KEY, _payload(), _meta())
    _file(store).unlink()
    assert store.read_fact(KEY) is None
    again = store.write_fact(KEY, _payload(), _meta())
    assert (again.action, again.version) == (SaveAction.CREATED, 1)


def test_invalid_payload_is_rejected_with_feedback_and_nothing_is_written(store):
    result = store.write_fact(KEY, {"application_name": "x", "bogus": 1})
    assert result.action == SaveAction.REJECTED and not result.ok
    assert {error.error_type for error in result.errors} >= {"extra_forbidden"}
    assert any(error.question for error in result.errors)
    assert not store.root.exists()


@pytest.mark.parametrize("key", ["Nonsense", "ReadmeForge.Unknown", "Shared.ApplicationOverview", "ReadmeForge.Kpis", "ReadmeForge.sources.ApplicationOverview"])
def test_a_key_matching_no_fact_pattern_is_rejected(store, key):
    result = store.write_fact(key, _payload())
    assert result.action == SaveAction.REJECTED and result.errors[0].error_type == "key_pattern_mismatch"


def test_an_unsafe_key_segment_is_rejected(store):
    result = store.write_fact("ReadmeForge.Components.a:b.Architecture", {})
    assert result.errors[0].error_type == "key_unsafe_path"


def test_component_keys_nest_and_store_the_application(store, tmp_path):
    key = "ReadmeForge.Components.api.ApplicationOverview"
    assert store.write_fact(key, _payload()).ok
    assert (store.root / "ReadmeForge" / "Components" / "api" / "ApplicationOverview.md").is_file()
    assert store.read_fact(key).app_id == "ReadmeForge"


def test_shared_facts_have_no_application(store):
    payload = json.loads(next((SAMPLES / "kpis").glob("*.json")).read_text(encoding="utf-8"))
    assert store.write_fact("Shared.Kpis", payload).ok
    assert store.read_fact("Shared.Kpis").app_id is None


def test_a_file_edited_by_hand_is_refused_on_read_and_on_write(store):
    store.write_fact(KEY, _payload("readmeforge_minimal.json"))
    path = _file(store)
    head, value = path.read_text(encoding="utf-8").split("# Value", 1)
    path.write_text(head + "# Value" + value.replace("ReadmeForge", "Hacked", 1), encoding="utf-8")
    with pytest.raises(BundleError):
        store.read_fact(KEY)
    result = store.write_fact(KEY, _payload("readmeforge_full.json"))
    assert result.action == SaveAction.REJECTED and result.errors[0].error_type == "bundle_file_untrusted"


def test_a_file_that_is_not_a_fact_file_is_refused():
    with pytest.raises(BundleError):
        parse_fact_file("just text\n")


def test_listing_by_application_and_by_source(store):
    store.write_fact(KEY, _payload(), _meta())
    store.write_fact("Other.ApplicationOverview", _payload())
    assert [r.key for r in store.list_facts()] == ["Other.ApplicationOverview", KEY]
    assert [r.key for r in store.list_facts("Other")] == ["Other.ApplicationOverview"]
    assert [r.key for r in store.list_facts_by_source("ReadmeForge/references/srs.pdf")] == [KEY]


def test_originals_and_source_concepts_are_not_listed_as_facts(store):
    store.write_fact(KEY, _payload())
    (store.root / "ReadmeForge" / "sources").mkdir(parents=True)
    (store.root / "ReadmeForge" / "sources" / "srs.md").write_text("---\ntype: Source\n---\n", encoding="utf-8")
    assert [r.key for r in store.list_facts()] == [KEY]


def test_log_and_index_follow_okf_and_are_stable(store):
    store.write_fact(KEY, _payload("readmeforge_minimal.json"), _meta())
    store.write_fact(KEY, _payload("readmeforge_full.json"), _meta())
    log = (store.root / "log.md").read_text(encoding="utf-8")
    assert log.startswith("# Directory Update Log\n\n## 2026-10-02\n* **Update**") or "## 2026-10-02" in log.splitlines()
    assert log.index("## 2026-10-02") < log.index("## 2026-10-01")
    assert "* **Creation**: [ReadmeForge.ApplicationOverview](/ReadmeForge/ApplicationOverview.md) v1 by okf-extraction-agent/m" in log
    index = (store.root / "index.md").read_text(encoding="utf-8")
    assert index.startswith('---\nokf_version: "0.2"\n---\n')
    assert "# ReadmeForge" in index and "[ReadmeForge overview](/ReadmeForge/ApplicationOverview.md) - What it is." in index


def test_conformance_every_concept_file_has_parseable_frontmatter_and_a_type(store):
    store.write_fact(KEY, _payload("readmeforge_full.json"), _meta())
    store.write_fact("Shared.Slo", json.loads(next((SAMPLES / "slo").glob("*.json")).read_text(encoding="utf-8")))
    for path in store.root.rglob("*.md"):
        if path.name in paths.RESERVED_FILES:
            continue
        front = load_frontmatter(path.read_text(encoding="utf-8").split("---\n")[1])
        assert front["type"]


def test_open_questions_section_lists_what_is_unanswered(store):
    store.write_fact(KEY, _payload("readmeforge_minimal.json"))
    text = _file(store).read_text(encoding="utf-8")
    assert "# Open questions: ReadmeForge.ApplicationOverview" in text
    assert text.index("# Value") < text.index("# Open questions")
    assert store.read_fact(KEY) is not None  # the extra section does not disturb reading


def test_instants_stay_text_when_read(store):
    store.write_fact(KEY, _payload(), _meta(stale_after="2026-12-31T00:00:00Z"))
    record = store.read_fact(KEY)
    assert record.stale_after == "2026-12-31T00:00:00Z" and record.generated_at == "2026-10-01T10:00:00Z"
