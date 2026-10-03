"""Manual trigger for ingestion: `python -m docfactory.agents.run_ingestion [--no-llm]`.

Moves every file from incoming/ to staging/, chunks and tags it against the ontology, decides its scope and stores it in DocStore/
with its chunks (docfactory/ingest/pipeline.py). Chunks the rules cannot tag and scopes they cannot decide go to the LLM fallback
(settings from .env, see .env.example); `--no-llm` runs the rules only. Files that still need a decision stay in staging/.
"""
import sys

from docfactory.agents.ingestion_fallback import IngestionFallback
from docfactory.agents.model_client_factory import default_client
from docfactory.env_file import load_env_file
from docfactory.ingest.pipeline import format_reports, run_ingest


def main(argv: list[str] | None = None) -> int:
    argv = argv or []
    if any(arg != "--no-llm" for arg in argv):
        print("usage: python -m docfactory.agents.run_ingestion [--no-llm]")
        return 2
    load_env_file()  # settings from .env; variables already set in the shell win
    fallback = None if "--no-llm" in argv else IngestionFallback(default_client())
    print(format_reports(run_ingest(fallback=fallback)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
