from pydantic import BaseModel

from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.db import PROJECT_ROOT
from docfactory.extract.batching import batch_text
from docfactory.models.doc_chunk import DocChunk
from docfactory.tools.extraction_tools import extraction_package

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-entity-extractor-agent.md"
ACTOR_PREFIX = "okf-extraction-agent"
MAX_TURNS = 6


class EntityExtractor:
    """The LLM step of extraction: one small call per batch, each a fresh AgentLoop with exactly one tool (submit_extraction).

    A call sees the entity's meaning and one batch of its chunks, never the whole document, and returns a partial object; merging,
    storing and saving are the pipeline's job. A call that fails, or ends without an accepted answer, returns nothing.
    """

    def __init__(self, client: ModelClient, system: str | None = None) -> None:
        self.client = client
        self.actor = f"{ACTOR_PREFIX}/{getattr(client, 'model', 'unknown')}"  # set by code, never by the model
        self.system = system if system is not None else load_prompt(PROMPT_FILE)

    def extract_batch(self, entity_model: type[BaseModel], docstore_path: str, batch: list[DocChunk]) -> tuple[dict | None, str | None, str]:
        """(stated fields, summary, '') for one batch, or (None, None, what went wrong)."""
        text = batch_text(batch)
        accepted: list[tuple[dict, str | None]] = []
        doc = (entity_model.__doc__ or "").strip()
        message = (f"Entity: {entity_model.__name__}: {doc}\nDocument: {docstore_path}\n\n"
                   f"Chunks:\n\n{text}")
        try:
            AgentLoop(self.client, extraction_package(entity_model, text, accepted), self.system, message, MAX_TURNS,
                      f"{entity_model.__name__} extractor").run()
        except Exception as error:  # one failed batch never stops the others
            if accepted:  # the answer was accepted; only the closing reply failed
                return *accepted[-1], ""
            return None, None, str(error)
        if not accepted:
            return None, None, "the model ended without an accepted submit_extraction call"
        return *accepted[-1], ""
