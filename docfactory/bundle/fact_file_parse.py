"""Reads a fact's concept file back into a FactRecord (metadata from the frontmatter, `value` = canonical JSON of the `# Value` block).

The block is not yet checked against the entity model or the stored hash; BundleStore does that.
"""
import json

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.fact_file_render import FENCE, VALUE_HEADING
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.canonical import canonical_json
from docfactory.models.fact_record import FactRecord
from docfactory.models.fact_source import FactSource
from docfactory.models.fact_status import FactStatus
from docfactory.models.fact_verification import FactVerification

_OPEN = "---\n"
_CLOSE = "\n---\n"


def split_frontmatter(text: str) -> tuple[str, str]:
    """(the frontmatter text, the body) of a concept file; ValueError when the frontmatter block is missing or not closed."""
    if not text.startswith(_OPEN):
        raise ValueError("the file does not start with a frontmatter block")
    end = text.find(_CLOSE, len(_OPEN) - 1)
    if end < 0:
        raise ValueError("the frontmatter block is not closed")
    return text[len(_OPEN):end + 1], text[end + len(_CLOSE):]


def value_block(body: str) -> str:
    """The text of the fenced block under the `# Value` heading; ValueError when there is none."""
    lines = body.splitlines()
    try:
        start = lines.index(VALUE_HEADING)
        opening = next(i for i in range(start + 1, len(lines)) if lines[i].startswith(FENCE))
        closing = next(i for i in range(opening + 1, len(lines)) if lines[i] == FENCE)
    except (ValueError, StopIteration):
        raise ValueError(f"no `{VALUE_HEADING}` heading followed by a fenced JSON block") from None
    return "\n".join(lines[opening + 1:closing])


def _events(raw) -> list[FactVerification]:
    if raw is None:
        return []
    return [FactVerification.model_validate(event) for event in (raw if isinstance(raw, list) else [raw])]


def parse_fact_file(text: str) -> FactRecord:
    """The record stored in `text`; BundleError when the file is not a fact file."""
    try:
        frontmatter_text, body = split_frontmatter(text)
        meta = load_frontmatter(frontmatter_text)
        value = canonical_json(json.loads(value_block(body)))
        generated = meta.get("generated") or {}
        key = meta["fact_key"]
        return FactRecord(
            key=key, value=value, hashcode=meta["hashcode"], completeness=meta["completeness"], version=meta["version"],
            app_id=None if key.split(".")[0] == "Shared" else key.split(".")[0],
            type=meta.get("type"), title=meta.get("title"), description=meta.get("description"), tags=meta.get("tags") or [],
            sources=[FactSource.model_validate(source) for source in meta.get("sources") or []],
            frontmatter=frontmatter_text, generated_by=generated.get("by"), generated_at=generated.get("at"),
            verified=_events(meta.get("verified")), status=FactStatus(meta.get("status", FactStatus.STABLE.value)),
            stale_after=meta.get("stale_after"),
        )
    except (ValueError, KeyError, TypeError) as error:
        raise BundleError(f"not a readable fact file: {error}") from error
