from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.proposal_field import ProposalField


class TypeProposal(DocFactoryModel):
    """A proposed new knowledge entity type, for the case where the ontology has no fit for a recurring kind of passage in the documents (for example Risks or Assumptions). It is a proposal only: a developer step creates the model from it, registers it and adds its tagging signals, after review."""

    entity: str = doc_field(
        description="Name of the new entity in PascalCase, plural when it holds a list, e.g. 'Risks'. Must not be an existing entity or nearly the same as one.",
        question="What is the new entity called (PascalCase)?",
        pattern="^[A-Z][A-Za-z0-9]+$",
    )
    doc: str = doc_field(
        description="One sentence saying what the entity holds, e.g. 'The risks of an application with their likelihood, impact and mitigation.'",
        question="What does this entity hold?",
        min_length=20,
    )
    scope: str = doc_field(
        default="app",
        description="'app' when the facts belong to one application (key <App>.<Entity>), 'shared' when they are common to all applications (key Shared.<Entity>), e.g. 'app'.",
        question="Is the entity specific to an application ('app') or common to all ('shared')?",
        pattern="^(app|shared)$",
    )
    fields: list[ProposalField] = doc_field(
        description="The fields of the entity itself (not of its items), at least one of them of kind 'str', e.g. a 'summary'.",
        question="Which fields does the entity have?",
        min_length=1,
    )
    list_name: str = doc_field(
        default="",
        description="Name of the list field that holds the items, snake_case plural, e.g. 'risks'. Empty when the entity has no list of items.",
        question="What is the list of items called?",
    )
    item_entity: str = doc_field(
        default="",
        description="Name of the item type in PascalCase, singular, e.g. 'Risk'. Empty when the entity has no list of items.",
        question="What is one item called (PascalCase, singular)?",
    )
    item_doc: str = doc_field(
        default="",
        description="One sentence saying what one item is, e.g. 'One risk with its likelihood, impact and mitigation.' Empty when there are no items.",
        question="What is one item?",
    )
    item_fields: list[ProposalField] = doc_field(
        default_factory=list,
        description="The fields of one item. The first one identifies the item (kind 'str', mandatory), e.g. 'name'. Empty when there are no items.",
        question="Which fields does one item have?",
    )
    heading_terms: list[str] = doc_field(
        description="Lower-case phrases that occur in the headings of the passages that hold this knowledge, e.g. ['risks', 'risk register']. At least one. They must not already signal another entity.",
        question="Which heading phrases signal this entity?",
        min_length=1,
    )
    id_patterns: list[str] = doc_field(
        default_factory=list,
        description="Regular expressions matching the identifiers of the items in the text, e.g. ['\\\\bRISK-\\\\d+']. Empty when the items have none.",
        question="Which regular expressions match the identifiers of its items?",
    )
    keywords: list[str] = doc_field(
        default_factory=list,
        description="Lower-case words or phrases in the text that weakly signal the entity, e.g. ['likelihood', 'mitigation'].",
        question="Which words in the text weakly signal this entity?",
    )
    sample_chunks: list[int] = doc_field(
        description="Numbers of the chunks that hold this kind of knowledge, taken from the '[chunk N]' markers, e.g. [75]. At least one.",
        question="Which chunks hold this kind of knowledge?",
        min_length=1,
    )
    rationale: str = doc_field(
        description="Why no existing entity fits, in one or two sentences naming the closest entity and what it lacks, e.g. 'Monitoring covers alerts, not risks.'",
        question="Why does no existing entity fit?",
        min_length=10,
    )
    source_path: str = doc_field(
        default="",
        description="Bundle path of the original the proposal came from, set by code, e.g. 'Acme/references/srs.pdf'.",
        question="Which original did the proposal come from?",
        scored=False,
    )
    proposed_by: str = doc_field(
        default="",
        description="The actor that proposed it, set by code, '<producer>/<version>', e.g. 'okf-type-proposal-agent/gemma4:31b'.",
        question="Who proposed it?",
        scored=False,
    )
