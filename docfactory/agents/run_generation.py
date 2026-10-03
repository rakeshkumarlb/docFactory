"""Manual trigger for the document-generator agent: `python -m docfactory.agents.run_generation <App> <DocType>`.

DocType is Overview, SMTD, SRS or SOP. The frontmatter index is brought up to date first (needs DOCFACTORY_EMBED_MODEL on the Ollama host),
then the agent searches the knowledge, reads the files it needs and saves the document body. If the document's DocumentControl and
RevisionHistory rows exist (they are supplied by the caller), the document is rendered to output/<App>/<DocType>.md.
"""
import sys

from docfactory import db, documents
from docfactory.agents.generator_agent import GeneratorAgent
from docfactory.agents.model_client_factory import default_client
from docfactory.db import PROJECT_ROOT
from docfactory.env_file import load_env_file
from docfactory.render import RenderError, render_markdown
from docfactory.retrieval.embedder_factory import default_embedder
from docfactory.retrieval.sqlite_vector_index import SqliteVectorIndex

DOC_TYPES = ("Overview", "SMTD", "SRS", "SOP")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in DOC_TYPES:
        print(f"usage: python -m docfactory.agents.run_generation <App> <{'|'.join(DOC_TYPES)}>")
        return 2
    app_id, doc_type = argv
    if not db.list_rows("KnowledgeFacts", app_id):
        print(f"no facts stored for application {app_id!r}; extract knowledge first")
        return 1
    load_env_file()  # settings from .env; variables already set in the shell win
    index = SqliteVectorIndex(default_embedder())
    embedded, removed = index.rebuild()
    print(f"index: {embedded} embedded, {removed} removed")
    print(GeneratorAgent(default_client(), index).run(app_id, doc_type))
    key = f"{app_id}.Outputs.{doc_type}"
    record = documents.get_document(key)
    if record is None:
        print(f"the agent saved no document under {key}")
        return 1
    print(f"saved {key}: version {record.version}, completeness {record.completeness:g}")
    try:
        text = render_markdown(app_id, doc_type)
    except RenderError as error:
        print(f"not rendered: {error}")
        return 0
    target = PROJECT_ROOT / "output" / app_id / f"{doc_type}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
