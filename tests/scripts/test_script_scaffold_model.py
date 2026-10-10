import copy
import json
import os
import subprocess
import sys

import add_field
import check_structure
import scaffold_model
from conftest import ENVIRONMENT_SPEC


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def scaffold(project, spec=None, kind="entity-model", *flags):
    spec_path = write_json(project / "spec.json", spec or ENVIRONMENT_SPEC)
    return scaffold_model.main([kind, spec_path, *flags])


def run_pytest(project, target):
    env = {**os.environ, "PYTHONPATH": str(project)}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", target],
        cwd=project, env=env, capture_output=True, text=True,
    )


def test_scaffolded_model_and_its_generated_tests_pass(project):
    assert scaffold(project) == 0
    model = (project / "docfactory/entitymodels/items/environment.py").read_text(encoding="utf-8")
    assert "class Environment(DocFactoryModel):" in model
    assert "from docfactory.models.not_applicable import NotApplicable" in model
    assert "default_factory=list" in model
    assert "na_allowed=True" in model
    result = run_pytest(project, "tests/test_environment.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_scaffolded_files_pass_the_structure_check(project):
    scaffold(project)
    assert check_structure.collect([], want_tests=False) == []
    (project / "tests").mkdir(exist_ok=True)
    missing = [m for _, _, rule, m in check_structure.collect([], want_tests=True) if rule == "test-missing"]
    assert not any("test_environment.py" in m for m in missing)


def test_scaffold_refuses_to_overwrite_and_writes_nothing_on_bad_spec(project):
    assert scaffold(project) == 0
    assert scaffold(project) == 1  # already exists
    bad = copy.deepcopy(ENVIRONMENT_SPEC)
    bad["class"] = "Other"
    bad["fields"][0]["type"] = "dict"
    assert scaffold(project, bad) == 1
    assert not (project / "docfactory/entitymodels/other.py").exists()


def test_dry_run_writes_nothing(project, capsys):
    assert scaffold(project, None, "entity-model", "--dry-run") == 0
    assert "class Environment" in capsys.readouterr().out
    assert not (project / "docfactory/entitymodels/items/environment.py").exists()


def test_add_field_inserts_field_imports_and_reports_test_lines(project, capsys):
    scaffold(project)
    field = {
        "name": "region",
        "type": "str | NotApplicable",
        "default": "None",
        "description": "Cloud region, e.g. eu-west-1. N/A for on-premise environments.",
        "na_allowed": True,
        "example": '"eu-west-1"',
    }
    spec = copy.deepcopy(ENVIRONMENT_SPEC)
    spec["fields"] = [f for f in spec["fields"] if f["name"] != "url"]
    (project / "docfactory/entitymodels/items/environment.py").unlink()
    (project / "tests/test_environment.py").unlink()
    assert scaffold(project, spec) == 0
    assert add_field.main(["Environment", write_json(project / "field.json", field)]) == 0
    model = (project / "docfactory/entitymodels/items/environment.py").read_text(encoding="utf-8")
    assert "region: str | NotApplicable = doc_field(" in model
    assert "from docfactory.models.not_applicable import NotApplicable" in model
    assert 'add_to_FULL' in capsys.readouterr().out
    assert add_field.main(["Environment", write_json(project / "field.json", field)]) == 1  # duplicate


def test_add_field_needs_explicit_permission_for_a_mandatory_field(project):
    scaffold(project)
    field = {"name": "owner", "type": "str", "description": "Owner of the environment, e.g. Ops team.", "example": '"Ops"'}
    path = write_json(project / "field.json", field)
    assert add_field.main(["Environment", path]) == 1
    assert add_field.main(["Environment", path, "--allow-mandatory"]) == 0


def with_conftest(project):
    (project / "tests").mkdir(exist_ok=True)
    (project / "tests/conftest.py").write_text("def tmp_db():\n    pass\n", encoding="utf-8")


def test_entity_saver_is_generated_with_the_model(project):
    with_conftest(project)
    assert scaffold(project, None, "entity-model", "--scope", "app") == 0
    assert (project / "docfactory/entitymodels/facts/environment.py").exists()  # a model with a saver is a fact
    assert not (project / "docfactory/entitymodels/items/environment.py").exists()
    assert (project / "docfactory/entitymodels/facts/__init__.py").exists()
    saver = (project / "docfactory/entitysaver/environment_saver.py").read_text(encoding="utf-8")
    assert "class EnvironmentSaver(BaseSaver[Environment]):" in saver
    assert '"{app}.Environment", "{app}.Components.{component}.Environment"' in saver
    test = (project / "tests/test_environment_saver.py").read_text(encoding="utf-8")
    compile(test, "test_environment_saver.py", "exec")
    assert "KnowledgeFacts" in test and "SAVER = EnvironmentSaver()" in test and "SAVER.save(KEY, PAYLOAD)" in test
    assert "from docfactory.entitysaver.environment_saver import EnvironmentSaver" in test
    assert 'KEY = "TestApp.Environment"' in test
    assert "'TestApp'" in test and "test_component_key_stores_the_application_as_app_id" in test
    assert "\"name\": 'Test-Env-changed'" in test and "test_missing_mandatory_field" in test
    assert check_structure.collect([], want_tests=True) == [
        f for f in check_structure.collect([], want_tests=True) if f[2] == "test-missing" and "environment" not in f[3]
    ]


def test_shared_scope_has_no_component_key_and_null_app_id(project):
    with_conftest(project)
    assert scaffold(project, None, "entity-model", "--scope", "shared") == 0
    test = (project / "tests/test_environment_saver.py").read_text(encoding="utf-8")
    assert 'KEY = "Shared.Environment"' in test
    assert 'row["AppID"] == None' in test and "component_key" not in test


def test_saver_refusals_write_nothing(project):
    assert scaffold(project, None, "entity-model", "--scope", "app") == 1  # no tmp_db fixture yet
    with_conftest(project)
    assert scaffold(project, None, "entity-model", "--pattern", "Widget.{app}") == 1
    assert scaffold(project, None, "shared-model", "--scope", "app") == 1
    spec = copy.deepcopy(ENVIRONMENT_SPEC)
    for f in spec["fields"]:
        f["example"] = "1" if f["name"] == "name" else f["example"]
    spec["fields"] = spec["fields"][:1]
    assert scaffold(project, spec, "entity-model", "--scope", "app") == 1  # no string example to change
    assert not (project / "docfactory/entitymodels/items/environment.py").exists()
    assert not (project / "docfactory/entitysaver/environment_saver.py").exists()
