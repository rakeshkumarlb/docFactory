from docfactory.models.file_action import FileAction


def test_members_and_values():
    assert [member.name for member in FileAction] == ["NEW", "SAME", "CHANGED"]
    assert all(member.value == member.name for member in FileAction)


def test_compares_equal_to_its_text():
    assert FileAction.NEW == "NEW"
    assert FileAction("CHANGED") is FileAction.CHANGED
