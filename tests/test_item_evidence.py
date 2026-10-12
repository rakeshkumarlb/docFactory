"""Where the document names an item, and the further statements about it, as readable sections of its file."""
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.paths import bundle_root
from docfactory.entitymodels.facts.application_overview import ApplicationOverview
from docfactory.entitymodels.facts.architecture import Architecture
from docfactory.extract.evidence import attach_evidence, places_of
from docfactory.models.doc_chunk import DocChunk


def chunk(no, heading, text):
    return DocChunk(chunk_no=no, heading=heading, text=text, text_hash="0" * 64)


HARDWARE = chunk(40, "4.2. Hardware Interfaces", "The system shall interface with:\n1) Server Infrastructure\n- Application servers - Database servers\n2) Network Infrastructure\n- Load balancers")


def test_the_line_naming_an_item_is_its_evidence_with_the_group_it_is_listed_under():
    assert places_of("Application servers", [HARDWARE]) == ["4.2. Hardware Interfaces (chunk 40): 1) Server Infrastructure / - Application servers - Database servers"]
    assert places_of("load BALANCERS", [HARDWARE]) == ["4.2. Hardware Interfaces (chunk 40): 2) Network Infrastructure / - Load balancers"]
    assert places_of("Firewalls", [HARDWARE]) == [] and places_of("", [HARDWARE]) == []


def test_evidence_is_capped_in_places_and_length():
    long = chunk(1, "H", "\n".join(f"Step {n}: use the Gateway {'x' * 400}" for n in range(6)))
    found = places_of("Gateway", [long])
    assert len(found) == 3 and all(len(f) < 340 for f in found) and found[0].endswith("...")


def test_code_sets_the_evidence_of_every_item_and_replaces_what_the_model_wrote():
    stated = {"components": [{"name": "Application servers", "evidence": ["invented"]}, {"name": "Unknown"}], "notes": "kept"}
    result = attach_evidence(Architecture, stated, [HARDWARE])
    assert result["components"][0]["evidence"] == ["4.2. Hardware Interfaces (chunk 40): 1) Server Infrastructure / - Application servers - Database servers"]
    assert result["components"][1]["evidence"] == [] and result["notes"] == "kept"
    assert stated["components"][0]["evidence"] == ["invented"]  # the input is not changed
    assert attach_evidence(ApplicationOverview, {"purpose": "p"}, [HARDWARE]) == {"purpose": "p"}  # no list of items with evidence


def test_an_item_file_shows_what_else_the_document_says_and_where(tmp_bundle):
    component = {"name": "Application servers", "additional_information": ["Listed under Server Infrastructure."],
                 "evidence": ["4.2. Hardware Interfaces (chunk 40): - Application servers"]}
    BundleStore().write_fact("Acme.Architecture", {"components": [component, {"name": "Bare"}]})
    text = (bundle_root() / "Acme/Architecture/components/Application-servers.md").read_text(encoding="utf-8")
    assert "# Additional information\n\n* Listed under Server Infrastructure.\n" in text
    assert "# Evidence\n\n* 4.2. Hardware Interfaces (chunk 40): - Application servers\n" in text
    assert text.index("# Value") < text.index("# Additional information") < text.index("# Evidence") < text.index("# Links")
    bare = (bundle_root() / "Acme/Architecture/components/Bare.md").read_text(encoding="utf-8")
    assert "# Additional information" not in bare and "# Evidence" not in bare
    assert BundleStore().read_fact("Acme.Architecture").value.count("Listed under Server Infrastructure.") == 1  # the JSON stays the truth
