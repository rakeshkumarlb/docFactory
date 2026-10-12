from enum import StrEnum


class ProposalFieldType(StrEnum):
    """The kinds of field a proposed entity type may use: TEXT (a string, default empty), TEXT_LIST (a list of strings, default empty), NUMBER (a whole number or None) and FLAG (true or false, default false). Richer shapes are added by a developer when the proposal is reviewed."""

    TEXT = "str"
    TEXT_LIST = "list[str]"
    NUMBER = "int | None"
    FLAG = "bool"
