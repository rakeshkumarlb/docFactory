"""One concept file per list item, the fact assembled from its parent and items (redesign step 3)."""
import json

import pytest

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.item_layout import item_slugs, split_fields
from docfactory.bundle.paths import bundle_root
from docfactory.entitymodels.facts.application_overview import ApplicationOverview
from docfactory.entitymodels.facts.architecture import Architecture
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_source import FactSource
from docfactory.models.save_action import SaveAction

KEY = "Acme.FunctionalRequirements"
FOLDER = "Acme/FunctionalRequirements"


def req(id, text=None):
    return {"id": id, "title": f"Title {id}", "description": text or f"The system SHALL do {id}."}


def payload(*ids, summary=None):
    return {"requirements": [req(i) for i in ids]} | ({"summary": summary} if summary else {})


def files():
    return sorted(p.relative_to(bundle_root()).as_posix() for p in (bundle_root() / FOLDER).rglob("*.md")) if (bundle_root() / FOLDER).is_dir() else []


def test_each_item_is_its_own_concept_and_the_parent_holds_the_rest(tmp_bundle):
    result = BundleStore().write_fact(KEY, payload("FR-01", "FR-02", summary="What it does."), FactMeta(generated_by="t/1", sources=[FactSource(resource="Acme/references/a.md")]))
    assert result.action == SaveAction.CREATED and result.version == 1
    assert files() == [f"{FOLDER}/index.md", f"{FOLDER}/requirements/FR-01.md", f"{FOLDER}/requirements/FR-02.md"]
    parent = (bundle_root() / "Acme" / "FunctionalRequirements.md").read_text(encoding="utf-8")
    assert '"summary": "What it does."' in parent and "FR-01" in parent.split("# Items")[1] and '"requirements"' not in parent.split("# Items")[0]
    item = (bundle_root() / FOLDER / "requirements" / "FR-01.md").read_text(encoding="utf-8")
    assert 'type: "Requirement"' in item and 'item_id: "FR-01"' in item and "position: 1" in item and 'fact_key: "Acme.FunctionalRequirements"' in item
    assert "* Part of [" in item and "(/Acme/FunctionalRequirements.md)" in item and "(/Acme/sources/a.md.md)" in item
    index = (bundle_root() / FOLDER / "index.md").read_text(encoding="utf-8")
    assert not index.startswith("---") and "(/Acme/FunctionalRequirements/requirements/FR-02.md)" in index


def test_read_assembles_the_whole_object_in_list_order(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, payload("FR-02", "FR-01", "FR-10"))
    value = json.loads(store.read_fact(KEY).value)
    assert [r["id"] for r in value["requirements"]] == ["FR-02", "FR-01", "FR-10"]
    assert FunctionalRequirements.model_validate(value).requirements[0].id == "FR-02"
    assert [i.item_id for i in store.list_items(KEY)] == ["FR-02", "FR-01", "FR-10"] and store.list_items(KEY, "nothing") == []


def test_same_payload_is_unchanged_and_writes_nothing(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, payload("FR-01", "FR-02"))
    before = {p: (bundle_root() / p).read_bytes() for p in files()}
    assert store.write_fact(KEY, payload("FR-01", "FR-02")).action == SaveAction.UNCHANGED
    assert {p: (bundle_root() / p).read_bytes() for p in files()} == before


def test_only_the_changed_item_gets_a_new_version(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, payload("FR-01", "FR-02"))
    changed = {"requirements": [req("FR-01"), req("FR-02", "The system SHALL do something else.")]}
    assert store.write_fact(KEY, changed).version == 2
    assert {i.item_id: i.version for i in store.list_items(KEY)} == {"FR-01": 1, "FR-02": 2}
    store.write_fact(KEY, payload("FR-01", "FR-02"))  # back again is a new change
    assert {i.item_id: i.version for i in store.list_items(KEY)} == {"FR-01": 1, "FR-02": 3}


def test_an_item_that_leaves_the_list_is_removed(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, payload("FR-01", "FR-02"))
    store.write_fact(KEY, payload("FR-01"))
    assert files() == [f"{FOLDER}/index.md", f"{FOLDER}/requirements/FR-01.md"]
    assert "(items +2 ~0 -0)" in (bundle_root() / "log.md").read_text(encoding="utf-8") and "(items +0 ~0 -1)" in (bundle_root() / "log.md").read_text(encoding="utf-8")
    store.write_fact(KEY, {"requirements": []})  # an emptied list keeps no item files
    assert files() == []
    assert json.loads(store.read_fact(KEY).value)["requirements"] == []


