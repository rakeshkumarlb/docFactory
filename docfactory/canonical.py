import hashlib
import json


def canonical_json(value) -> str:
    """Canonical JSON text of a JSON-compatible value: sorted keys, no extra whitespace, UTF-8 characters kept."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    """SHA-256 of the UTF-8 bytes of `text`, as lowercase hex."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
