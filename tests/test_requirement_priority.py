from docfactory.entitymodels.items.requirement_priority import RequirementPriority


def test_members_and_values():
    assert [member.name for member in RequirementPriority] == ["MUST", "SHOULD", "COULD", "WONT"]
    assert all(member.value == member.name for member in RequirementPriority)
