"""The one place that names the paths, classes and helpers the dev scripts depend on.

Change a convention here, not in the scripts. `ROOT` can be redirected with the
DOCFACTORY_ROOT environment variable (the script tests use a temporary project).
"""
import os
from pathlib import Path

ROOT = Path(os.environ.get("DOCFACTORY_ROOT") or Path(__file__).resolve().parents[2])
PACKAGE = "docfactory"

# Names the generated code imports. These are bootstrap classes, written by hand once.
BASE_MODEL = "DocFactoryModel"
BASE_MODEL_MODULE = "docfactory.models.doc_factory_model"
FIELD_HELPER = "doc_field"
FIELD_HELPER_MODULE = "docfactory.models.doc_field"
NOT_APPLICABLE = "NotApplicable"
NOT_APPLICABLE_MODULE = "docfactory.models.not_applicable"
BOOTSTRAP_CLASSES = {BASE_MODEL}  # cannot be scaffolded: they are what scaffolds derive from

# Top-level folders of the package that hold models. models/ (machinery only) and documentmodels/ are flat; entitymodels/ has
# sub-folders (below).
MODEL_FOLDERS = ("models", "entitymodels", "documentmodels")
ALL_FOLDERS = MODEL_FOLDERS

# entitymodels/ has exactly two sub-folders and no module directly in it:
#   facts   an entity model registered in the fact registry (a top-level knowledge fact, stored as a concept file of the bundle)
#   items   an entity model that is not registered (nested item types and enums)
ENTITY_SUBFOLDERS = ("facts", "items")
ENTITY_FACTS, ENTITY_ITEMS = ENTITY_SUBFOLDERS

KINDS = {
    "entity-model": {"folder": "entitymodels"},
    "shared-model": {"folder": "models"},
}

# The fact registry: the one place that lists the facts a bundle can hold (entity name -> model, application or shared). Only top-level
# entities (facts) are registered; nested item types never are.
FACT_REGISTRY_FILE = "docfactory/bundle/fact_registry.py"
FACT_TEST_SUFFIX = "_fact"  # tests/test_<model>_fact.py is the generated test of a fact

# Placeholders used to turn a key pattern into a concrete key for generated tests.
SAMPLE_SEGMENTS = {"{app}": "TestApp", "{component}": "testcomponent"}

# Annotation names that are never allowed in a model (Principle: typed everything).
FORBIDDEN_TYPE_NAMES = {"dict", "Dict", "Any", "Mapping", "MutableMapping", "TypedDict", "object"}
BARE_CONTAINER_NAMES = {"list", "List", "set", "Set", "tuple", "Tuple", "frozenset"}
ENUM_BASES = {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"}
