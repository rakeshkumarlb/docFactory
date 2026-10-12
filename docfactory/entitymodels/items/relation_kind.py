from enum import StrEnum


class RelationKind(StrEnum):
    """The kinds of relationship one item states about another: DEPENDS_ON (cannot work without it), IMPLEMENTS (realises it), REFINES (adds detail to it), INTEGRATES_WITH (exchanges data with it), MONITORS (watches it), CONFLICTS_WITH (cannot hold together with it), RELATES_TO (connected in a way none of the others names)."""

    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    REFINES = "refines"
    INTEGRATES_WITH = "integrates_with"
    MONITORS = "monitors"
    CONFLICTS_WITH = "conflicts_with"
    RELATES_TO = "relates_to"
