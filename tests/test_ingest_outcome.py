from docfactory.models.ingest_outcome import IngestOutcome


def test_members_and_values():
    assert [member.name for member in IngestOutcome] == ["NEW", "CHANGED", "SAME", "REPAIRED", "STAGED"]
    assert all(member.value == member.name for member in IngestOutcome)


def test_compares_equal_to_its_text():
    assert IngestOutcome.REPAIRED == "REPAIRED"
    assert IngestOutcome("STAGED") is IngestOutcome.STAGED
