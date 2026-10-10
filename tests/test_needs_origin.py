from docfactory.documentmodels.needs_origin import NeedsOrigin


def test_members_and_values():
    assert [member.name for member in NeedsOrigin] == ["LLM", "FALLBACK", "NO_LLM"]
    assert [member.value for member in NeedsOrigin] == ["llm", "fallback", "no_llm"]
