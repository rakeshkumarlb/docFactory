from pydantic import BaseModel

from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.models.entity_record import EntityRecord
from docfactory.project_root import PROJECT_ROOT
from docfactory.tools.extraction_tools import extraction_package

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-entity-item-extractor-agent.md"
ACTOR_PREFIX = "okf-entity-extraction-agent"
MAX_TURNS = 6


class EntityItemExtractor:
    """The LLM step of entity-centric extraction: one small call per recognized entity, a fresh AgentLoop with exactly one tool (submit_extraction).

    A call sees the entity (type, name, aliases, the item model's meaning) and its evidence text (its own chunks in every original, then its
    neighbours' chunks), and returns the item's fields as a partial object without the fields code sets (`exclude`: identity, evidence,
    relations). Storing and merging are the pipeline's job. A call that fails, or ends without an accepted answer, returns nothing.
    """

    def __init__(self, client: ModelClient, system: str | None = None) -> None:
        self.client = client
        self.actor = f"{ACTOR_PREFIX}/{getattr(client, 'model', 'unknown')}"  # set by code, never by the model
        self.system = system if system is not None else load_prompt(PROMPT_FILE)

    def extract_item(self, item_model: type[BaseModel], entity: EntityRecord, text: str, exclude: frozenset[str]) -> tuple[dict | None, str | None, str]:
        """(stated fields, summary, '') for one entity, or (None, None, what went wrong)."""
        accepted: list[tuple[dict, str | None]] = []
        doc = " ".join((item_model.__doc__ or "").split())
        aka = f" (also: {', '.join(entity.aliases)})" if entity.aliases else ""
        message = (f"Item type: {item_model.__name__}: {doc}\nItem: {entity.name}{aka}\n"
                   f"What it is: {entity.summary or 'not summarised'}\n\nChunks:\n\n{text}")
        try:
            AgentLoop(self.client, extraction_package(item_model, text, accepted, exclude), self.system, message, MAX_TURNS,
                      f"{item_model.__name__} item extractor").run()
        except Exception as error:  # one failed entity never stops the others
            if not accepted:
                return None, None, str(error)
        if not accepted:
            return None, None, "the model ended without an accepted submit_extraction call"
        return *accepted[-1], ""
