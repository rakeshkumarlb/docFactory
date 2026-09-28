import pytest
from pydantic import ValidationError

from docfactory.entitymodels.architecture import Architecture
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.component import Component
from docfactory.models.data_store import DataStore
from docfactory.models.integration import Integration

MINIMAL = {}

FULL = {
    "architecture_style": "Test architecture style",
    "technology_stack": ["Test technology stack"],
    "components": [{"name": "Test component"}],
    "data_stores": [{"name": "Test data store"}],
    "integrations": [{"name": "Test integration"}],
    "diagram_reference": "Test diagram reference",
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    Architecture.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Architecture.model_validate(FULL)
    assert Architecture.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Architecture.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Architecture.model_validate(MINIMAL)
    assert obj.architecture_style == ''
    assert obj.technology_stack == []
    assert obj.components == []
    assert obj.data_stores == []
    assert obj.integrations == []
    assert obj.diagram_reference is None
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["diagram_reference"])
def test_not_applicable_is_accepted_where_allowed(field):
    Architecture.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["architecture_style", "technology_stack", "components", "data_stores", "integrations", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Architecture.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Architecture has 7 top-level scored fields, none mandatory.
# Full payload total: architecture_style (1), technology_stack (1), components -> Component item (5), data_stores -> DataStore item (4), integrations -> Integration item (6), diagram_reference (1), notes (1) = 19.
FULL_COMPLETE = {'architecture_style': 'Test architecture style',
 'technology_stack': ['Test technology stack'],
 'components': [{'name': 'Test name',
                 'purpose': 'Test purpose',
                 'technology': 'Test technology',
                 'owner': 'Test owner',
                 'dependencies': ['Test dependencies']}],
 'data_stores': [{'name': 'Test name',
                  'store_type': 'Test store type',
                  'technology': 'Test technology',
                  'contents': 'Test contents'}],
 'integrations': [{'name': 'Test name',
                   'direction': 'Test direction',
                   'protocol': 'Test protocol',
                   'purpose': 'Test purpose',
                   'data_exchanged': 'Test data exchanged',
                   'authentication': 'Test authentication'}],
 'diagram_reference': 'Test diagram reference',
 'notes': 'Test notes'}


def test_completeness_of_mandatory_only_payload():
    # an empty payload: every one of the 7 top-level fields is at its default (an empty list counts as one unanswered field)
    # -> answered 0 / total 7
    obj = Architecture.model_validate(MINIMAL)
    assert field_counts(obj) == (0, 7)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # every field filled, each list holding one fully filled item -> 19 / 19 * 100
    obj = Architecture.model_validate(FULL_COMPLETE)
    assert field_counts(obj) == (19, 19)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 0 of 7
    defaults = {'architecture_style': '',
 'technology_stack': [],
 'components': [],
 'data_stores': [],
 'integrations': [],
 'diagram_reference': None,
 'notes': ''}
    obj = Architecture.model_validate(defaults)
    assert field_counts(obj) == (0, 7)


def test_legal_not_applicable_on_diagram_reference_counts_as_answered():
    # diagram_reference N/A = 1 answered; the other 6 fields stay at their defaults -> 1 / 7
    obj = Architecture.model_validate({"diagram_reference": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (1, 7)
    assert completeness(obj) == pytest.approx(1 / 7 * 100)


def test_two_item_list_scores_both_items_fields():
    # components: a fully filled item (5/5) and a mandatory-only item (1/5) -> 6/10;
    # the other 6 top-level fields stay at their defaults (0/1 each) -> overall 6 / 16
    full_item = {'name': 'Test name',
 'purpose': 'Test purpose',
 'technology': 'Test technology',
 'owner': 'Test owner',
 'dependencies': ['Test dependencies']}
    half_item = {'name': 'Test name'}
    obj = Architecture.model_validate({"components": [full_item, half_item]})
    assert field_counts(obj) == (6, 16)
    assert completeness(obj) == pytest.approx(6 / 16 * 100)
