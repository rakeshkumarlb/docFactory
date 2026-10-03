from enum import StrEnum


class IngestOutcome(StrEnum):
    """Outcome of ingesting one file: NEW (stored first time), CHANGED (same name, different hash: replaced, version + 1), SAME (identical bytes already stored and on disk: staged copy discarded), REPAIRED (row with this hash existed but the stored file was missing: file put back, chunks rewritten, version unchanged) or STAGED (left in staging/ with a reason)."""

    NEW = "NEW"
    CHANGED = "CHANGED"
    SAME = "SAME"
    REPAIRED = "REPAIRED"
    STAGED = "STAGED"
