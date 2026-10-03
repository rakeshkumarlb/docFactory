import os
from pathlib import Path

from docfactory.db import PROJECT_ROOT


def load_env_file(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from .env (project root by default) into os.environ.

    Variables already set in the environment win, so a shell value overrides the file. Blank lines and '#' comments are
    skipped, and surrounding quotes on a value are removed. A missing file is not an error.
    """
    path = path or PROJECT_ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
