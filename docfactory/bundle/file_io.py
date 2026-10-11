"""Writing a text file the safe way: all or nothing, and not at all when nothing changed."""
import os
from pathlib import Path


def put_text(target: Path, text: str) -> bool:
    """Write `text` (UTF-8, LF) to `target` through a temporary file and an atomic replace, creating folders.
    Returns False, touching nothing, when the file already holds exactly these bytes."""
    data = text.encode("utf-8")
    if target.is_file() and target.read_bytes() == data:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, target)
    return True
