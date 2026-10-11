"""Key patterns of facts: whole-segment matching of a key against a pattern such as `{app}.Components.{component}.Architecture`."""
import re

SHARED = "Shared"
PLACEHOLDER = re.compile(r"\{(app|component|doctype)\}")


def pattern_matches(pattern: str, key: str) -> bool:
    """Whole-segment match. `{app}`, `{component}`, `{doctype}` stand for one non-empty segment; `Shared` is not an `{app}`."""
    segments, parts = pattern.split("."), key.split(".")
    if len(segments) != len(parts):
        return False
    for segment, part in zip(segments, parts):
        if PLACEHOLDER.fullmatch(segment):
            if not part or (segment == "{app}" and part == SHARED):
                return False
        elif segment != part:
            return False
    return True
