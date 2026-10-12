from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.graph_edge import GraphEdge
from docfactory.models.graph_node import GraphNode


class RelationshipGraph(DocFactoryModel):
    """The relationship graph of one scope (an application or Shared): its concepts as nodes and the typed edges between them, derived from the bundle's files on every run. The graph is a view; the JSON of the facts stays the truth."""

    scope: str = doc_field(
        description="The scope folder the graph covers, e.g. 'AI-Driven-Job-Matching-Platform' or 'Shared'.",
        question="Which scope does the graph cover?",
        min_length=1,
    )
    nodes: list[GraphNode] = doc_field(
        default_factory=list,
        description="The concepts of the scope, ordered by id.",
        question="Which concepts are in the graph?",
    )
    edges: list[GraphEdge] = doc_field(
        default_factory=list,
        description="The relationships, ordered by source, kind and target.",
        question="Which relationships are in the graph?",
    )
