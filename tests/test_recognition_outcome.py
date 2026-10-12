from docfactory.models.recognition_outcome import RecognitionOutcome


def test_members_and_values():
    assert [member.name for member in RecognitionOutcome] == ["RECOGNIZED", "UNCHANGED", "PARTIAL", "FAILED"]
    assert all(member.value == member.name for member in RecognitionOutcome)


def test_compares_equal_to_its_text():
    assert RecognitionOutcome.PARTIAL == "PARTIAL"
    assert RecognitionOutcome("FAILED") is RecognitionOutcome.FAILED
