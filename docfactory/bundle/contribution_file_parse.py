"""Reads a contribution concept file back into a FactContribution; the hash of its `# Value` block must match its hashcode."""
import json

from pydantic import ValidationError

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.contribution_file_render import CONTRIBUTION_TYPE
from docfactory.bundle.fact_file_parse import split_frontmatter, value_block
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.bundle.paths import EXISTING_RESOURCE
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.fact_contribution import FactContribution


def parse_contribution_file(text: str) -> FactContribution:
    """The record stored in `text`; BundleError when it is not a contribution concept or was changed outside the system."""
    try:
        frontmatter_text, body = split_frontmatter(text)
        meta = load_frontmatter(frontmatter_text)
        if meta.get("type") != CONTRIBUTION_TYPE:
            raise ValueError(f"type is {meta.get('type')!r}, not {CONTRIBUTION_TYPE!r}")
        value = canonical_json(json.loads(value_block(body)))
        if sha256_hex(value) != meta["hashcode"]:
            raise ValueError("the stored JSON does not match its hashcode; the file was edited outside the system")
        sources = meta.get("sources") or []
        return FactContribution(
            fact_key=meta["fact_key"], resource=sources[0]["resource"] if sources else EXISTING_RESOURCE, value_json=value,
            hashcode=meta["hashcode"], chunks_hash=meta.get("chunks_hash"), description=meta.get("description"),
            generated_by=meta["generated"]["by"], timestamp=meta["generated"]["at"],
        )
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise BundleError(f"not a readable contribution: {error}") from error
