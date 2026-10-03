"""Fixtures for testing the dev scripts in .claude/scripts against a throwaway project."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".claude" / "scripts"))

import conventions  # noqa: E402

STUBS = {
    "docfactory/__init__.py": "",
    "docfactory/models/__init__.py": "",
    "docfactory/models/doc_factory_model.py": (
        "from pydantic import BaseModel, ConfigDict\n\n\n"
        "class DocFactoryModel(BaseModel):\n"
        '    """Stub base model."""\n\n'
        '    model_config = ConfigDict(extra="forbid")\n'
    ),
    "docfactory/models/doc_field.py": (
        "from pydantic import Field\n\n\n"
        "def doc_field(default=..., *, default_factory=None, description, question=None,\n"
        "              na_allowed=False, scored=True, binding=None, min_length=None):\n"
        '    extra = {"question": question or description, "na_allowed": na_allowed,\n'
        '             "scored": scored, "binding": binding}\n'
        '    kwargs = {"description": description, "json_schema_extra": extra}\n'
        "    if min_length is not None:\n"
        '        kwargs["min_length"] = min_length\n'
        "    if default_factory is not None:\n"
        '        kwargs["default_factory"] = default_factory\n'
        "    elif default is not ...:\n"
        '        kwargs["default"] = default\n'
        "    return Field(**kwargs)\n"
    ),
    "docfactory/models/not_applicable.py": (
        "from docfactory.models.doc_factory_model import DocFactoryModel\n"
        "from docfactory.models.doc_field import doc_field\n\n\n"
        "class NotApplicable(DocFactoryModel):\n"
        '    """Stub N/A value."""\n\n'
        '    reason: str = doc_field(description="Why it does not apply, e.g. no database.", min_length=1)\n'
    ),
    "docfactory/entitymodels/__init__.py": "",
    "docfactory/documentmodels/__init__.py": "",
    "docfactory/entitysaver/__init__.py": "",
    "docfactory/documentsaver/__init__.py": "",
}

ENVIRONMENT_SPEC = {
    "class": "Environment",
    "doc": "One deployment environment of an application.",
    "imports": [],
    "fields": [
        {
            "name": "name",
            "type": "str",
            "description": "Name of the environment, e.g. Production or Staging.",
            "min_length": 1,
            "example": '"Test-Env"',
        },
        {
            "name": "url",
            "type": "str | NotApplicable",
            "default": "None",
            "description": "Base URL of the environment, e.g. https://example.test. N/A when it has no URL.",
            "question": "What is the base URL of this environment?",
            "na_allowed": True,
            "example": '"https://example.test"',
        },
        {
            "name": "notes",
            "type": "list[str]",
            "default": "[]",
            "description": "Free notes about the environment, e.g. maintenance windows.",
            "example": '["a note"]',
        },
    ],
}


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A temporary project root with stub base classes; scripts are pointed at it."""
    for name, content in STUBS.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    monkeypatch.setattr(conventions, "ROOT", tmp_path)
    return tmp_path
