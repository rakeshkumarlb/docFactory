from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.extract.batching import batch_text
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.entity_record import EntityRecord
from docfactory.models.window_recognition import WindowRecognition
from docfactory.project_root import PROJECT_ROOT
from docfactory.recognize.catalog_filter import catalog_text
from docfactory.recognize.type_vocabulary import vocabulary_text
from docfactory.recognize.windows import window_hash
from docfactory.tools.recognition_tools import recognition_package

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-entity-recognizer-agent.md"
ACTOR_PREFIX = "okf-recognition-agent"
MAX_TURNS = 6


class EntityRecognizer:
    """The LLM step of recognition: one small call per window of a document, each a fresh AgentLoop with exactly one tool (submit_recognition).

    A call sees the document's outline, one window of its chunks, the type vocabulary, the part of the entity graph the window may refer to
    and the keyword-rule hints, and returns the window's entities, relationships and chunk topics; storing and merging are the pipeline's job.
    A call that fails, or ends without an accepted answer, returns nothing.
    """

    def __init__(self, client: ModelClient, system: str | None = None) -> None:
        self.client = client
        self.actor = f"{ACTOR_PREFIX}/{getattr(client, 'model', 'unknown')}"  # set by code, never by the model
        self.system = system if system is not None else load_prompt(PROMPT_FILE)

    def recognize_window(self, source_path: str, outline: str, window: list[DocChunk], catalog: list[EntityRecord],
                         hints: list[str]) -> tuple[WindowRecognition | None, str]:
        """(the accepted recognition of the window, '') or (None, what went wrong)."""
        text = batch_text(window)
        chunk_nos = [c.chunk_no for c in window]
        accepted: list = []
        message = (f"Document: {source_path}\n\nOutline:\n{outline}\n\nEntity types:\n{vocabulary_text()}\n\n"
                   f"Catalog (entities already known: id | type | name | aliases):\n{catalog_text(catalog)}\n\n"
                   f"Keyword-rule hints (may be wrong): {'; '.join(hints) if hints else 'none'}\n\nChunks:\n\n{text}")
        try:
            AgentLoop(self.client, recognition_package(text, chunk_nos, catalog, accepted), self.system, message, MAX_TURNS,
                      "entity recognizer").run()
        except Exception as error:  # one failed window never stops the others
            if not accepted:
                return None, str(error)
        if not accepted:
            return None, "the model ended without an accepted submit_recognition call"
        entities, relations, topics = accepted[-1]
        return WindowRecognition(window_hash=window_hash(window), chunk_nos=chunk_nos, entities=entities, relations=relations, topics=topics), ""
