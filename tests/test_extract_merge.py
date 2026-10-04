"""Merging partial fact values (Phase 3 redesign, step 1)."""
from docfactory.entitymodels.facts.application_overview import ApplicationOverview
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.extract.merge import merge_partials


def req(id, **fields):
    return {"id": id, "title": fields.pop("title", f"T {id}"), "description": fields.pop("description", f"D {id}"), **fields}


def test_scalars_take_the_first_non_empty_value_and_report_conflicts():
    merged, conflicts = merge_partials(ApplicationOverview, [
        ("new.pdf", {"purpose": "Match jobs."}),
        ("old.pdf", {"purpose": "Match candidates to jobs.", "business_owner": "HR"}),
    ])
    assert merged == {"purpose": "Match jobs.", "business_owner": "HR"}
    assert conflicts == ["purpose: kept 'Match jobs.' from new.pdf; old.pdf says 'Match candidates to jobs.'"]


def test_equal_values_differing_only_in_case_or_spacing_are_no_conflict():
    _, conflicts = merge_partials(ApplicationOverview, [("a", {"purpose": "Match  jobs."}), ("b", {"purpose": "match jobs."})])
    assert conflicts == []


def test_string_lists_are_unioned_without_duplicates():
    merged, _ = merge_partials(ApplicationOverview, [("a", {"target_users": ["Recruiters", "Job seekers"]}),
                                                    ("b", {"target_users": ["job seekers", "Admins"]})])
    assert merged["target_users"] == ["Recruiters", "Job seekers", "Admins"]


def test_items_are_unioned_by_identity_and_merged_field_by_field():
    merged, conflicts = merge_partials(FunctionalRequirements, [
        ("new.pdf", {"requirements": [req("FR-01", priority="MUST"), req("FR-02")]}),
        ("old.pdf", {"requirements": [req("FR-01.", title="T FR-01", description="D FR-01", acceptance_criteria=["Works"]), req("FR-03")]}),
    ])
    assert [r["id"] for r in merged["requirements"]] == ["FR-01", "FR-02", "FR-03"]
    first = merged["requirements"][0]
    assert first["priority"] == "MUST" and first["acceptance_criteria"] == ["Works"]
    assert conflicts == []


def test_a_differing_item_field_is_a_conflict_named_by_identity():
    _, conflicts = merge_partials(FunctionalRequirements, [("a", {"requirements": [req("FR-01", title="Register")]}),
                                                          ("b", {"requirements": [req("FR-01", title="Sign up")]})])
    assert conflicts == ["requirements[FR-01].title: kept 'Register' from a; b says 'Sign up'"]


def test_not_applicable_counts_as_a_value():
    merged, conflicts = merge_partials(FunctionalRequirements, [("a", {"out_of_scope": {"reason": "None."}}),
                                                               ("b", {"out_of_scope": ["Payroll"]})])
    assert merged["out_of_scope"] == {"reason": "None."} and len(conflicts) == 1


def test_nothing_stated_merges_to_nothing():
    assert merge_partials(FunctionalRequirements, [("a", {}), ("b", {"summary": ""})]) == ({}, [])
