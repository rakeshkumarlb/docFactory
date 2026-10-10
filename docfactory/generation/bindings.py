"""Resolves a template field's binding ('<Entity>.<field>') to the entity field that supplies it, and its label and question."""
from pydantic.fields import FieldInfo

from docfactory.build import FACT_SPECS
from docfactory.generation.template_error import TemplateError
from docfactory.models.template_field import TemplateField
from docfactory.open_questions import question_of
from docfactory.render import title_of


def source_field(binding: str) -> FieldInfo:
    """The entity field a binding names. Raises TemplateError for an unknown entity or field."""
    fact_name, _, name = binding.partition(".")
    spec = FACT_SPECS.get(fact_name)
    if spec is None:
        raise TemplateError(f"binding {binding!r}: unknown entity {fact_name!r}; known entities: {', '.join(FACT_SPECS)}")
    field = spec["model"].model_fields.get(name)
    if field is None:
        raise TemplateError(f"binding {binding!r}: {fact_name} has no field {name!r}; its fields: {', '.join(spec['model'].model_fields)}")
    return field


def field_name(binding: str) -> str:
    """The entity field name of a binding: 'FunctionalRequirements.out_of_scope' gives 'out_of_scope'."""
    return binding.partition(".")[2]


def label_of(field: TemplateField) -> str:
    """The label shown in front of the value: the template's label, else the source field's name in title case."""
    return field.label or title_of(field_name(field.binding))


def question_for(field: TemplateField) -> str:
    """The question asked when the field is missing: the template's question, else the entity field's."""
    return field.question or question_of(source_field(field.binding))
