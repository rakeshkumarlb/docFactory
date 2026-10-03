from enum import StrEnum


class FileAction(StrEnum):
    """Outcome of comparing or storing a file against DocStore: NEW (no stored row), SAME (identical hash, no-op) or CHANGED (different hash, replaces and bumps the version)."""

    NEW = "NEW"
    SAME = "SAME"
    CHANGED = "CHANGED"
