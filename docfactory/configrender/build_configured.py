"""Builds a configuration-based document body from the stored facts, deterministically.

Every template field is looked up in its fact (`build.load_fact`) and copied when the fact answers it (`build.is_answered`, the same rule as
completeness). A field whose fact is absent or still at its default stays `missing` with an empty value: nothing is invented, nothing fails.
"""
from pydantic_core import to_jsonable_python

from docfactory.build import FACT_SPECS, is_answered, load_fact
from docfactory.canonical import canonical_json
from docfactory.configrender.bindings import field_name, label_of, source_field
from docfactory.models.configured_body import ConfiguredBody
from docfactory.models.configured_field import ConfiguredField
from docfactory.models.configured_section import ConfiguredSection
from docfactory.models.document_template import DocumentTemplate


def build_body(template: DocumentTemplate, app_id: str) -> ConfiguredBody:
    """The body of `app_id`'s `template` document: its sections in template order, each field filled from its fact or marked missing."""
    cache: dict = {}
    sections = []
    for section in template.sections:
        fields = []
        for field in section.fields:
            fact = load_fact(app_id, field.binding.partition(".")[0], cache)
            source = source_field(field.binding)
            value = getattr(fact, field_name(field.binding)) if fact is not None else None
            answered = fact is not None and is_answered(source, value)
            fields.append(ConfiguredField(
                binding=field.binding, label=label_of(field), render_as=field.render_as,
                status="answered" if answered else "missing",
                value=canonical_json(to_jsonable_python(value)) if answered else "",
            ))
        sections.append(ConfiguredSection(id=section.id, title=section.title, fields=fields))
    return ConfiguredBody(sections=sections)
