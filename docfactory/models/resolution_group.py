from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ResolutionGroup(DocFactoryModel):
    """One decision of entity resolution: entities of one type that are the same thing under different names (e.g. 'AI Engine' and 'AI-Driven Matching Engine' are 'Matching Engine'). The merge folds them into the kept entity."""

    keep: str = doc_field(
        description="Entity id of the entity that stays, normally the one with the clearest canonical name, e.g. 'Component/matching-engine'.",
        question="Which entity stays?",
        min_length=1,
    )
    same: list[str] = doc_field(
        default_factory=list,
        description="Entity ids of the other entities that are the same thing and are folded into the kept one, e.g. ['Component/ai-engine'].",
        question="Which entities are the same thing?",
    )
    reason: str = doc_field(
        default='',
        description="Why they are the same, from their names and summaries, e.g. 'Both are the matching component; the SRS calls it AI Engine.'.",
        question="Why are they the same thing?",
    )
