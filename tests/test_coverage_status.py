from docfactory.models.coverage_status import CoverageStatus


def test_members_and_values():
    assert [member.name for member in CoverageStatus] == ["EXTRACTED", "NOTED", "NOT_EXTRACTED", "SKIPPED_SCOPE", "UNMAPPED"]
    assert all(member.value == member.name for member in CoverageStatus)


def test_compares_equal_to_its_text():
    assert CoverageStatus.NOTED == "NOTED"
    assert CoverageStatus("UNMAPPED") is CoverageStatus.UNMAPPED
