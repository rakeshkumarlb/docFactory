from enum import StrEnum


class NonFunctionalCategory(StrEnum):
    """Quality category of a non-functional requirement, e.g. PERFORMANCE or SECURITY."""

    PERFORMANCE = "PERFORMANCE"
    AVAILABILITY = "AVAILABILITY"
    SECURITY = "SECURITY"
    USABILITY = "USABILITY"
    MAINTAINABILITY = "MAINTAINABILITY"
    COMPLIANCE = "COMPLIANCE"
    OTHER = "OTHER"
