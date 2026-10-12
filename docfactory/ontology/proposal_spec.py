"""Turns a stored TypeProposal into the inputs of the deterministic scaffold scripts and the ontology: model specs and the signals entry. Pure functions, writes nothing.

The specs follow `.claude/skills/docfactory-field-spec`; defaults and test examples are chosen by code from the field kind, so a proposal cannot
smuggle in an invented default. Only the identifying first field of an item is mandatory.
"""
import json

from docfactory.models.proposal_field import ProposalField
from docfactory.models.proposal_field_type import ProposalFieldType
from docfactory.models.type_proposal import TypeProposal
from docfactory.ontology.proposal_checks import snake

DEFAULTS = {ProposalFieldType.TEXT: "''", ProposalFieldType.TEXT_LIST: "[]", ProposalFieldType.NUMBER: "None", ProposalFieldType.FLAG: "False"}
EXAMPLES = {ProposalFieldType.TEXT: '"Test value"', ProposalFieldType.TEXT_LIST: '["Test value"]', ProposalFieldType.NUMBER: "1", ProposalFieldType.FLAG: "True"}


def _field(field: ProposalField, required: bool = False) -> dict:
    spec = {"name": field.name, "type": field.type.value, "default": "REQUIRED" if required else DEFAULTS[field.type],
            "description": field.description, "question": field.question, "example": EXAMPLES[field.type]}
    if required:
        spec["min_length"] = 1
    return spec


def item_spec(proposal: TypeProposal) -> dict | None:
    """The model spec of the item type, or None when the proposal has no list of items."""
    if not proposal.item_entity:
        return None
    fields = [_field(f, required=(i == 0)) for i, f in enumerate(proposal.item_fields)]
    return {"class": proposal.item_entity, "doc": proposal.item_doc, "fields": fields}


def fact_spec(proposal: TypeProposal) -> dict:
    """The model spec of the fact: its own fields, then the list of items."""
    fields = [_field(f) for f in proposal.fields]
    spec = {"class": proposal.entity, "doc": proposal.doc, "fields": fields}
    if proposal.item_entity:
        label = proposal.list_name.replace("_", " ")
        fields.append({"name": proposal.list_name, "type": f"list[{proposal.item_entity}]", "default": "[]", "example": "[]",
                       "description": f"The {label} of the application, one entry per item the documents state, e.g. one {proposal.item_entity}. Empty when none were stated.",
                       "question": f"Which {label} does the application have?"})
        spec["imports"] = [f"from docfactory.entitymodels.items.{snake(proposal.item_entity)} import {proposal.item_entity}"]
    return spec


def signals_entry(proposal: TypeProposal) -> str:
    """The text of the entry for `signals.json`, in the file's own layout (no trailing comma)."""
    def line(name: str, values: list[str]) -> str:
        return f'    "{name}": ' + json.dumps(values, ensure_ascii=False)
    return "  {\n" + f'    "entity": "{proposal.entity}",\n' + ",\n".join([
        line("heading_terms", proposal.heading_terms), line("id_patterns", proposal.id_patterns), line("keywords", proposal.keywords)]) + "\n  }"
