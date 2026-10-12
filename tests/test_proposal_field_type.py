from docfactory.models.proposal_field_type import ProposalFieldType


def test_members_and_values():
    assert [member.name for member in ProposalFieldType] == ["TEXT", "TEXT_LIST", "NUMBER", "FLAG"]
    assert [member.value for member in ProposalFieldType] == ["str", "list[str]", "int | None", "bool"]


def test_compares_equal_to_its_text():
    assert ProposalFieldType("bool") is ProposalFieldType.FLAG
