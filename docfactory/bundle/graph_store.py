import hashlib
from pathlib import Path

from docfactory import clock
from docfactory.bundle.file_io import put_text
from docfactory.bundle.graph_queries import broken_links, semantic_edges, summary, unlinked
from docfactory.bundle.paths import GRAPH_DIR, SUFFIX, bundle_root, is_safe_segment
from docfactory.models.relationship_graph import RelationshipGraph

GRAPH_FILE = "relationships" + SUFFIX
MAX_DIAGRAM_EDGES = 80
GENERATED_BY = "docfactory/graph"


def graph_relpath(scope: str) -> str:
    """The bundle-relative path of a scope's graph concept: 'Acme' -> 'Acme/graph/relationships.md'. ValueError for an unsafe scope name."""
    if not is_safe_segment(scope):
        raise ValueError(f"scope {scope!r} cannot be used as a folder name")
    return f"{scope}/{GRAPH_DIR}/{GRAPH_FILE}"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _label(graph: RelationshipGraph) -> dict[str, str]:
    return {n.id: n.title for n in graph.nodes}


def graph_body(graph: RelationshipGraph) -> str:
    """The Markdown body of the graph concept: summary, the relationships the text gave, broken links and a diagram of them. Same graph, same bytes."""
    label = _label(graph)
    shown = semantic_edges(graph)
    lines = [f"# Summary", "", summary(graph), ""]
    lines += ["# Relationships", ""]
    if shown:
        lines += ["| From | Relationship | To | Found by | Evidence |", "|---|---|---|---|---|"]
        for e in shown:
            to = f"[{label.get(e.target, e.target)}]({e.target.replace(' ', '%20')})" if e.resolved else f"{e.target} (not stored)"
            lines.append(f"| [{label.get(e.source, e.source)}]({e.source.replace(' ', '%20')}) | {e.kind} | {to} | {e.origin} | {_cell(e.evidence)} |")
    else:
        lines.append("No item names or states a relationship to another item yet.")
    lines += ["", "# Broken links", ""]
    lines += [f"* {label.get(e.source, e.source)} {e.kind} {e.target}" for e in broken_links(graph)] or ["None."]
    lines += ["", "# Items with no relationship in the text", ""]
    loose = unlinked(graph)
    lines += [f"{len(loose)} of {sum(1 for n in graph.nodes if n.identifier)} items."] if loose else ["None."]
    drawn = [e for e in shown if e.resolved][:MAX_DIAGRAM_EDGES]
    lines += ["", "# Diagram", ""]
    if drawn:
        names = {}
        for e in drawn:
            for node_id in (e.source, e.target):
                names.setdefault(node_id, f"n{len(names) + 1}")
        lines += ["```mermaid", "graph LR"]
        lines += [f'  {name}["{label.get(node_id, node_id).replace(chr(34), chr(39))}"]' for node_id, name in names.items()]
        lines += [f"  {names[e.source]} -->|{e.kind}| {names[e.target]}" for e in drawn]
        lines += ["```"]
        if len([e for e in shown if e.resolved]) > len(drawn):
            lines += ["", f"The diagram shows the first {MAX_DIAGRAM_EDGES} relationships; the table above lists all."]
    else:
        lines.append("Nothing to draw.")
    return "\n".join(lines) + "\n"


class GraphStore:
    """The only writer of the generated relationship graph concepts (`<scope>/graph/relationships.md`, OKF type `Relationship Graph`).

    The file is a derived view: it is rewritten from a graph on every run and never edited by hand. It is left untouched (timestamp included)
    when the body is unchanged.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else bundle_root()

    def write(self, graph: RelationshipGraph) -> bool:
        """Write the graph concept of `graph.scope`. True when the file changed."""
        body = graph_body(graph)
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        path = self.root / graph_relpath(graph.scope)
        if path.is_file() and f'hashcode: "{digest}"' in path.read_text(encoding="utf-8").split("\n---\n", 1)[0]:
            return False
        head = (f'type: "Relationship Graph"\ntitle: "{graph.scope} relationship graph"\n'
                f'description: "How the concepts of {graph.scope} relate to each other: structure, mentions and stated relations."\n'
                f'generated: {{ by: "{GENERATED_BY}", at: {clock.now_iso()} }}\nstatus: stable\nhashcode: "{digest}"\n')
        return put_text(path, f"---\n{head}---\n\n{body}")
