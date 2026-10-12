"""EntityStore: the entity graph of a scope written as a whole; versions, removal, index, tamper check, OKF frontmatter."""
import pytest

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.entity_store import EntityStore
from docfactory.bundle.fact_file_parse import split_frontmatter
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.bundle.paths import bundle_root, entity_relpath
from docfactory.models.entity_evidence import EntityEvidence
from docfactory.models.entity_link import EntityLink
from docfactory.models.entity_record import EntityRecord

T1, T2 = "2026-10-12T10:00:00Z", "2026-10-13T10:00:00Z"
ENGINE = EntityRecord(entity_id="Component/matching-engine", scope="App", type="Component", name="Matching Engine", aliases=["AI Engine"],
                      summary="Ranks candidates.", evidence=[EntityEvidence(resource="App/references/a.md", chunk_no=3, heading="4. Components")],
                      links=[EntityLink(target="DataStore/search-index", relation="depends on", kind="depends_on", resources=["App/references/a.md"])])
INDEX = EntityRecord(entity_id="DataStore/search-index", scope="App", type="DataStore", name="Search Index")


def meta(record):
    text = (bundle_root() / entity_relpath("App", record.entity_id)).read_text(encoding="utf-8")
    return load_frontmatter(split_frontmatter(text)[0]), text


def test_the_path():
    assert entity_relpath("App", "Component/matching-engine") == "App/entities/Component/matching-engine.md"
    for bad in ("matching-engine", "Component/a/b", "Component/.."):
        with pytest.raises(ValueError):
            entity_relpath("App", bad)


def test_write_read_and_okf_frontmatter(tmp_bundle):
    done = EntityStore().write_all("App", [ENGINE, INDEX], T1)
    assert done == {"created": ["Component/matching-engine", "DataStore/search-index"], "updated": [], "removed": []}
    assert EntityStore().list("App") == [ENGINE, INDEX] and EntityStore().get("App", INDEX.entity_id) == INDEX
    fm, text = meta(ENGINE)
    assert fm["type"] == "Component" and fm["title"] == "Matching Engine" and fm["status"] == "draft" and fm["version"] == 1
    assert fm["sources"] == [{"resource": "App/references/a.md"}] and fm["verified"] == []
    assert "- depends on [Search Index](/App/entities/DataStore/search-index.md)" in text
    index = (bundle_root() / "App" / "entities" / "index.md").read_text(encoding="utf-8")
    assert "## Component" in index and "[Matching Engine](/App/entities/Component/matching-engine.md) - Ranks candidates." in index
    assert BundleStore().list_facts() == []  # entities are not facts


def test_versions_and_removal(tmp_bundle):
    store = EntityStore()
    store.write_all("App", [ENGINE, INDEX], T1)
    done = store.write_all("App", [ENGINE.model_copy(update={"summary": "New."}), INDEX], T2)
    assert done == {"created": [], "updated": ["Component/matching-engine"], "removed": []}
    assert meta(ENGINE)[0]["version"] == 2 and meta(INDEX)[0]["version"] == 1
    assert meta(INDEX)[0]["generated"]["at"] == T1  # unchanged: untouched
    done = store.write_all("App", [INDEX], T2)
    assert done["removed"] == ["Component/matching-engine"] and store.list("App") == [INDEX]
    assert not (bundle_root() / "App" / "entities" / "Component").exists()


def test_an_edited_file_is_refused(tmp_bundle):
    EntityStore().write_all("App", [ENGINE], T1)
    path = bundle_root() / entity_relpath("App", ENGINE.entity_id)
    path.write_text(path.read_text(encoding="utf-8").replace('"Ranks candidates."\n  ', '"Ranks everything."\n  ', 1).replace('"summary": "Ranks candidates."', '"summary": "Other."'), encoding="utf-8")
    with pytest.raises(BundleError, match="edited outside the system"):
        EntityStore().list("App")
