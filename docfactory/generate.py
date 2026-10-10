"""Manual trigger for generation: `python -m docfactory.generate <App> <DocType|all> [--no-llm]`.

The document is defined by a YAML template (generation/templates/<DocType>.yaml), stored
in DocumentOutputs and rendered to output/<App>/<DocType>.md and <DocType>.missing.md. The needs list is phrased by the
same small checked LLM call; --no-llm saves one need per gap instead.
"""
import argparse
import sys

from docfactory import db
from docfactory.agents.model_client_factory import default_client
from docfactory.agents.needs_writer import NeedsWriter
from docfactory.generation.generate_document import generate_document
from docfactory.generation.template_error import TemplateError
from docfactory.generation.template_loader import list_doc_types
from docfactory.env_file import load_env_file
from docfactory.generation.generation_steps import format_reports


def _apps() -> list[str]:
    return sorted({row["AppID"] for row in db.list_rows("KnowledgeFacts") if row["AppID"]})


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m docfactory.generate")
    parser.add_argument("app", help="the application, as its fact key scope, e.g. AI-Driven-Job-Matching-Platform")
    parser.add_argument("doc_type", help=f"the document type ({', '.join(list_doc_types())}), or all")
    parser.add_argument("--no-llm", action="store_true", help="save one need per gap instead of asking the LLM to phrase the needs list")
    args = parser.parse_args(argv)
    if args.app not in _apps():
        print(f"{args.app!r} has no knowledge facts; applications with facts: {', '.join(_apps()) or 'none'}")
        return 1
    writer = None
    if not args.no_llm:
        load_env_file()  # settings from .env; variables already set in the shell win
        writer = NeedsWriter(default_client())
    doc_types = list_doc_types() if args.doc_type == "all" else [args.doc_type]
    try:
        reports = [generate_document(args.app, doc_type, writer) for doc_type in doc_types]
    except TemplateError as error:
        print(f"template error: {error}")
        return 1
    print(format_reports(args.app, reports))
    return 1 if any(r.errors for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
