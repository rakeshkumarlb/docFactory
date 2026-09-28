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

# Top-level folders of the package. models/, entitymodels/ and entitysaver/ are flat.
MODEL_FOLDERS = ("models", "entitymodels", "documentmodels")
SAVER_FOLDERS = ("entitysaver", "documentsaver")
ALL_FOLDERS = MODEL_FOLDERS + SAVER_FOLDERS

# documentmodels/ and documentsaver/ have one sub-folder per role, and every file lives in one of them:
#   documents    a document body, composed of sections (one per document type)
#   shared       reusable across every document type, supplied by the caller (document control, revision history)
#   entitybound  a section in a specific format whose fields bind to entity facts
DOCUMENT_ROLES = ("documents", "shared", "entitybound")
ROLE_FOLDERS = ("documentmodels", "documentsaver")
SAVER_ROLES = ("documents", "shared")  # an entity-bound section is stored inside its document body: no saver

# Which roles a role may import from (inside documentmodels/): documents compose sections and shared parts,
# entity-bound sections stand alone, shared parts stand alone.
ROLE_MAY_IMPORT = {"documents": ("entitybound", "shared"), "entitybound": (), "shared": ()}

KINDS = {
    "entity-model": {"folder": "entitymodels"},
    "document-model": {"folder": "documentmodels"},
    "shared-model": {"folder": "models"},
}

# Where the saver for a model kind lives and what it writes. Only top-level entities (facts) and
# top-level documents and the reusable document parts get a saver; nested item types never do.
SAVERS = {
    "entity-model": {
        "folder": "entitysaver",
        "table": "KnowledgeFacts",
        "key_column": "FactKey",
    },
    "document-model": {
        "folder": "documentsaver",  # plus a role sub-folder, see SAVER_ROLES
        "table": "DocumentOutputs",
        "key_column": "DocumentKey",
    },
}

# Placeholders used to turn a key pattern into a concrete key for generated tests.
SAMPLE_SEGMENTS = {"{app}": "TestApp", "{component}": "testcomponent", "{doctype}": "TESTDOC"}

# Annotation names that are never allowed in a model (Principle: typed everything).
FORBIDDEN_TYPE_NAMES = {"dict", "Dict", "Any", "Mapping", "MutableMapping", "TypedDict", "object"}
BARE_CONTAINER_NAMES = {"list", "List", "set", "Set", "tuple", "Tuple", "frozenset"}
ENUM_BASES = {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"}

# Field bindings that are not a fact path.
BINDING_CALLER = "caller"  # supplied by the caller (document control, revision history)
BINDING_COMPOSED = "composed"  # a nested section model; its own fields carry the bindings
