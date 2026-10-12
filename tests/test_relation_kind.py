from docfactory.entitymodels.items.relation_kind import RelationKind


def test_members_and_values():
    assert [member.name for member in RelationKind] == ["DEPENDS_ON", "IMPLEMENTS", "REFINES", "INTEGRATES_WITH", "MONITORS", "CONFLICTS_WITH", "RELATES_TO"]
    assert [member.value for member in RelationKind] == ["depends_on", "implements", "refines", "integrates_with", "monitors", "conflicts_with", "relates_to"]


def test_compares_equal_to_its_text():
    assert RelationKind("monitors") is RelationKind.MONITORS
