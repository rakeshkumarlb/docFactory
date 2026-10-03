import pytest
from pydantic import ValidationError

from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class _Sample(DocFactoryModel):
    """Test-only model."""

    required: str = doc_field(description="A required text, e.g. test.", question="What is it?", min_length=1)
    optional: str | None = doc_field(default=None, description="An optional text, e.g. test.", na_allowed=True)
    items: list[str] = doc_field(default_factory=list, description="Items, e.g. one.", scored=False, binding="Thing.items")


def _extra(name):
    return _Sample.model_fields[name].json_schema_extra


def test_description_is_the_field_description():
    assert _Sample.model_fields["required"].description == "A required text, e.g. test."


def test_metadata_reads_back_from_json_schema_extra():
    assert _extra("required") == {
        "question": "What is it?",
        "na_allowed": False,
        "scored": True,
        "binding": None,
        "render_as": "list",
    }
    assert _extra("optional")["na_allowed"] is True
    assert _extra("items")["scored"] is False
    assert _extra("items")["binding"] == "Thing.items"


def test_render_as_defaults_to_list_and_accepts_table():
    assert _extra("items")["render_as"] == "list"

    class _WithTable(DocFactoryModel):
        """Test-only model."""

        rows: list[str] = doc_field(default_factory=list, description="Rows, e.g. one.", render_as="table")

    assert _WithTable.model_fields["rows"].json_schema_extra["render_as"] == "table"


def test_render_as_rejects_an_unknown_style():
    with pytest.raises(ValueError, match="render_as"):
        doc_field(default_factory=list, description="Rows, e.g. one.", render_as="chart")


def test_question_falls_back_to_description():
    assert _extra("optional")["question"] == "An optional text, e.g. test."


def test_default_ellipsis_means_required():
    assert _Sample.model_fields["required"].is_required()
    assert not _Sample.model_fields["optional"].is_required()
    with pytest.raises(ValidationError):
        _Sample.model_validate({})


def test_default_and_default_factory():
    obj = _Sample.model_validate({"required": "x"})
    assert obj.optional is None
    assert obj.items == []
    assert _Sample.model_validate({"required": "x"}).items is not _Sample.model_validate({"required": "x"}).items


def test_min_length_is_forwarded():
    with pytest.raises(ValidationError):
        _Sample.model_validate({"required": ""})


def test_render_as_accepts_numbered_for_ordered_lists():
    class _Ordered(DocFactoryModel):
        """Test-only model."""

        steps: list[str] = doc_field(default_factory=list, description="Steps, e.g. one.", render_as="numbered")

    assert _Ordered.model_fields["steps"].json_schema_extra["render_as"] == "numbered"
