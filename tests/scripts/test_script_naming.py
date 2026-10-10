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
    info = naming.resolve("entity-model", "ApplicationOverview", fact=True)
    assert info["errors"] == []
    assert info["file"] == "docfactory/entitymodels/facts/application_overview.py"
    assert info["test_file"] == "tests/test_application_overview.py"
    assert info["module"] == "docfactory.entitymodels.facts.application_overview"
    assert info["exists"] is False
    item = naming.resolve("entity-model", "Requirement")
    assert item["file"] == "docfactory/entitymodels/items/requirement.py"
    assert item["module"] == "docfactory.entitymodels.items.requirement"


def test_path_helpers_read_the_folder(project):
    package = project / "docfactory"
    assert naming.top_folder(package / "entitymodels" / "x.py") == "entitymodels"
    assert naming.top_folder(package / "documentmodels" / "x.py") == "documentmodels"
    assert naming.top_folder(package / "canonical.py") is None
    assert naming.entity_sub_of(package / "entitymodels" / "facts" / "x.py") == "facts"
    assert naming.entity_sub_of(package / "entitymodels" / "x.py") is None
    assert naming.entity_sub_of(package / "models" / "x.py") is None


def test_resolve_rejects_bad_names_and_bootstrap_classes(project):
    assert naming.resolve("entity-model", "application_overview")["errors"]
    assert naming.resolve("shared-model", "DocFactoryModel")["errors"]
    assert naming.resolve("entity-model", "FooSaver")["errors"]
    assert naming.resolve("nonsense", "Foo")["errors"]


def test_resolve_detects_class_defined_elsewhere(project):
    other = project / "docfactory" / "documentmodels" / "environment.py"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text("class Environment:\n    pass\n", encoding="utf-8")
    assert naming.resolve("entity-model", "Environment")["errors"]


def test_saver_target_and_sample_keys(project):
    info = naming.saver_target("entity-model", "Environment", "docfactory.entitymodels.items.environment")
    assert info["saver_class"] == "EnvironmentSaver"
    assert info["file"] == "docfactory/entitysaver/environment_saver.py"
    assert info["test_file"] == "tests/test_environment_saver.py"
    assert naming.sample_key("{app}.Components.{component}.Architecture") == "TestApp.Components.testcomponent.Architecture"
    assert naming.sample_key("Shared.Kpis") == "Shared.Kpis"


def test_pattern_rules():
    assert naming.pattern_problems("entity-model", "{app}.Widget") == []
    assert naming.pattern_problems("entity-model", "Shared.Kpis") == []
    assert naming.pattern_problems("entity-model", "Widget.{app}")
    assert naming.pattern_problems("entity-model", "Bad Pattern")
