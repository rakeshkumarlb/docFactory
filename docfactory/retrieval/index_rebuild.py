"""Rebuild the vector index of the facts (metadata + JSON value) from the database: `python -m docfactory.retrieval.index_rebuild`."""
import sys

from docfactory.env_file import load_env_file
from docfactory.retrieval.embedder_factory import default_embedder
from docfactory.retrieval.sqlite_vector_index import SqliteVectorIndex


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    embedded, removed = SqliteVectorIndex(default_embedder()).rebuild()
    print(f"index rebuilt: {embedded} fact(s) embedded, {removed} removed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
