"""Manual trigger for ingestion: `python -m docfactory.agents.run_ingestion`.

Moves every file from incoming/ to staging/, chunks and tags it against the ontology, decides its scope and stores it in DocStore/
with its chunks (docfactory/ingest/pipeline.py). Files that need a decision stay in staging/ with the reason. No LLM is used yet.
"""
import sys

from docfactory.env_file import load_env_file
from docfactory.ingest.pipeline import format_reports, run_ingest


def main(argv: list[str] | None = None) -> int:
    load_env_file()  # settings from .env; variables already set in the shell win
    print(format_reports(run_ingest()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
