"""Questions to ask a relationship graph. Pure functions over a RelationshipGraph, deterministic, nothing is written."""
from docfactory.models.graph_edge import GraphEdge
from docfactory.models.graph_node import GraphNode
from docfactory.models.relationship_graph import RelationshipGraph

STRUCTURAL = "structural"


def outgoing(graph: RelationshipGraph, node_id: str) -> list[GraphEdge]:
    """The edges that start at `node_id`."""
    return [e for e in graph.edges if e.source == node_id]


def backlinks(graph: RelationshipGraph, node_id: str) -> list[GraphEdge]:
    """The edges that point to `node_id`."""
    return [e for e in graph.edges if e.target == node_id]


def neighbours(graph: RelationshipGraph, node_id: str) -> list[str]:
    """The ids of the nodes directly connected to `node_id` in either direction, sorted."""
    return sorted({e.target for e in outgoing(graph, node_id) if e.resolved} | {e.source for e in backlinks(graph, node_id)})


def semantic_edges(graph: RelationshipGraph) -> list[GraphEdge]:
    """The edges the text gave (mentioned and stated), not the structural ones."""
    return [e for e in graph.edges if e.origin != STRUCTURAL]


def broken_links(graph: RelationshipGraph) -> list[GraphEdge]:
    """The edges whose target is not stored in the bundle."""
    return [e for e in graph.edges if not e.resolved]


def unlinked(graph: RelationshipGraph) -> list[GraphNode]:
    """The items (nodes with an identifier) that no mentioned or stated edge touches, in either direction."""
    touched = {e.source for e in semantic_edges(graph)} | {e.target for e in semantic_edges(graph)}
    return [n for n in graph.nodes if n.identifier and n.id not in touched]


def summary(graph: RelationshipGraph) -> str:
    """One line: counts of nodes, edges by origin, broken links and unlinked items."""
    count = {origin: sum(e.origin == origin for e in graph.edges) for origin in (STRUCTURAL, "mentioned", "stated")}
    return (f"{graph.scope}: {len(graph.nodes)} concepts, {len(graph.edges)} relationships ({count[STRUCTURAL]} structural, {count['mentioned']} mentioned, "
            f"{count['stated']} stated), {len(broken_links(graph))} broken links, {len(unlinked(graph))} items with no relationship in the text")
