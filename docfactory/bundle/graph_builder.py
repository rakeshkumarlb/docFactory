import json
import re

from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.fact_registry import FACT_SPECS
from docfactory.bundle.item_file_render import source_link
from docfactory.bundle.item_layout import split_fields
from docfactory.bundle.paths import fact_relpath
from docfactory.extract.grounding import normal_identity
from docfactory.models.graph_edge import GraphEdge
from docfactory.models.graph_node import GraphNode
from docfactory.models.relationship_graph import RelationshipGraph
from docfactory.okf_frontmatter import type_name

MIN_MENTION = 3  # an identifier shorter than this is never searched for in other items' text


def _strings(value) -> list[str]:
    """Every string inside a JSON value, depth first."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    return []


class GraphBuilder:
    """Builds the relationship graph of one scope from the bundle's concept files. Deterministic, read-only, no LLM.

    Three kinds of edge: structural ones from the layout (item part_of its fact, fact derived_from its Source), mentioned ones where an item's own
    text names another item's identifier (only identifiers with a digit, such as FR-12, so common words never link), and stated ones from the
    `relations` the extraction took from the documents. A stated or mentioned target that is not stored is kept as a broken link, which OKF allows.
    """

    def __init__(self, store: BundleStore | None = None) -> None:
        self.store = store or BundleStore()

    def scopes(self) -> list[str]:
        """The scopes that hold facts, ordered by name."""
        return sorted({(fact.app_id or "Shared") for fact in self.store.list_facts()})

    def build(self, scope: str) -> RelationshipGraph:
        """The graph of `scope` (an application name or 'Shared')."""
        facts = [f for f in self.store.list_facts() if (f.app_id or "Shared") == scope]
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []
        items = []  # (node id, identifier, parsed value)
        for fact in facts:
            fact_id = "/" + fact_relpath(fact.key)
            nodes[fact_id] = GraphNode(id=fact_id, type=fact.type or "Fact", title=fact.title or fact.key)
            for source in fact.sources:
                target = source_link(source.resource)
                if target:
                    nodes.setdefault(target, GraphNode(id=target, type="Source", title=source.title or source.resource))
                    edges.append(GraphEdge(source=fact_id, target=target, kind="derived_from", origin="structural"))
            for item in self.store.list_items(fact.key):
                item_id = "/" + item.relpath
                nodes[item_id] = GraphNode(id=item_id, type=type_name(self._item_type(fact.key, item.field)), title=item.item_id, identifier=item.item_id)
                edges.append(GraphEdge(source=item_id, target=fact_id, kind="part_of", origin="structural"))
                items.append((item_id, item.item_id, json.loads(item.value)))
        edges += self._text_edges(items, nodes)
        return RelationshipGraph(scope=scope, nodes=sorted(nodes.values(), key=lambda n: n.id),
                                 edges=sorted(edges, key=lambda e: (e.source, e.origin, e.kind, e.target)))

    @staticmethod
    def _item_type(key: str, field: str) -> str:
        return split_fields(FACT_SPECS[key.rsplit(".", 1)[-1]]["model"])[field].__name__

    @staticmethod
    def _text_edges(items: list, nodes: dict[str, GraphNode]) -> list[GraphEdge]:
        """The mentioned and stated edges among `items` (node id, identifier, value)."""
        by_identity: dict[str, str] = {}
        for node_id, identifier, _ in sorted(items):
            by_identity.setdefault(normal_identity(identifier), node_id)
        mentionable = sorted((i for i in by_identity if len(i) >= MIN_MENTION and any(c.isdigit() for c in i)), key=len, reverse=True)
        pattern = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(i) for i in mentionable) + r")(?![A-Za-z0-9])", re.IGNORECASE) if mentionable else None
        edges = []
        for node_id, identifier, value in items:
            stated = {normal_identity(r["target"]): r for r in value.get("relations", [])}
            own = normal_identity(identifier)
            for relation in stated.values():
                target = by_identity.get(normal_identity(relation["target"]))
                edges.append(GraphEdge(source=node_id, target=target or relation["target"], kind=relation["kind"], origin="stated",
                                       evidence=relation.get("evidence", ""), resolved=target is not None))
            if pattern is None:
                continue
            text = " ".join(s for k, v in value.items() if k != "relations" for s in _strings(v))
            for found in sorted({normal_identity(m) for m in pattern.findall(text)} - {own} - set(stated)):
                edges.append(GraphEdge(source=node_id, target=by_identity[found], kind="references", origin="mentioned"))
        return edges
