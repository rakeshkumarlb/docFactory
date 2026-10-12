"""The relationship graph: structural, mentioned and stated edges, broken links, the graph concept and the extraction checks (redesign step 6)."""
import json

import pytest

from docfactory import clock
from docfactory.agents.run_graph import main, write_graphs
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.graph_builder import GraphBuilder
from docfactory.bundle.graph_queries import backlinks, broken_links, neighbours, outgoing, semantic_edges, summary, unlinked
from docfactory.bundle.graph_store import GraphStore, graph_body, graph_relpath
from docfactory.bundle.paths import bundle_root
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.extract.grounding import relation_problems
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_source import FactSource
from docfactory.tools.extraction_tools import extraction_package

FR = "/Acme/FunctionalRequirements/requirements/"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-11T10:00:00Z")


def req(id, text, relations=None):
    return {"id": id, "title": f"Title {id}", "description": text} | ({"relations": relations} if relations else {})


def store_requirements(*requirements):
    meta = FactMeta(generated_by="t/1", title="Acme functional requirements", sources=[FactSource(resource="Acme/references/srs.md")])
    BundleStore().write_fact("Acme.FunctionalRequirements", {"requirements": list(requirements)}, meta)


def graph():
    return GraphBuilder().build("Acme")


def test_structural_edges_follow_the_layout(tmp_bundle):
    store_requirements(req("FR-01", "The system SHALL log in."))
    g = graph()
    pairs = {(e.source, e.kind, e.target) for e in g.edges}
    assert (FR + "FR-01.md", "part_of", "/Acme/FunctionalRequirements.md") in pairs
    assert ("/Acme/FunctionalRequirements.md", "derived_from", "/Acme/sources/srs.md.md") in pairs
    assert {n.type for n in g.nodes} == {"Requirement", "Functional Requirements", "Source"}
    assert [n.identifier for n in g.nodes if n.identifier] == ["FR-01"]
    assert all(e.origin == "structural" for e in g.edges) and semantic_edges(g) == []


def test_an_identifier_named_in_the_text_is_a_mentioned_edge(tmp_bundle):
    store_requirements(req("FR-01", "Log in."), req("FR-02", "After FR-01 the system SHALL show the account; see also fr-02 and FR-99."), req("A", "Mentions FR-01"))
    mentioned = [(e.source, e.target) for e in graph().edges if e.origin == "mentioned"]
    assert mentioned == [(FR + "A.md", FR + "FR-01.md"), (FR + "FR-02.md", FR + "FR-01.md")]  # itself, unknown FR-99 and words without digits are not edges


def test_a_stated_relation_is_an_edge_and_an_unknown_target_a_broken_link(tmp_bundle):
    store_requirements(
        req("FR-01", "Log in."),
        req("FR-02", "Show the account.", [{"target": "FR-01", "kind": "depends_on", "evidence": "after login"}, {"target": "FR-77", "kind": "refines"}]))
    g = graph()
    stated = [e for e in g.edges if e.origin == "stated"]
    assert [(e.kind, e.target, e.resolved, e.evidence) for e in stated] == [("depends_on", FR + "FR-01.md", True, "after login"), ("refines", "FR-77", False, "")]
    assert [e.target for e in broken_links(g)] == ["FR-77"]
    assert backlinks(g, FR + "FR-01.md")[0].source == FR + "FR-02.md" and len(outgoing(g, FR + "FR-02.md")) == 3
    assert neighbours(g, FR + "FR-01.md") == ["/Acme/FunctionalRequirements.md", FR + "FR-02.md"]
    assert [n.identifier for n in unlinked(g)] == []


def test_items_no_text_relationship_touches_are_counted(tmp_bundle):
    store_requirements(req("FR-01", "Log in."), req("FR-02", "Log out."))
    g = graph()
    assert [n.identifier for n in unlinked(g)] == ["FR-01", "FR-02"]
    assert summary(g) == "Acme: 4 concepts, 3 relationships (3 structural, 0 mentioned, 0 stated), 0 broken links, 2 items with no relationship in the text"


