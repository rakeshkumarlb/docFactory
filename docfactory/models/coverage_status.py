from enum import StrEnum


class CoverageStatus(StrEnum):
    """What became of one chunk of an ingested original: EXTRACTED (an entity it is tagged with was extracted from exactly these chunks, so its content is in a fact), NOTED (no entity claimed it, but discovery kept it in a note of the Note fact), NOT_EXTRACTED (it is tagged with an entity that can have a fact from this file, but no up-to-date extraction covers it: not run yet, a batch failed, or the chunks changed), SKIPPED_SCOPE (every entity it is tagged with gets no fact from this file, e.g. Slo in an application document or any file in general/: its content is not in any fact) or UNMAPPED (no entity is tagged on it: its content is in no fact). NOTED counts as kept: the content is in a note, not lost."""

    EXTRACTED = "EXTRACTED"
    NOTED = "NOTED"
    NOT_EXTRACTED = "NOT_EXTRACTED"
    SKIPPED_SCOPE = "SKIPPED_SCOPE"
    UNMAPPED = "UNMAPPED"
