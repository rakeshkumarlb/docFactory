"""The single-tool needs-list package (Phase 4): submit_needs checks coverage and writes nothing."""
from docfactory.documentmodels.document_gap import DocumentGap
from docfactory.tools.needs_tools import NEEDS_PACKAGE_NAME, NEEDS_TOOL_NAMES, needs_package

GAPS = [DocumentGap(number=n, field=f"section.field_{n}", question=f"Question {n}?", expected_source=f"Entity.field_{n}") for n in (1, 2, 3)]


def need(gaps, audience="product owner", question="What is it?"):
    return {"question": question, "audience": audience, "gaps": gaps}


def call(accepted, needs):
    return needs_package(GAPS, accepted).call("submit_needs", {"needs": needs})


def test_the_package_holds_exactly_one_tool():
    package = needs_package(GAPS, [])
    assert NEEDS_PACKAGE_NAME == "generation-needs" and NEEDS_TOOL_NAMES == ["submit_needs"]
    assert package.name == "generation-needs" and [t.name for t in package.tools()] == ["submit_needs"]


def test_the_schema_is_inlined_and_describes_a_need():
    schema = needs_package(GAPS, []).tools()[0].input_schema()
    assert "$defs" not in str(schema)
    assert set(schema["properties"]["needs"]["items"]["properties"]) == {"question", "audience", "gaps"}


def test_a_list_covering_every_gap_is_accepted():
    accepted = []
    assert call(accepted, [need([1, 2]), need([3], audience="architect")]) == {"ok": True, "needs": 2}
    assert [n.gaps for n in accepted[0]] == [[1, 2], [3]]


def test_an_uncovered_gap_is_refused():
    accepted = []
    result = call(accepted, [need([1, 2])])
    assert result["ok"] is False and "covered by no need: [3]" in " ".join(result["errors"]) and accepted == []


def test_an_unknown_gap_number_is_refused():
    result = call([], [need([1, 2, 3, 7])])
    assert result["ok"] is False and "do not exist: [7]" in " ".join(result["errors"])


def test_a_need_without_a_gap_is_refused():
    result = call([], [need([1, 2, 3]), need([])])
    assert result["ok"] is False and "gaps" in result["error"]


def test_a_need_without_an_audience_is_refused():
    result = call([], [need([1, 2, 3], audience=" ")])
    assert result["ok"] is False and "names no audience" in " ".join(result["errors"])


def test_an_empty_list_is_refused():
    assert call([], [])["ok"] is False
