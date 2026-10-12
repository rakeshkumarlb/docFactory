"""Manual trigger for the coverage report: `python -m docfactory.agents.run_coverage ["<bundle path>" ...]`.

Without a path every ingested original of the bundle is reported. For each chunk it says whether its content is in a fact or was lost on
the way (unmapped, skipped by scope, not extracted yet), then one line per scope on its relationship graph. Read-only, deterministic, no LLM, writes nothing.
"""
import sys

from docfactory.bundle.graph_builder import GraphBuilder
from docfactory.bundle.graph_queries import summary
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.coverage import all_coverage, file_coverage, format_coverage


def print_graphs(scopes: list[str]) -> None:
    """One line per scope on its relationship graph: relationships found, broken links and items no relationship touches."""
    builder = GraphBuilder()
    for scope in scopes:
        if scope in builder.scopes():
            print("  graph " + summary(builder.build(scope)))


def main(argv: list[str]) -> int:
    if not argv:
        reports = all_coverage()
        print(format_coverage(reports))
        print_graphs(sorted({r.path.split("/")[0] for r in reports}))
        return 0
    store = SourceStore()
    reports = []
    for path in argv:
        normal = path.replace("\\", "/").strip("/")
        if store.read(normal) is None:
            print(f"{normal!r} is not an ingested original; ingested files:")
            for record in store.list():
                print(f"  {record.path}")
            return 1
        reports.append(file_coverage(normal))
    print(format_coverage(reports))
    print_graphs(sorted({r.path.split("/")[0] for r in reports}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
