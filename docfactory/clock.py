from datetime import datetime, timezone


def now_iso() -> str:
    """The current UTC time as an ISO 8601 datetime with explicit offset, e.g. 2026-10-03T10:00:00Z. Tests replace this function."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
