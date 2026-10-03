import pytest

from docfactory.completeness import completeness, field_counts
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable


class _Leaf(DocFactoryModel):
    """Test-only item: one mandatory field and one optional field."""

    name: str = doc_field(description="Name, e.g. test.")
    note: str | None = doc_field(default=None, description="Note, e.g. test.")


class _Scalars(DocFactoryModel):
    """Test-only model with defaults that are not knowledge."""

    title: str | None = doc_field(default=None, description="Title, e.g. test.")
    count: int = doc_field(default=0, description="Count, e.g. 3.")
    flag: bool = doc_field(default=False, description="Flag, e.g. True.")
    tech: str = doc_field(default="", description="Technical, e.g. x.", scored=False)


class _Lists(DocFactoryModel):
    """Test-only model with lists."""

    leaves: list[_Leaf] = doc_field(default_factory=list, description="Leaves, e.g. one.")


class _Tags(DocFactoryModel):
    """Test-only model with a list of plain strings."""

    tags: list[str] = doc_field(default_factory=list, description="Tags, e.g. a.")


class _Nested(DocFactoryModel):
    """Test-only model with an optional nested model."""

    leaf: _Leaf | None = doc_field(default=None, description="Leaf, e.g. one.")


class _NaModel(DocFactoryModel):
    """Test-only model with N/A allowed on a scalar, a list and a nested model."""

    url: str | NotApplicable | None = doc_field(default=None, description="Url, e.g. x.", na_allowed=True)
    leaves: list[_Leaf] | NotApplicable = doc_field(default_factory=list, description="Leaves, e.g. one.", na_allowed=True)
    leaf: _Leaf | NotApplicable | None = doc_field(default=None, description="Leaf, e.g. one.", na_allowed=True)


class _Mandatory(DocFactoryModel):
    """Test-only model whose nested model and list are mandatory."""

    leaf: _Leaf = doc_field(description="Leaf, e.g. one.")
    leaves: list[_Leaf] = doc_field(description="Leaves, e.g. one.")


class _Unscored(DocFactoryModel):
    """Test-only model whose only field is unscored."""

    tech: str = doc_field(default="", description="Technical, e.g. x.", scored=False)


class _Holder(DocFactoryModel):
    """Test-only model mixing a scalar, an absent nested model and a list."""

    title: str | None = doc_field(default=None, description="Title, e.g. test.")
    leaf: _Leaf | None = doc_field(default=None, description="Leaf, e.g. one.")
    leaves: list[_Leaf] = doc_field(default_factory=list, description="Leaves, e.g. one.")


NA = NotApplicable(reason="Not relevant for this test.")


def test_defaults_are_not_answered():
    # title, count, flag are all at their defaults: 0 of 3 (tech is unscored).
    assert field_counts(_Scalars()) == (0, 3)
    assert completeness(_Scalars()) == 0.0


def test_defaults_passed_explicitly_are_still_not_answered():
    obj = _Scalars(title=None, count=0, flag=False)
    assert field_counts(obj) == (0, 3)


def test_a_value_different_from_the_default_is_answered():
    # title answered, count and flag not: 1 of 3.
    assert field_counts(_Scalars(title="x")) == (1, 3)
    assert completeness(_Scalars(title="x")) == pytest.approx(100 / 3)
    # all three answered: 3 of 3.
    assert completeness(_Scalars(title="x", count=2, flag=True)) == 100.0


def test_unscored_fields_are_excluded_from_both_counts():
    assert field_counts(_Scalars(tech="something")) == (0, 3)
    # a model with only unscored fields has nothing to answer: 0 of 0 counts as 100.
    assert field_counts(_Unscored()) == (0, 0)
    assert completeness(_Unscored()) == 100.0


def test_mandatory_fields_are_answered_by_definition():
    # name is mandatory (answered), note is at its default: 1 of 2.
    assert field_counts(_Leaf(name="a")) == (1, 2)
    assert completeness(_Leaf(name="a")) == 50.0


def test_an_empty_list_is_one_unanswered_field():
    assert field_counts(_Lists()) == (0, 1)
    assert field_counts(_Lists(leaves=[])) == (0, 1)


def test_a_list_of_two_items_is_scored_over_both_items_fields():
    # item one complete: 2 of 2; item two half-filled: 1 of 2; together 3 of 4 = 75.
    obj = _Lists(leaves=[_Leaf(name="a", note="n"), _Leaf(name="b")])
    assert field_counts(obj) == (3, 4)
    assert completeness(obj) == 75.0


def test_a_list_with_one_complete_item_scores_100():
    assert completeness(_Lists(leaves=[_Leaf(name="a", note="n")])) == 100.0


def test_a_non_empty_list_of_plain_values_is_one_answered_field():
    assert field_counts(_Tags(tags=["a", "b"])) == (1, 1)
    assert field_counts(_Tags()) == (0, 1)


def test_an_absent_nested_model_is_one_unanswered_field():
    assert field_counts(_Nested()) == (0, 1)


def test_a_present_nested_model_is_scored_by_its_own_fields():
    # replaced by leaf.name (answered) and leaf.note (default): 1 of 2.
    assert field_counts(_Nested(leaf=_Leaf(name="a"))) == (1, 2)
    assert field_counts(_Nested(leaf=_Leaf(name="a", note="n"))) == (2, 2)


def test_not_applicable_on_a_scalar_counts_as_answered():
    # url is N/A (answered), leaves and leaf are at their defaults: 1 of 3.
    assert field_counts(_NaModel(url=NA)) == (1, 3)


def test_not_applicable_on_a_list_is_one_answered_field():
    assert field_counts(_NaModel(leaves=NA)) == (1, 3)


def test_not_applicable_on_a_nested_model_is_one_answered_field():
    assert field_counts(_NaModel(leaf=NA)) == (1, 3)


def test_everything_not_applicable_scores_100():
    assert completeness(_NaModel(url=NA, leaves=NA, leaf=NA)) == 100.0


def test_mandatory_nested_model_and_list_are_scored_by_their_content():
    # leaf: name (answered) + note (default) = 1 of 2; leaves: one half-filled item = 1 of 2; together 2 of 4.
    obj = _Mandatory(leaf=_Leaf(name="a"), leaves=[_Leaf(name="b")])
    assert field_counts(obj) == (2, 4)


def test_a_mandatory_empty_list_is_answered_by_definition():
    # leaf: 1 of 2; leaves: the mandatory list was given (empty): 1 of 1; together 2 of 3.
    assert field_counts(_Mandatory(leaf=_Leaf(name="a"), leaves=[])) == (2, 3)


def test_mixed_object_arithmetic():
    # title answered: 1 of 1. leaf absent: 0 of 1. leaves: (2 of 2) + (1 of 2) = 3 of 4.
    # Together 4 answered of 6 total.
    obj = _Holder(title="t", leaves=[_Leaf(name="a", note="n"), _Leaf(name="b")])
    assert field_counts(obj) == (4, 6)
    assert completeness(obj) == pytest.approx(4 / 6 * 100)
