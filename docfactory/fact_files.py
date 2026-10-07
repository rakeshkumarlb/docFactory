"""The files of each knowledge fact under knowledgefacts/ (views of KnowledgeFacts.Value, written only by code; never edited by hand).

One JSON file per fact key, the key segments as folders: ReadmeForge.Components.api.Architecture -> knowledgefacts/ReadmeForge/Components/api/Architecture.json.
It holds only the fact's JSON value, in model field order; the OKF metadata stays in the table. Next to it, <Entity>.missing.md lists the
fact's open questions (open_questions.py); a fact with none has no such file.

    python -m docfactory.fact_files      (rewrite every file from the database, remove files of facts that no longer exist)
"""
import json
import os
import re
import sys
from pathlib import Path

from pydantic import BaseModel

from docfactory import db
from docfactory.db import PROJECT_ROOT
from docfactory.missing_md import missing_md
from docfactory.open_questions import open_questions

ENV_VAR = "DOCFACTORY_KNOWLEDGEFACTS"
FACTS_DIR = "knowledgefacts"
MISSING_SUFFIX = ".missing.md"
_UNSAFE = re.compile(r'[\x00-\x1f/\\:*?"<>|]')
_RESERVED_NAMES = {"con", "prn", "aux", "nul", *(f"com{n}" for n in range(1, 10)), *(f"lpt{n}" for n in range(1, 10))}


def facts_root() -> Path:
    """The folder of the fact files: env DOCFACTORY_KNOWLEDGEFACTS, else knowledgefacts/ under the project root."""
    override = os.environ.get(ENV_VAR)
    return Path(override) if override else PROJECT_ROOT / FACTS_DIR


def file_path_of(key: str) -> str:
    """The path of a fact's JSON file relative to the folder, forward slashes: Shared.Kpis -> Shared/Kpis.json.

    Raises ValueError when a key segment (component names are free text) could leave the folder or is not a legal file name.
    """
    segments = key.split(".")
    for segment in segments:
        if not segment or segment != segment.strip() or _UNSAFE.search(segment) or segment.lower() in _RESERVED_NAMES:
            raise ValueError(f"key segment {segment!r} of {key!r} cannot be used as a file name")
    return "/".join(segments) + ".json"


def missing_path_of(key: str) -> str:
    """The path of a fact's open-questions file relative to the folder: Shared.Kpis -> Shared/Kpis.missing.md."""
    return file_path_of(key).removesuffix(".json") + MISSING_SUFFIX


def file_text(ordered_json: str) -> str:
    """The JSON file content: the value indented, keys in the given (model) order, ending with a newline."""
    return json.dumps(json.loads(ordered_json), indent=2, ensure_ascii=False) + "\n"


def _target(relative: str) -> Path:
    root = facts_root().resolve()
    target = (root / relative).resolve()
    if root not in target.parents:
        raise ValueError(f"{relative!r} is outside the knowledge facts folder")
    return target


def _put(target: Path, text: str | None) -> bool:
    """Write `text` to `target`, or remove the file when `text` is None. Returns False, touching nothing, when it is already so."""
    if text is None:
        if not target.exists():
            return False
        target.unlink()
        return True
    data = text.encode("utf-8")
    if target.is_file() and target.read_bytes() == data:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return True


def write_file(key: str, fact: BaseModel) -> bool:
    """Write the validated fact's JSON file and its open-questions file (removed when nothing is open), creating folders.
    Returns False, touching nothing, when both are already current."""
    questions = open_questions(fact)
    wrote_json = _put(_target(file_path_of(key)), file_text(fact.model_dump_json()))
    wrote_missing = _put(_target(missing_path_of(key)), missing_md(key, questions) if questions else None)
    return wrote_json or wrote_missing


def rebuild() -> tuple[int, int, int]:
    """Rewrite every fact's files from the database and remove files no fact owns. Returns (facts written, already current, files removed).
    A stored key no entity saver owns is skipped, so its files count as orphans."""
    from docfactory.saver_resolution import saver_for_key  # saver resolution imports the savers, which import this module

    written = current = 0
    expected = set()
    for row in db.list_rows("KnowledgeFacts"):
        saver = saver_for_key(row["FactKey"])
        if saver is None:
            continue
        expected |= {file_path_of(row["FactKey"]), missing_path_of(row["FactKey"])}
        if write_file(row["FactKey"], saver.model.model_validate_json(row["Value"])):
            written += 1
        else:
            current += 1
    root = facts_root()
    removed = 0
    if root.is_dir():
        for path in sorted([*root.rglob("*.json"), *root.rglob(f"*{MISSING_SUFFIX}")]):
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
