import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.monitoring_section import MonitoringSection
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.alert import Alert

MINIMAL = {}

FULL = {
    "monitoring_tools": ["Test monitoring tools"],
    "key_metrics": ["Test key metrics"],
    "alerts": [{"name": "Test alerts"}],
    "dashboards": ["Test dashboards"],
    "log_locations": ["Test log locations"],
}


def test_minimal_payload_is_valid():
    MonitoringSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = MonitoringSection.model_validate(FULL)
    assert MonitoringSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        MonitoringSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = MonitoringSection.model_validate(MINIMAL)
    assert obj.monitoring_tools == []
    assert obj.key_metrics == []
    assert obj.alerts == []
    assert obj.dashboards == []
    assert obj.log_locations == []


@pytest.mark.parametrize("field", ["monitoring_tools", "key_metrics", "alerts", "dashboards", "log_locations"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        MonitoringSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Mirror of the entity (hand-written) ---
from docfactory.entitymodels.monitoring import Monitoring  # noqa: E402


def test_section_mirrors_every_entity_field():
    assert list(MonitoringSection.model_fields) == list(Monitoring.model_fields)
    for name, field in MonitoringSection.model_fields.items():
        entity_field = Monitoring.model_fields[name]
        assert field.annotation == entity_field.annotation
        assert field.default == entity_field.default
        assert field.default_factory == entity_field.default_factory
        assert field.json_schema_extra["na_allowed"] == entity_field.json_schema_extra["na_allowed"]
        assert field.json_schema_extra["binding"] == f"Monitoring.{name}"


def test_list_of_item_fields_render_as_expected():
    tables = ['alerts']
    for name, field in MonitoringSection.model_fields.items():
        assert field.json_schema_extra["render_as"] == ("table" if name in tables else "list")
