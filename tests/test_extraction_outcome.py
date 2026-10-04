from docfactory.models.extraction_outcome import ExtractionOutcome


def test_members_and_values():
    assert [member.name for member in ExtractionOutcome] == [
        "SAVED",
        "UNCHANGED",
        "SKIPPED_UNCHANGED_CHUNKS",
        "SKIPPED_SCOPE",
        "REMOVED",
        "REJECTED",
        "FAILED",
    ]
    assert all(member.value == member.name for member in ExtractionOutcome)


def test_compares_equal_to_its_text():
    assert ExtractionOutcome.SAVED == "SAVED"
    assert ExtractionOutcome("FAILED") is ExtractionOutcome.FAILED
