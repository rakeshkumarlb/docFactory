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
BASE_SAVER = "BaseSaver"
BASE_SAVER_MODULE = "docfactory.base_saver"
BOOTSTRAP_CLASSES = {BASE_MODEL}  # cannot be scaffolded: they are what scaffolds derive from

# Top-level folders of the package. models/ (machinery only) and entitysaver/ are flat; entitymodels/ and
# documentmodels/ have sub-folders (below).
MODEL_FOLDERS = ("models", "entitymodels", "documentmodels")
SAVER_FOLDERS = ("entitysaver", "documentsaver")
ALL_FOLDERS = MODEL_FOLDERS + SAVER_FOLDERS

# entitymodels/ has exactly two sub-folders and no module directly in it:
#   facts   an entity model with a saver in entitysaver/ (a top-level knowledge fact)
#   items   an entity model with no saver (nested item types and enums)
ENTITY_SUBFOLDERS = ("facts", "items")
ENTITY_FACTS, ENTITY_ITEMS = ENTITY_SUBFOLDERS

KINDS = {
    "entity-model": {"folder": "entitymodels"},
    "shared-model": {"folder": "models"},
}

# Where the saver for a model kind lives and what it writes. Only top-level entities (facts) get a saver; nested item types never do.
SAVERS = {
    "entity-model": {
        "folder": "entitysaver",
        "table": "KnowledgeFacts",
        "key_column": "FactKey",
    },
}

# Placeholders used to turn a key pattern into a concrete key for generated tests.
SAMPLE_SEGMENTS = {"{app}": "TestApp", "{component}": "testcomponent"}

# Annotation names that are never allowed in a model (Principle: typed everything).
FORBIDDEN_TYPE_NAMES = {"dict", "Dict", "Any", "Mapping", "MutableMapping", "TypedDict", "object"}
BARE_CONTAINER_NAMES = {"list", "List", "set", "Set", "tuple", "Tuple", "frozenset"}
ENUM_BASES = {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"}
