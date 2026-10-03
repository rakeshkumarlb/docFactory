from enum import StrEnum


class FactStatus(StrEnum):
    """Lifecycle status of a knowledge fact (OKF status): DRAFT (not yet reviewed), STABLE (reviewed and trusted) or DEPRECATED (superseded, do not rely on it)."""

    DRAFT = "draft"
    STABLE = "stable"
    DEPRECATED = "deprecated"
