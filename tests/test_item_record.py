import pytest
from pydantic import ValidationError

from docfactory.models.item_record import ItemRecord

MINIMAL = {"parent_key": "Test.Entity", "field": "items", "item_id": "I-1", "position": 1, "value": "{}", "hashcode": "a" * 64, "version": 1, "completeness": 50.0}
FULL = {"parent_key": "Test.Entity", "field": "items", "item_id": "I-1", "position": 1, "value": "{}", "hashcode": "a" * 64, "version": 2, "completeness": 50.0, "relpath": "Test/Entity/items/I-1.md"}


def test_minimal_payload_is_valid():
    ItemRecord.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ItemRecord.model_validate(FULL)
    assert ItemRecord.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["parent_key", "field", "item_id", "position", "value", "hashcode", "version", "completeness"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ItemRecord.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ItemRecord.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = ItemRecord.model_validate(MINIMAL)
    assert obj.relpath == ""


def test_bounds_and_hash_shape():
    for bad in ({"position": 0}, {"version": 0}, {"hashcode": "xyz"}, {"parent_key": ""}, {"field": ""}):
        with pytest.raises(ValidationError):
            ItemRecord.model_validate({**FULL, **bad})
