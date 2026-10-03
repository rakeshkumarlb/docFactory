import hashlib
from pathlib import Path


def file_sha256(path: Path) -> str:
    """SHA-256 of the file's bytes, as lowercase hex."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
