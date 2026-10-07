"""Manual trigger for generation: `python -m docfactory.generate <App> <Overview|SMTD|SRS|SOP|all> [--no-llm]`.

For each document type: build the body from the stored facts, maintain document control and revision history, save the needs list and
render output/<App>/<DocType>.md and <DocType>.missing.md. One small checked LLM call (NeedsWriter, settings from .env) phrases the needs
list when the gaps changed; --no-llm saves one need per gap instead.
"""
import argparse
import sys

from docfactory import db
from docfactory.agents.model_client_factory import default_client
from docfactory.agents.needs_writer import NeedsWriter
from docfactory.env_file import load_env_file
from docfactory.generation.doc_types import DOC_TYPES
from docfactory.generation.generate_document import format_reports, generate


def _apps() -> list[str]:
    return sorted({row["AppID"] for row in db.list_rows("KnowledgeFacts") if row["AppID"]})


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m docfactory.generate")
    parser.add_argument("app", help="the application, as its fact key scope, e.g. AI-Driven-Job-Matching-Platform")
    parser.add_argument("doc_type", choices=[*DOC_TYPES, "all"], help="the document type, or all")
    parser.add_argument("--no-llm", action="store_true", help="save one need per gap instead of asking the LLM to phrase the needs list")
    args = parser.parse_args(argv)
    if args.app not in _apps():
        print(f"{args.app!r} has no knowledge facts; applications with facts: {', '.join(_apps()) or 'none'}")
        return 1
    writer = None
    if not args.no_llm:
        load_env_file()  # settings from .env; variables already set in the shell win
        writer = NeedsWriter(default_client())
    doc_types = list(DOC_TYPES) if args.doc_type == "all" else [args.doc_type]
    reports = [generate(args.app, doc_type, writer) for doc_type in doc_types]
    print(format_reports(args.app, reports))
    return 1 if any(r.errors for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
