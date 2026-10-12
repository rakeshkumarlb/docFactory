"""Manual trigger for the relationship graph: `python -m docfactory.agents.run_graph [<scope> ...]`.

Builds the relationship graph of each scope (an application folder or Shared; all scopes without an argument) from the concept files of the
bundle, writes it as the concept `<scope>/graph/relationships.md` and prints a one-line summary per scope. Deterministic, no LLM.
"""
import sys

from docfactory.bundle.graph_builder import GraphBuilder
from docfactory.bundle.graph_queries import summary
from docfactory.bundle.graph_store import GraphStore


def write_graphs(scopes: list[str] | None = None) -> list[str]:
    """Build and store the graph of each scope in `scopes` (all scopes when None) and return one summary line per scope."""
    builder, store = GraphBuilder(), GraphStore()
    lines = []
    for scope in scopes or builder.scopes():
        graph = builder.build(scope)
        store.write(graph)
        lines.append(summary(graph))
    return lines


def main(argv: list[str]) -> int:
    lines = write_graphs(argv or None)
    print("\n".join(lines) if lines else "no facts in the bundle: no graph to build")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
