"""Read single scalar values from the deterministic frontmatter text written by okf_frontmatter (no YAML library needed)."""
import json
import re


def frontmatter_value(frontmatter: str | None, name: str) -> str | None:
    """The value of a top-level `name: value` line (a JSON string is decoded), or None when absent."""
    if not frontmatter:
        return None
    match = re.search(rf"^{re.escape(name)}: (.*)$", frontmatter, re.MULTILINE)
    if match is None:
        return None
    raw = match.group(1).strip()
    if raw.startswith('"'):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw
