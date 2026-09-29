from enum import StrEnum


class RequirementPriority(StrEnum):
    """MoSCoW priority of a requirement: MUST, SHOULD, COULD or WONT (agreed not to be delivered now)."""

    MUST = "MUST"
    SHOULD = "SHOULD"
    COULD = "COULD"
    WONT = "WONT"
