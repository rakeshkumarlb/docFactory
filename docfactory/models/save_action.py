from enum import StrEnum


class SaveAction(StrEnum):
    """What a save did: CREATED (new row), UPDATED (changed value), UNCHANGED (same hash) or REJECTED (nothing written)."""

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    REJECTED = "REJECTED"
