"""The partial form of an entity model for one extraction batch (Phase 3 redesign, step 1)."""
from docfactory.entitymodels.facts.application_overview import ApplicationOverview
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.extract.partial_schema import partial_model, partial_values


def test_every_top_level_field_is_optional_with_its_description_kept():
    model = partial_model(ApplicationOverview)
    assert all(not f.is_required() and f.default is None for f in model.model_fields.values())
    assert model.model_fields["purpose"].description == ApplicationOverview.model_fields["purpose"].description
    assert partial_model(ApplicationOverview) is model  # built once


def test_a_batch_may_state_only_some_fields_even_mandatory_ones_missing():
    stated, errors = partial_values(ApplicationOverview, {"target_users": ["Recruiters"]})
    assert errors == [] and stated == {"target_users": ["Recruiters"]}


def test_defaults_and_empty_values_state_nothing():
    stated, errors = partial_values(FunctionalRequirements, {"summary": "", "requirements": [], "out_of_scope": []})
    assert errors == [] and stated == {}


def test_list_items_keep_their_mandatory_fields_and_errors_carry_the_question():
    stated, errors = partial_values(FunctionalRequirements, {"requirements": [{"id": "FR-01", "title": "Register"}]})
    assert stated is None
    (error,) = errors
    assert error.path == "requirements.0.description" and error.question == "What does this requirement state?"


def test_constraints_are_kept_and_hallucinated_fields_rejected():
    assert partial_values(ApplicationOverview, {"application_name": ""})[0] is None
    stated, errors = partial_values(ApplicationOverview, {"colour": "blue"})
    assert stated is None and errors[0].error_type == "extra_forbidden"


def test_not_applicable_is_accepted_where_allowed():
    stated, errors = partial_values(FunctionalRequirements, {"out_of_scope": {"reason": "Nothing is excluded."}})
    assert errors == [] and stated == {"out_of_scope": {"reason": "Nothing is excluded."}}
