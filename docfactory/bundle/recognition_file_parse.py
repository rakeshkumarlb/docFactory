"""Reads a recognition concept file back into a FileRecognition; the hash of its `# Value` block must match its hashcode."""
import json

from pydantic import ValidationError

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.fact_file_parse import split_frontmatter, value_block
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.bundle.recognition_file_render import RECOGNITION_TYPE
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.file_recognition import FileRecognition
from docfactory.models.window_recognition import WindowRecognition


def parse_recognition_file(text: str) -> FileRecognition:
    """The record stored in `text`; BundleError when it is not a recognition concept or was changed outside the system."""
    try:
        frontmatter_text, body = split_frontmatter(text)
        meta = load_frontmatter(frontmatter_text)
        if meta.get("type") != RECOGNITION_TYPE:
            raise ValueError(f"type is {meta.get('type')!r}, not {RECOGNITION_TYPE!r}")
        windows = json.loads(value_block(body))
        if sha256_hex(canonical_json(windows)) != meta["hashcode"]:
            raise ValueError("the stored JSON does not match its hashcode; the file was edited outside the system")
        return FileRecognition(resource=meta["sources"][0]["resource"], windows=[WindowRecognition.model_validate(w) for w in windows],
                               hashcode=meta["hashcode"], generated_by=meta["generated"]["by"], timestamp=meta["generated"]["at"])
    except (ValueError, KeyError, TypeError, IndexError, ValidationError) as error:
        raise BundleError(f"not a readable recognition: {error}") from error
