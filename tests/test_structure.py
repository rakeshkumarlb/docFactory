"""Repo-wide structure rules from CLAUDE.md ("Tests: Structure").

The static rules (one class per file, file name = snake_case of the class, saver names and bodies,
model folders, base class, layering, stray Pydantic classes) live in `.claude/scripts/check_structure.py`
and are loaded from there. The rules that need the classes imported are checked here.
"""
import importlib
import importlib.util
import inspect
import pkgutil
import sys
from pathlib import Path
from typing import Any, get_args, get_origin

import pytest

import docfactory
from docfactory.models.doc_factory_model import DocFactoryModel

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".claude" / "scripts"
MODEL_PACKAGES = ("docfactory.models", "docfactory.entitymodels", "docfactory.documentmodels")
FORBIDDEN = (dict, Any, object)


def _load_check_structure():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("check_structure", SCRIPTS / "check_structure.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _model_classes():
    found = []
    for package_name in MODEL_PACKAGES:
        package = importlib.import_module(package_name)
        for info in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f"{package_name}.{info.name}")
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if cls.__module__ == module.__name__ and issubclass(cls, DocFactoryModel):
                    found.append(cls)
    return found


def _forbidden_parts(annotation):
    """Every forbidden or untyped piece inside an annotation."""
    origin = get_origin(annotation)
    if annotation in FORBIDDEN or origin in FORBIDDEN:
        return [annotation]
    if annotation in (list, set, tuple, frozenset):
        return [annotation]  # a container without an item type
    found = []
    for argument in get_args(annotation):
        found += _forbidden_parts(argument)
    return found


MODELS = _model_classes()


def test_static_structure_rules_hold_for_the_whole_package():
    check_structure = _load_check_structure()
    findings = check_structure.collect([], want_tests=False)
    assert findings == [], "\n".join(f"{path}:{line}: {rule} {message}" for path, line, rule, message in findings)


def test_the_model_packages_contain_models():
    assert {cls.__name__ for cls in MODELS} >= {"DocFactoryModel", "NotApplicable", "SaveError", "SaveResult"}


def test_every_package_folder_has_an_init_file():
    package = Path(docfactory.__file__).parent
    for folder in ("models", "entitymodels", "documentmodels", "entitysaver", "documentsaver"):
        assert (package / folder / "__init__.py").is_file(), folder


@pytest.mark.parametrize("cls", MODELS, ids=lambda cls: cls.__name__)
def test_every_model_has_a_docstring_and_a_description_on_every_field(cls):
    assert inspect.getdoc(cls) and cls.__doc__, f"{cls.__name__} has no docstring of its own"
    for name, field in cls.model_fields.items():
        assert field.description and field.description.strip(), f"{cls.__name__}.{name} has no description"


@pytest.mark.parametrize("cls", MODELS, ids=lambda cls: cls.__name__)
def test_no_model_field_is_a_dict_any_or_untyped_list(cls):
    for name, field in cls.model_fields.items():
        assert _forbidden_parts(field.annotation) == [], f"{cls.__name__}.{name}: {field.annotation}"


@pytest.mark.parametrize("cls", MODELS, ids=lambda cls: cls.__name__)
def test_every_model_derives_from_the_project_base_model_and_forbids_extras(cls):
    assert issubclass(cls, DocFactoryModel)
    assert cls.model_config.get("extra") == "forbid"


@pytest.mark.parametrize("cls", MODELS, ids=lambda cls: cls.__name__)
def test_every_field_declares_the_docfactory_metadata(cls):
    for name, field in cls.model_fields.items():
        extra = field.json_schema_extra
        assert isinstance(extra, dict) and {"question", "na_allowed", "scored", "binding"} <= set(extra), f"{cls.__name__}.{name} is not declared with doc_field"


def test_the_forbidden_type_detector_catches_what_it_should():
    assert _forbidden_parts(dict[str, int]) and _forbidden_parts(list[Any]) and _forbidden_parts(list) and _forbidden_parts(dict)
    assert _forbidden_parts(list[str] | None) == [] and _forbidden_parts(list[int | None]) == []
