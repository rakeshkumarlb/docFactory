from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.entitymodels.facts.note import Note
from docfactory.extract.batching import batch_text
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.note_draft import NoteDraft
from docfactory.ontology.ontology_render import ontology_summary
from docfactory.project_root import PROJECT_ROOT
from docfactory.tools.discovery_tools import discovery_package

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-discovery-agent.md"
ACTOR_PREFIX = "okf-discovery-agent"
MAX_TURNS = 6


class Discoverer:
    """The LLM step of discovery: one small call per batch of chunks that no entity claims, each a fresh AgentLoop with exactly one tool (submit_discovery).

    A call sees the ontology summary and one batch of chunks, never the whole document, and returns notes plus the chunks that hold nothing;
    merging, storing and saving are the pipeline's job. A call that fails, or ends without an accepted answer, returns nothing.
    """

    def __init__(self, client: ModelClient, system: str | None = None) -> None:
        self.client = client
        self.actor = f"{ACTOR_PREFIX}/{getattr(client, 'model', 'unknown')}"  # set by code, never by the model
        self.system = system if system is not None else load_prompt(PROMPT_FILE)

    def discover_batch(self, source_path: str, batch: list[DocChunk]) -> tuple[tuple[list[NoteDraft], list[int]] | None, str]:
        """((notes, chunks with nothing to keep), '') for one batch, or (None, what went wrong)."""
        text = batch_text(batch)
        accepted: list[tuple[list[NoteDraft], list[int]]] = []
        message = (f"Knowledge entities the system stores (none of them claimed these chunks):\n{ontology_summary()}\n\n"
                   f"Notes: {(Note.__doc__ or '').strip()}\nDocument: {source_path}\n\nChunks:\n\n{text}")
        try:
            AgentLoop(self.client, discovery_package({c.chunk_no for c in batch}, text, accepted), self.system, message, MAX_TURNS, "discoverer").run()
        except Exception as error:  # one failed batch never stops the others
            return (accepted[-1], "") if accepted else (None, str(error))
        return (accepted[-1], "") if accepted else (None, "the model ended without an accepted submit_discovery call")
