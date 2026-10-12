import pytest
from pydantic import ValidationError

from docfactory.models.window_recognition import WindowRecognition
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.chunk_topic import ChunkTopic
from docfactory.models.recognized_entity import RecognizedEntity
from docfactory.models.recognized_relation import RecognizedRelation

MINIMAL = {
    "window_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
}

FULL = {
    "window_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "chunk_nos": [1, 2],
    "entities": [],
    "relations": [],
    "topics": [],
}


def test_minimal_payload_is_valid():
    WindowRecognition.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = WindowRecognition.model_validate(FULL)
    assert WindowRecognition.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["window_hash"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        WindowRecognition.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        WindowRecognition.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = WindowRecognition.model_validate(MINIMAL)
    assert obj.chunk_nos == []
    assert obj.entities == []
    assert obj.relations == []
    assert obj.topics == []


@pytest.mark.parametrize("field", ["window_hash"])
def test_text_not_matching_the_pattern_is_rejected(field):
    with pytest.raises(ValidationError):
        WindowRecognition.model_validate({**FULL, field: "not matching the pattern"})


@pytest.mark.parametrize("field", ["window_hash", "chunk_nos", "entities", "relations", "topics"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        WindowRecognition.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
