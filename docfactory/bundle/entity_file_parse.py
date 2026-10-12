"""Reads an entity concept file back: (the EntityRecord, its version, its hashcode); the hash of its `# Value` block must match its hashcode."""
import json

from pydantic import ValidationError

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.fact_file_parse import split_frontmatter, value_block
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.entity_record import EntityRecord


def parse_entity_file(text: str) -> tuple[EntityRecord, int, str]:
    """(record, version, hashcode) stored in `text`; BundleError when it is not an entity concept or was changed outside the system."""
    try:
        frontmatter_text, body = split_frontmatter(text)
        meta = load_frontmatter(frontmatter_text)
        value = json.loads(value_block(body))
        if sha256_hex(canonical_json(value)) != meta["hashcode"]:
            raise ValueError("the stored JSON does not match its hashcode; the file was edited outside the system")
        record = EntityRecord.model_validate(value)
        if record.entity_id != meta["entity_id"]:
            raise ValueError(f"entity_id {meta['entity_id']!r} does not match the value's {record.entity_id!r}")
        return record, int(meta["version"]), meta["hashcode"]
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise BundleError(f"not a readable entity: {error}") from error
