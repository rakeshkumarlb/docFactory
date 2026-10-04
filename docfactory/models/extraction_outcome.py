from enum import StrEnum


class ExtractionOutcome(StrEnum):
    """Outcome of extracting one entity from one DocStore file: SAVED (the merged fact was created or updated), UNCHANGED (the merged fact's value did not change), SKIPPED_UNCHANGED_CHUNKS (the entity's chunks in this file are unchanged since its stored contribution: no LLM call), SKIPPED_SCOPE (no fact key for this entity from this file, e.g. Slo in an application document or any file in general/), REMOVED (the entity is no longer tagged in this file: its contribution was deleted and the fact re-merged from the other files), REJECTED (the merged fact failed validation, e.g. a mandatory field no document states yet; the file's contribution is kept) or FAILED (no batch gave an accepted answer; nothing was stored)."""

    SAVED = "SAVED"
    UNCHANGED = "UNCHANGED"
    SKIPPED_UNCHANGED_CHUNKS = "SKIPPED_UNCHANGED_CHUNKS"
    SKIPPED_SCOPE = "SKIPPED_SCOPE"
    REMOVED = "REMOVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
