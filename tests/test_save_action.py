from docfactory.models.save_action import SaveAction


def test_members_and_values():
    assert [member.name for member in SaveAction] == ["CREATED", "UPDATED", "UNCHANGED", "REJECTED"]
    assert all(member.value == member.name for member in SaveAction)


def test_compares_equal_to_its_text():
    assert SaveAction.CREATED == "CREATED"
    assert SaveAction("REJECTED") is SaveAction.REJECTED
