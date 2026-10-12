"""The bundle's log.md (OKF section 9): date-grouped entries, newest date first."""
from pathlib import Path

from docfactory.bundle.file_io import put_text

LOG_FILE = "log.md"
TITLE = "# Directory Update Log"


def log_text(existing: str, date: str, entry: str) -> str:
    """`existing` log text with `* entry` added at the end of the `## date` section (the section is created at the top when new)."""
    lines = existing.splitlines() or [TITLE]
    heading = f"## {date}"
    if heading not in lines:
        at = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
        lines[at:at] = [heading, entry, ""] if at < len(lines) else ["", heading, entry]
    else:
        start = lines.index(heading) + 1
        end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
        while end > start and not lines[end - 1].strip():
            end -= 1
        lines.insert(end, entry)
    return "\n".join(lines).rstrip("\n") + "\n"


def append_entry(root: Path, date: str, entry: str) -> None:
    """Add the line `entry` (starting with '* ') to the `date` section of log.md."""
    target = root / LOG_FILE
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    put_text(target, log_text(existing, date, entry))


def append_log(root: Path, date: str, action: str, key: str, relpath: str, version: int, actor: str, detail: str = "") -> None:
    """Record one change of a concept: `* **Creation**: [key](/path.md) v1 by actor` (action is Creation, Update or Deprecation); `detail` is appended, e.g. ' (items +2 ~1 -0)'."""
    append_entry(root, date, f"* **{action}**: [{key}](/{relpath}) v{version} by {actor}{detail}")
