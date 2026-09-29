import pytest
from pydantic import ValidationError

from docfactory.entitymodels.facts.monitoring import Monitoring
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.alert import Alert

MINIMAL = {}

FULL = {
    "monitoring_tools": ["Test monitoring tools"],
    "key_metrics": ["Test key metrics"],
    "alerts": [{"name": "Test alert"}],
    "dashboards": ["Test dashboards"],
    "log_locations": ["Test log locations"],
}


def test_minimal_payload_is_valid():
    Monitoring.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Monitoring.model_validate(FULL)
    assert Monitoring.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Monitoring.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Monitoring.model_validate(MINIMAL)
    assert obj.monitoring_tools == []
    assert obj.key_metrics == []
    assert obj.alerts == []
    assert obj.dashboards == []
    assert obj.log_locations == []


@pytest.mark.parametrize("field", ["monitoring_tools", "key_metrics", "alerts", "dashboards", "log_locations"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Monitoring.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Monitoring has 5 top-level scored fields, none mandatory.
# Full payload total: monitoring_tools (1), key_metrics (1), alerts -> Alert item (5), dashboards (1), log_locations (1) = 9.
FULL_COMPLETE = {'monitoring_tools': ['Test monitoring tools'],
 'key_metrics': ['Test key metrics'],
 'alerts': [{'name': 'Test name',
             'condition': 'Test condition',
             'severity': 'Test severity',
             'response_action': 'Test response action',
             'notification_channel': 'Test notification channel'}],
 'dashboards': ['Test dashboards'],
 'log_locations': ['Test log locations']}


def test_completeness_of_mandatory_only_payload():
    # an empty payload: every one of the 5 top-level fields is at its default (an empty list counts as one unanswered field)
    # -> answered 0 / total 5
    obj = Monitoring.model_validate(MINIMAL)
    assert field_counts(obj) == (0, 5)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # every field filled, each list holding one fully filled item -> 9 / 9 * 100
    obj = Monitoring.model_validate(FULL_COMPLETE)
    assert field_counts(obj) == (9, 9)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 0 of 5
    defaults = {'monitoring_tools': [], 'key_metrics': [], 'alerts': [], 'dashboards': [], 'log_locations': []}
    obj = Monitoring.model_validate(defaults)
    assert field_counts(obj) == (0, 5)


def test_two_item_list_scores_both_items_fields():
    # alerts: a fully filled item (5/5) and a mandatory-only item (1/5) -> 6/10;
    # the other 4 top-level fields stay at their defaults (0/1 each) -> overall 6 / 14
    full_item = {'name': 'Test name',
 'condition': 'Test condition',
 'severity': 'Test severity',
 'response_action': 'Test response action',
 'notification_channel': 'Test notification channel'}
    half_item = {'name': 'Test name'}
    obj = Monitoring.model_validate({"alerts": [full_item, half_item]})
    assert field_counts(obj) == (6, 14)
    assert completeness(obj) == pytest.approx(6 / 14 * 100)
