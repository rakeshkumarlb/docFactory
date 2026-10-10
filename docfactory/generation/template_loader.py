"""Loads the YAML document templates: `templates/<DocType>.yaml` next to this module, or the folder named by env DOCFACTORY_TEMPLATES."""
import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from docfactory.generation.template_check import check_template
from docfactory.generation.template_error import TemplateError
from docfactory.models.document_template import DocumentTemplate

ENV_VAR = "DOCFACTORY_TEMPLATES"


def templates_dir() -> Path:
    """Where the templates are: env DOCFACTORY_TEMPLATES, else generation/templates/."""
    override = os.environ.get(ENV_VAR)
    return Path(override) if override else Path(__file__).resolve().parent / "templates"


def list_doc_types() -> list[str]:
    """The document types that have a template, in name order."""
    return sorted(path.stem for path in templates_dir().glob("*.yaml"))


def load_template(doc_type: str) -> DocumentTemplate:
    """The validated template of `doc_type`. Raises TemplateError when it is missing, not valid, or wired wrongly."""
    path = templates_dir() / f"{doc_type}.yaml"
    if not path.is_file():
        raise TemplateError(f"no template for document type {doc_type!r}: {path.as_posix()} does not exist; available: {', '.join(list_doc_types()) or 'none'}")
    try:
        template = DocumentTemplate.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (yaml.YAMLError, ValidationError) as error:
        raise TemplateError(f"{path.name}: {error}") from error
    if template.doc_type != doc_type:
        raise TemplateError(f"{path.name}: doc_type is {template.doc_type!r}, the file name says {doc_type!r}")
    return check_template(template)
