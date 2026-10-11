"""Contribution concepts: what each ingested original contributed to a fact (Step 4 of the OKF bundle redesign)."""
import pytest

from docfactory.bundle import paths
from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.contribution_file_parse import parse_contribution_file
from docfactory.bundle.contribution_file_render import render_contribution_file
from docfactory.bundle.contribution_store import ContributionStore
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.bundle.paths import EXISTING_RESOURCE
from docfactory.canonical import sha256_hex

KEY = "Acme.FunctionalRequirements"
SRS = "Acme/references/srs.pdf"


@pytest.fixture
def store(tmp_bundle):
    return ContributionStore()


def _file(store, key=KEY, resource=SRS):
    return store.root / paths.contribution_relpath(key, resource)


def test_a_contribution_round_trips_as_canonical_json(store):
    saved = store.save(KEY, SRS, {"summary": "S", "requirements": []}, "a" * 64, "One line.", "okf-extraction-agent/fake", "2026-10-04T10:00:00Z")
    assert saved.value_json == '{"requirements":[],"summary":"S"}' and saved.hashcode == sha256_hex(saved.value_json)
    assert (saved.chunks_hash, saved.description, saved.generated_by, saved.timestamp) == ("a" * 64, "One line.", "okf-extraction-agent/fake", "2026-10-04T10:00:00Z")
    assert store.get(KEY, SRS) == saved
    assert parse_contribution_file(render_contribution_file(saved)) == saved


def test_the_file_is_an_okf_concept_beside_the_source(store):
    store.save(KEY, SRS, {"requirements": []}, "a" * 64, "One line.", "okf-extraction-agent/fake", "2026-10-04T10:00:00Z")
    assert _file(store) == store.root / "Acme" / "sources" / "srs.pdf" / "FunctionalRequirements.md"
    text = _file(store).read_text(encoding="utf-8")
    front = load_frontmatter(text.split("---\n")[1])
    assert front["type"] == "Contribution" and front["description"] == "One line." and front["sources"] == [{"resource": SRS}]
    assert front["generated"] == {"by": "okf-extraction-agent/fake", "at": "2026-10-04T10:00:00Z"} and front["fact_key"] == KEY
    assert "\n# Value\n\n```json\n" in text


def test_saving_again_replaces_the_files_contribution_and_the_log_records_changes_only(store):
    store.save(KEY, SRS, {"summary": "old"}, None, None, "x", "2026-10-04T10:00:00Z")
    store.save(KEY, SRS, {"summary": "old"}, None, None, "x", "2026-10-04T10:00:00Z")
    store.save(KEY, SRS, {"summary": "new"}, None, None, "x", "2026-10-05T10:00:00Z")
    assert [c.value_json for c in store.list(KEY)] == ['{"summary":"new"}']
    log = (store.root / "log.md").read_text(encoding="utf-8")
    assert log.count("* **Creation**") == 1 and log.count("* **Update**") == 1


def test_list_by_key_or_resource_and_remove(store):
    store.save(KEY, "Acme/references/a.pdf", {"summary": "a"}, None, None, "x", "2026-10-04T10:00:00Z")
    store.save(KEY, "Acme/references/b.pdf", {"summary": "b"}, None, None, "x", "2026-10-04T10:00:00Z")
    store.save("Acme.Architecture", "Acme/references/a.pdf", {"notes": "n"}, None, None, "x", "2026-10-04T10:00:00Z")
    assert [c.resource for c in store.list(KEY)] == ["Acme/references/a.pdf", "Acme/references/b.pdf"]
    assert [c.fact_key for c in store.list(resource="Acme/references/a.pdf")] == ["Acme.Architecture", KEY]
    assert len(store.list()) == 3
    store.remove(KEY, "Acme/references/a.pdf")
    assert store.get(KEY, "Acme/references/a.pdf") is None and len(store.list()) == 2
    store.remove(KEY, "Acme/references/a.pdf")  # removing what is not there is fine
    assert "* **Deprecation**" in (store.root / "log.md").read_text(encoding="utf-8")


def test_removing_the_last_contribution_of_a_file_removes_its_folder(store):
    store.save(KEY, SRS, {"summary": "a"}, None, None, "x", "2026-10-04T10:00:00Z")
    store.remove(KEY, SRS)
    assert not _file(store).parent.exists()


def test_the_existing_contribution_has_no_source_and_sits_in_the_scope_folder(store):
    saved = store.save("Shared.Kpis", EXISTING_RESOURCE, {"kpis": []}, None, None, "seed", "2026-10-04T10:00:00Z")
    assert saved.resource == EXISTING_RESOURCE
    assert _file(store, "Shared.Kpis", EXISTING_RESOURCE) == store.root / "Shared" / "sources" / "(existing)" / "Kpis.md"
    assert store.get("Shared.Kpis", EXISTING_RESOURCE) == saved
    assert load_frontmatter(_file(store, "Shared.Kpis", EXISTING_RESOURCE).read_text(encoding="utf-8").split("---\n")[1])["sources"] == []


def test_a_contribution_edited_outside_the_system_is_refused(store):
    store.save(KEY, SRS, {"summary": "S"}, None, None, "x", "2026-10-04T10:00:00Z")
    path = _file(store)
    path.write_text(path.read_text(encoding="utf-8").replace('"summary": "S"', '"summary": "Hacked"'), encoding="utf-8")
    with pytest.raises(BundleError, match="edited outside the system"):
        store.get(KEY, SRS)
    with pytest.raises(BundleError):
        store.list()


@pytest.mark.parametrize("key,resource", [("Acme", SRS), ("Acme.Components.api.Sop", SRS), (KEY, "srs.pdf"), (KEY, "Acme/srs.pdf")])
def test_only_scope_entity_keys_and_scope_references_name_resources_are_accepted(key, resource):
    with pytest.raises(ValueError):
        paths.contribution_relpath(key, resource)


def test_contributions_are_not_listed_as_facts_or_sources(store):
    store.save(KEY, SRS, {"summary": "S"}, None, None, "x", "2026-10-04T10:00:00Z")
    BundleStore().write_fact("Acme.ApplicationOverview", {"application_name": "Acme", "purpose": "Books rooms."})
    assert [r.key for r in BundleStore().list_facts()] == ["Acme.ApplicationOverview"]
