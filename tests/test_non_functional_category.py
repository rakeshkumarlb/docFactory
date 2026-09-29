from docfactory.entitymodels.items.non_functional_category import NonFunctionalCategory


def test_members_and_values():
    assert [member.name for member in NonFunctionalCategory] == [
        "PERFORMANCE", "AVAILABILITY", "SECURITY", "USABILITY", "MAINTAINABILITY", "COMPLIANCE", "OTHER",
    ]
    assert all(member.value == member.name for member in NonFunctionalCategory)
