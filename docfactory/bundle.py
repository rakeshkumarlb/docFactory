"""OKF bundle files under bundles/ (views of KnowledgeFacts, written only by code): paths and the file writer."""
import os
import re
from pathlib import Path

from docfactory.db import PROJECT_ROOT

ENV_VAR = "DOCFACTORY_BUNDLES"
BUNDLE_DIR = "bundles"
_UNSAFE = re.compile(r'[\x00-\x1f/\\:*?"<>|]')
_RESERVED_NAMES = {"con", "prn", "aux", "nul", *(f"com{n}" for n in range(1, 10)), *(f"lpt{n}" for n in range(1, 10))}


def bundles_root() -> Path:
    """The bundle folder: env DOCFACTORY_BUNDLES, else bundles/ under the project root."""
    override = os.environ.get(ENV_VAR)
    return Path(override) if override else PROJECT_ROOT / BUNDLE_DIR


def file_path_of(key: str) -> str:
    """The stored FilePath of a fact key: ReadmeForge.Components.api.Architecture -> bundles/ReadmeForge/Components/api/Architecture.md.

    Raises ValueError when a key segment (component names are free text) could leave the bundle folder or is not a legal file name.
    """
    segments = key.split(".")
    for segment in segments:
        if not segment or segment != segment.strip() or _UNSAFE.search(segment) or segment.lower() in _RESERVED_NAMES:
            raise ValueError(f"key segment {segment!r} of {key!r} cannot be used as a file name")
    return f"{BUNDLE_DIR}/" + "/".join(segments) + ".md"


def file_text(frontmatter: str, body: str) -> str:
    """A whole concept file: frontmatter block, blank line, body."""
    return f"---\n{frontmatter}---\n\n{body}"


def write_file(file_path: str, text: str) -> bool:
    """Write the bundle file for a stored FilePath (creating folders). Returns False, touching nothing, when the content is already there."""
    root = bundles_root().resolve()
    target = (root / file_path.removeprefix(f"{BUNDLE_DIR}/")).resolve()
    if root not in target.parents:
        raise ValueError(f"{file_path!r} is outside the bundle folder")
    if target.is_file() and target.read_bytes() == text.encode("utf-8"):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text.encode("utf-8"))
    return True
