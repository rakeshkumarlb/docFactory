import pytest

import naming


@pytest.mark.parametrize(
    "name, expected",
    [
        ("ApplicationOverview", "application_overview"),
        ("Kpis", "kpis"),
        ("SmtdSupportModel", "smtd_support_model"),
        ("HTTPServer", "http_server"),
        ("Slo", "slo"),
    ],
)
def test_to_snake(name, expected):
    assert naming.to_snake(name) == expected


@pytest.mark.parametrize("name, ok", [("Environment", True), ("environment", False), ("My_Class", False), ("2Fast", False)])
def test_is_pascal(name, ok):
    assert naming.is_pascal(name) is ok


def test_key_matching_and_app_id():
    assert naming.key_matches("{app}.Architecture", "KitchenHQ.Architecture")
    assert naming.key_matches("{app}.Components.{component}.Architecture", "KitchenHQ.Components.dbmcp.Architecture")
    assert not naming.key_matches("{app}.Architecture", "KitchenHQ.Components.dbmcp.Architecture")
    assert naming.key_matches("Shared.Kpis", "Shared.Kpis")
    assert not naming.key_matches("Shared.Kpis", "Other.Kpis")
    assert naming.app_id_of("Shared.Kpis") is None
    assert naming.app_id_of("KitchenHQ.Components.dbmcp.Architecture") == "KitchenHQ"


def test_resolve_entity_model(project):
    info = naming.resolve("entity-model", "ApplicationOverview")
    assert info["errors"] == []
    assert info["file"] == "docfactory/entitymodels/application_overview.py"
    assert info["test_file"] == "tests/test_application_overview.py"
    assert info["module"] == "docfactory.entitymodels.application_overview"
    assert info["exists"] is False


def test_resolve_rejects_bad_names_and_bootstrap_classes(project):
    assert naming.resolve("entity-model", "application_overview")["errors"]
    assert naming.resolve("shared-model", "DocFactoryModel")["errors"]
    assert naming.resolve("entity-model", "FooSaver")["errors"]
    assert naming.resolve("nonsense", "Foo")["errors"]


def test_resolve_detects_class_defined_elsewhere(project):
    other = project / "docfactory" / "documentmodels" / "environment.py"
    other.write_text("class Environment:\n    pass\n", encoding="utf-8")
    assert naming.resolve("entity-model", "Environment")["errors"]


def test_saver_target_and_sample_keys(project):
    info = naming.saver_target("entity-model", "Environment", "docfactory.entitymodels.environment")
    assert info["saver_class"] == "EnvironmentSaver"
    assert info["file"] == "docfactory/entitysaver/environment_saver.py"
    assert info["test_file"] == "tests/test_environment_saver.py"
    assert naming.saver_target("document-model", "SmtdDocument", "x")["folder"] == "docfactory/documentsaver"
    assert naming.sample_key("{app}.Components.{component}.Architecture") == "TestApp.Components.testcomponent.Architecture"
    assert naming.sample_key("Shared.Kpis") == "Shared.Kpis"


def test_pattern_rules():
    assert naming.pattern_problems("entity-model", "{app}.Widget") == []
    assert naming.pattern_problems("entity-model", "Shared.Kpis") == []
    assert naming.pattern_problems("entity-model", "Widget.{app}")
    assert naming.pattern_problems("entity-model", "Bad Pattern")
    assert naming.pattern_problems("document-model", "{app}.Outputs.{doctype}.DocumentControl") == []
    assert naming.pattern_problems("document-model", "{app}.DocumentControl")
