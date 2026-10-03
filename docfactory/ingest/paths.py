import os
from pathlib import Path

from docfactory.db import PROJECT_ROOT

INCOMING_ENV = "DOCFACTORY_INCOMING"
DOCSTORE_ENV = "DOCFACTORY_DOCSTORE"
STAGING_ENV = "DOCFACTORY_STAGING"


def incoming_dir() -> Path:
    """The drop zone for new originals: env DOCFACTORY_INCOMING, else incoming/ under the project root."""
    return Path(os.environ.get(INCOMING_ENV) or PROJECT_ROOT / "incoming")


def docstore_dir() -> Path:
    """The store of classified originals: env DOCFACTORY_DOCSTORE, else DocStore/ under the project root."""
    return Path(os.environ.get(DOCSTORE_ENV) or PROJECT_ROOT / "DocStore")


def staging_dir() -> Path:
    """Where files wait while they are chunked and tagged, and stay when a human must decide: env DOCFACTORY_STAGING, else staging/."""
    return Path(os.environ.get(STAGING_ENV) or PROJECT_ROOT / "staging")


def resolve_within(root: Path, relative: str) -> Path:
    """`relative` (forward slashes) resolved under `root`. Raises ValueError for absolute paths, empty paths or any escape from `root`."""
    if not relative or not relative.strip("/"):
        raise ValueError("path is empty")
    if Path(relative).is_absolute() or relative.startswith(("/", "\\")):
        raise ValueError(f"path must be relative: {relative!r}")
    base = root.resolve()
    target = (base / relative).resolve()
    if target == base or base not in target.parents:
        raise ValueError(f"path escapes {root.name}/: {relative!r}")
    return target
