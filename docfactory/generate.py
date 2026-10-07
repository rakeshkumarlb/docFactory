"""Manual trigger for generation: `python -m docfactory.generate <App> <Overview|SMTD|SRS|SOP|all> [--no-llm]`.

For each document type: build the body from the stored facts, maintain document control and revision history, save the needs list and
render output/<App>/<DocType>.md and <DocType>.missing.md. --no-llm saves one need per gap instead of the LLM's needs list.
"""
import argparse
import sys

from docfactory import db
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
        print("the needs-list LLM call is not built yet (Phase 4 step 4); run with --no-llm")
        return 2
    doc_types = list(DOC_TYPES) if args.doc_type == "all" else [args.doc_type]
    reports = [generate(args.app, doc_type, writer) for doc_type in doc_types]
    print(format_reports(args.app, reports))
    return 1 if any(r.errors for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
