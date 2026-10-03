import copy

import pytest

import field_spec
from conftest import ENVIRONMENT_SPEC


def field(**overrides):
    base = {
        "name": "title",
        "type": "str",
        "description": "Title of the thing, e.g. Kitchen Orders.",
        "example": '"T"',
    }
    base.update(overrides)
    return base


def test_valid_spec_has_no_problems():
    assert field_spec.validate_model_spec(copy.deepcopy(ENVIRONMENT_SPEC), "entity-model") == []


@pytest.mark.parametrize(
    "annotation",
    ["dict", "dict[str, str]", "Any", "typing.Any", "list", "list[dict]", "List", "object", "Mapping[str, int]"],
)
def test_untyped_or_forbidden_types_are_rejected(annotation):
    assert field_spec.validate_field(field(type=annotation, default="None"))


@pytest.mark.parametrize("annotation", ["str", "list[Item]", "list[str]", "int | None", "str | NotApplicable"])
def test_typed_annotations_are_accepted(annotation):
    extra = {"na_allowed": True, "default": "None"} if "NotApplicable" in annotation else {}
    assert field_spec.validate_field(field(type=annotation, **extra)) == []


def test_na_allowed_and_type_must_agree():
    assert field_spec.validate_field(field(type="str | NotApplicable", default="None"))
    assert field_spec.validate_field(field(na_allowed=True, default="None"))


def test_mandatory_field_cannot_allow_na():
    assert field_spec.validate_field(field(type="str | NotApplicable", na_allowed=True))


def test_description_must_give_an_example_and_be_long_enough():
    assert field_spec.validate_field(field(description="Title of the thing that is shown."))
    assert field_spec.validate_field(field(description="Too short"))
    assert field_spec.validate_field(field(description="Title of the thing that is shown.", scored=False)) == []


def test_question_must_be_a_question():
    assert field_spec.validate_field(field(question="Tell me the title"))
    assert field_spec.validate_field(field(question="What is the title?")) == []


@pytest.mark.parametrize("default", ["None", "[]", "''", "False", "0", "Status.DRAFT"])
def test_honest_defaults_are_accepted(default):
    assert field_spec.validate_field(field(default=default)) == []


def test_bad_default_unknown_key_and_bad_example():
    assert field_spec.validate_field(field(default="compute()"))
    assert field_spec.validate_field(field(colour="red"))
    assert field_spec.validate_field(field(example="not python ("))


def test_bindings_only_for_document_models_and_required_there():
    assert field_spec.validate_field(field(binding="Architecture.environments"), "entity-model")
    assert field_spec.validate_field(field(), "document-model")
    assert field_spec.validate_field(field(binding="Architecture.environments"), "document-model") == []
    assert field_spec.validate_field(field(binding="caller"), "document-model") == []
    assert field_spec.validate_field(field(binding="composed"), "document-model") == []
    assert field_spec.validate_field(field(binding="somewhere"), "document-model")


def test_model_spec_rules():
    spec = copy.deepcopy(ENVIRONMENT_SPEC)
    spec["fields"].append(copy.deepcopy(spec["fields"][0]))
    assert any("duplicate" in p for p in field_spec.validate_model_spec(spec, "entity-model"))
    spec = copy.deepcopy(ENVIRONMENT_SPEC)
    spec["class"] = "environment"
    assert field_spec.validate_model_spec(spec, "entity-model")
    spec = copy.deepcopy(ENVIRONMENT_SPEC)
    spec["imports"] = ["from pydantic import BaseModel"]
    assert field_spec.validate_model_spec(spec, "entity-model")
    spec["imports"] = ["import os; import sys"]
    assert field_spec.validate_model_spec(spec, "entity-model")


def test_min_length_rules():
    assert field_spec.validate_field(field(min_length=1)) == []
    assert field_spec.validate_field(field(min_length=0))
    assert field_spec.validate_field(field(min_length="1"))
    assert field_spec.validate_field(field(type="int", min_length=1))
    assert field_spec.validate_field(field(type="str | None", default="None", min_length=1))


def test_render_as_accepts_list_or_table_only():
    assert field_spec.validate_field(field(render_as="table")) == []
    assert field_spec.validate_field(field(render_as="list")) == []
    assert field_spec.validate_field(field(render_as="grid"))


def test_render_as_table_is_emitted_in_the_generated_field():
    import render_model

    assert 'render_as="table"' in render_model.render_field(field(render_as="table"))
    assert "render_as" not in render_model.render_field(field())
