from enum import StrEnum


class RecognitionOutcome(StrEnum):
    """Outcome of recognizing one ingested original: RECOGNIZED (every window has an accepted recognition, at least one was new), UNCHANGED (every window was unchanged since the stored recognition: no LLM call), PARTIAL (some windows failed and are retried on the next run; the accepted ones are stored) or FAILED (no window gave an accepted answer; nothing was stored)."""

    RECOGNIZED = "RECOGNIZED"
    UNCHANGED = "UNCHANGED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
