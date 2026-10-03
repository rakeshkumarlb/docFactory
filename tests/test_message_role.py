from docfactory.models.message_role import MessageRole


def test_members_and_values():
    assert [member.name for member in MessageRole] == ["USER", "ASSISTANT", "TOOL"]
    assert [member.value for member in MessageRole] == ["user", "assistant", "tool"]


def test_compares_equal_to_its_text():
    assert MessageRole("tool") is MessageRole.TOOL
    assert MessageRole.USER == "user"
