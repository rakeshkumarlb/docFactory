"""The JSON file of each knowledge fact under knowledgefacts/ (a view of KnowledgeFacts.Value, written only by code; never edited by hand).

One file per fact key, the key segments as folders: ReadmeForge.Components.api.Architecture -> knowledgefacts/ReadmeForge/Components/api/Architecture.json.
The file holds only the fact's JSON value, in model field order; the OKF metadata stays in the table.

    python -m docfactory.fact_files      (rewrite every file from the database, remove files of facts that no longer exist)
"""
import json
import os
import re
import sys
from pathlib import Path

from docfactory import db
from docfactory.db import PROJECT_ROOT

ENV_VAR = "DOCFACTORY_KNOWLEDGEFACTS"
FACTS_DIR = "knowledgefacts"
_UNSAFE = re.compile(r'[\x00-\x1f/\\:*?"<>|]')
_RESERVED_NAMES = {"con", "prn", "aux", "nul", *(f"com{n}" for n in range(1, 10)), *(f"lpt{n}" for n in range(1, 10))}


def facts_root() -> Path:
    """The folder of the fact files: env DOCFACTORY_KNOWLEDGEFACTS, else knowledgefacts/ under the project root."""
    override = os.environ.get(ENV_VAR)
    return Path(override) if override else PROJECT_ROOT / FACTS_DIR


def file_path_of(key: str) -> str:
    """The path of a fact's file relative to the folder, forward slashes: Shared.Kpis -> Shared/Kpis.json.

    Raises ValueError when a key segment (component names are free text) could leave the folder or is not a legal file name.
    """
    segments = key.split(".")
    for segment in segments:
        if not segment or segment != segment.strip() or _UNSAFE.search(segment) or segment.lower() in _RESERVED_NAMES:
            raise ValueError(f"key segment {segment!r} of {key!r} cannot be used as a file name")
    return "/".join(segments) + ".json"


def file_text(ordered_json: str) -> str:
    """The file content: the JSON value indented, keys in the given (model) order, ending with a newline."""
    return json.dumps(json.loads(ordered_json), indent=2, ensure_ascii=False) + "\n"


def write_file(key: str, ordered_json: str) -> bool:
    """Write the fact's file (creating folders). Returns False, touching nothing, when the content is already there."""
    root = facts_root().resolve()
    target = (root / file_path_of(key)).resolve()
    if root not in target.parents:
        raise ValueError(f"{key!r} is outside the knowledge facts folder")
    data = file_text(ordered_json).encode("utf-8")
    if target.is_file() and target.read_bytes() == data:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return True


def rebuild() -> tuple[int, int, int]:
    """Rewrite every fact file from the database and remove files no fact owns. Returns (written, already current, removed)."""
    from docfactory.saver_resolution import ordered_value  # saver resolution imports the savers, which import this module

    written = current = 0
    expected = set()
    for row in db.list_rows("KnowledgeFacts"):
        expected.add(file_path_of(row["FactKey"]))
        if write_file(row["FactKey"], ordered_value(row["FactKey"], row["Value"])):
            written += 1
        else:
            current += 1
    root = facts_root()
    removed = 0
    if root.is_dir():
        for path in sorted(root.rglob("*.json")):
            if path.relative_to(root).as_posix() not in expected:
                path.unlink()
                removed += 1
    return written, current, removed


def main() -> int:
    written, current, removed = rebuild()
    print(f"{written} written, {current} already current, {removed} removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