def test_the_graph_concept_is_written_once_and_is_not_a_fact(tmp_bundle):
    store_requirements(req("FR-01", "Log in."), req("FR-02", "After FR-01 show the account.", [{"target": "FR-77", "kind": "refines"}]))
    g = graph()
    assert GraphStore().write(g) is True and GraphStore().write(g) is False
    text = (bundle_root() / graph_relpath("Acme")).read_text(encoding="utf-8")
    assert text.startswith('---\ntype: "Relationship Graph"') and "| FR-02 |" in text.replace("[FR-02](/Acme/FunctionalRequirements/requirements/FR-02.md)", "FR-02")
    assert "```mermaid" in text and "-->|references|" in text and "FR-77 (not stored)" in text and "* FR-02 refines FR-77" in text
    assert [f.key for f in BundleStore().list_facts()] == ["Acme.FunctionalRequirements"]  # graph/relationships.md is not read as a fact
    assert graph_body(g) == graph_body(graph())  # same graph, same bytes
    with pytest.raises(ValueError):
        graph_relpath("a/b")


def test_run_graph_writes_every_scope(tmp_bundle, capsys):
    assert main([]) == 0 and "no facts" in capsys.readouterr().out
    store_requirements(req("FR-01", "Log in."))
    BundleStore().write_fact("Shared.Kpis", {"kpis": [{"name": "Uptime", "definition": "Share of time the service answers.", "unit": "%", "target": ">= 99%"}]})
    lines = write_graphs()
    assert [line.split(":")[0] for line in lines] == ["Acme", "Shared"]
    assert (bundle_root() / "Acme/graph/relationships.md").is_file() and (bundle_root() / "Shared/graph/relationships.md").is_file()
    assert GraphBuilder().scopes() == ["Acme", "Shared"]


def test_relation_problems_name_self_references_and_repeated_targets():
    ok = {"requirements": [req("FR-01", "x", [{"target": "FR-02", "kind": "refines"}])]}
    assert relation_problems(FunctionalRequirements, ok) == []
    own = {"requirements": [req("FR-01", "x", [{"target": "fr-01.", "kind": "refines"}])]}
    assert "related to itself" in relation_problems(FunctionalRequirements, own)[0]
    twice = {"requirements": [req("FR-01", "x", [{"target": "FR-02", "kind": "refines"}, {"target": "FR-02", "kind": "implements"}])]}
    assert "twice" in relation_problems(FunctionalRequirements, twice)[0]
    assert relation_problems(FunctionalRequirements, {"summary": "s"}) == []


def test_the_extraction_tool_checks_relations_against_the_text():
    text = "[chunk 1] Login\nFR-01. | Log in.\nFR-02. | After FR-01 show the account."
    accepted = []
    package = extraction_package(FunctionalRequirements, text, accepted)
    good = {"requirements": [req("FR-01", "Log in."), req("FR-02", "After FR-01 show the account.", [{"target": "FR-01", "kind": "depends_on", "evidence": "After FR-01"}])]}
    assert package.call("submit_extraction", {"values": good})["ok"] is True
    unknown = {"requirements": [req("FR-02", "After FR-01 show the account.", [{"target": "FR-55", "kind": "depends_on"}])]}
    refused = package.call("submit_extraction", {"values": unknown})
    assert refused["ok"] is False and "FR-55" in refused["error"]
    own = {"requirements": [req("FR-02", "After FR-01 show the account.", [{"target": "FR-02", "kind": "refines"}])]}
    assert "itself" in package.call("submit_extraction", {"values": own})["error"]
    bad_kind = {"requirements": [req("FR-02", "After FR-01 show the account.", [{"target": "FR-01", "kind": "likes"}])]}
    assert package.call("submit_extraction", {"values": bad_kind})["ok"] is False
    assert len(accepted) == 1 and json.dumps(accepted[0][0]).count("depends_on") == 1


def test_relations_stay_out_of_the_rendered_documents_and_the_score(tmp_bundle):
    from docfactory.completeness import completeness
    from docfactory.render import field_lines

    plain = FunctionalRequirements.model_validate({"requirements": [req("FR-01", "Log in.")]})
    related = FunctionalRequirements.model_validate({"requirements": [req("FR-01", "Log in.", [{"target": "FR-02", "kind": "refines"}])]})
    assert completeness(plain) == completeness(related)
    lines = "\n".join(field_lines("Requirements", related.requirements, "table", 2))
    assert "Relations" not in lines and "FR-02" not in lines
    assert "\n".join(field_lines("Requirements", related.requirements, "list", 2)).count("Relations") == 0
