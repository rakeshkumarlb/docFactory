from enum import StrEnum


class NeedsOrigin(StrEnum):
    """Where a needs list came from: llm (checked LLM call), fallback (the call failed; one need per gap) or no_llm (generate ran with --no-llm; one need per gap)."""

    LLM = "llm"
    FALLBACK = "fallback"
    NO_LLM = "no_llm"
