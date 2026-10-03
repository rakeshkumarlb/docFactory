from docfactory.models.fact_status import FactStatus


def test_members_and_values():
    assert [member.name for member in FactStatus] == ["DRAFT", "STABLE", "DEPRECATED"]
    assert [member.value for member in FactStatus] == ["draft", "stable", "deprecated"]


def test_compares_equal_to_its_text():
    assert FactStatus.DRAFT == "draft"
    assert FactStatus("deprecated") is FactStatus.DEPRECATED