def test_an_edited_item_file_is_refused_on_read_and_on_write(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, payload("FR-01", "FR-02"))
    path = bundle_root() / FOLDER / "requirements" / "FR-02.md"
    path.write_text(path.read_text(encoding="utf-8").replace("SHALL do FR-02", "SHALL do other"), encoding="utf-8")
    with pytest.raises(BundleError, match="FR-02.md.*edited outside"):
        store.read_fact(KEY)
    rejected = store.write_fact(KEY, payload("FR-01"))
    assert rejected.action == SaveAction.REJECTED and rejected.errors[0].error_type == "bundle_file_untrusted"


def test_an_edited_parent_is_refused_even_when_the_items_are_intact(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, payload("FR-01", summary="Original."))
    parent = bundle_root() / "Acme" / "FunctionalRequirements.md"
    parent.write_text(parent.read_text(encoding="utf-8").replace("Original.", "Edited."), encoding="utf-8")
    with pytest.raises(BundleError, match="hashcode"):
        store.read_fact(KEY)


def test_an_extra_or_missing_item_file_breaks_the_assembled_hash(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, payload("FR-01", "FR-02"))
    (bundle_root() / FOLDER / "requirements" / "FR-02.md").unlink()
    with pytest.raises(BundleError, match="hashcode"):
        store.read_fact(KEY)


def test_item_files_are_not_facts_and_facts_without_lists_are_unchanged(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, payload("FR-01", "FR-02"))
    store.write_fact("Acme.ApplicationOverview", {"application_name": "Acme", "purpose": "Does things."})
    assert [f.key for f in store.list_facts()] == ["Acme.ApplicationOverview", KEY]
    assert not split_fields(ApplicationOverview) and not (bundle_root() / "Acme" / "ApplicationOverview").exists()
    index = (bundle_root() / "index.md").read_text(encoding="utf-8")
    assert "FR-01" not in index


def test_a_fact_with_several_lists_splits_each(tmp_bundle):
    assert list(split_fields(Architecture)) == ["components", "data_stores", "integrations"]
    BundleStore().write_fact("Acme.Architecture", {"components": [{"name": "api"}, {"name": "web"}], "integrations": [{"name": "Stripe"}]})
    assert [p for p in files_of("Acme/Architecture")] == ["Acme/Architecture/components/api.md", "Acme/Architecture/components/web.md",
                                                           "Acme/Architecture/index.md", "Acme/Architecture/integrations/Stripe.md"]
    assert [i.item_id for i in BundleStore().list_items("Acme.Architecture", "integrations")] == ["Stripe"]


def files_of(folder):
    return sorted(p.relative_to(bundle_root()).as_posix() for p in (bundle_root() / folder).rglob("*.md"))


def test_unsafe_and_repeated_identifiers_get_distinct_safe_file_names(tmp_bundle):
    assert item_slugs(["FR-01", "fr-01", "a/b: c", "con", ""]) == ["FR-01", "fr-01~2", "a-b-c", "_con", "item"]
    store = BundleStore()
    store.write_fact(KEY, {"requirements": [req("A/B"), req("a/b"), req("A/B")]})
    assert [i.item_id for i in store.list_items(KEY)] == ["A/B", "a/b", "A/B"]
    assert len({i.relpath for i in store.list_items(KEY)}) == 3


def test_delete_fact_removes_parent_items_and_logs_it(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, payload("FR-01"))
    assert store.delete_fact(KEY, "human:test") is True
    assert store.read_fact(KEY) is None and not (bundle_root() / FOLDER).exists()
    assert "**Deprecation**" in (bundle_root() / "log.md").read_text(encoding="utf-8") and "KEY" not in (bundle_root() / "index.md").read_text(encoding="utf-8")
    assert store.delete_fact(KEY) is False and store.delete_fact("not a key") is False


def test_items_carry_their_own_completeness_and_open_questions(tmp_bundle):
    store = BundleStore()
    store.write_fact(KEY, {"requirements": [req("FR-01") | {"rationale": "Because.", "acceptance_criteria": ["It works."], "priority": "MUST"}, req("FR-02")]})
    full, bare = store.list_items(KEY)
    assert full.completeness > bare.completeness
    text = (bundle_root() / FOLDER / "requirements" / "FR-02.md").read_text(encoding="utf-8")
    assert "# Open questions" in text and "rationale" in text
    assert "# Open questions" not in (bundle_root() / FOLDER / "requirements" / "FR-01.md").read_text(encoding="utf-8")
