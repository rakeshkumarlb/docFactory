"""Reads an item's concept file back into an ItemRecord (`value` = canonical JSON of the `# Value` block). Checking it against the item model and its hash is BundleStore's job."""
import json

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.fact_file_parse import split_frontmatter, value_block
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.canonical import canonical_json
from docfactory.models.item_record import ItemRecord


def parse_item_file(text: str, relpath: str) -> ItemRecord:
    """The record stored in `text`; BundleError when the file is not an item file."""
    try:
        frontmatter_text, body = split_frontmatter(text)
        meta = load_frontmatter(frontmatter_text)
        return ItemRecord(
            parent_key=meta["fact_key"], field=meta["item_field"], item_id=str(meta["item_id"]), position=meta["position"],
            value=canonical_json(json.loads(value_block(body))), hashcode=meta["hashcode"], version=meta["version"],
            completeness=meta["completeness"], relpath=relpath,
        )
    except (ValueError, KeyError, TypeError) as error:
        raise BundleError(f"not a readable item file: {error}") from error
