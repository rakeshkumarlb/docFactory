from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.extract.batching import batch_text
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.type_proposal import TypeProposal
from docfactory.ontology.ontology_render import ontology_summary
from docfactory.project_root import PROJECT_ROOT
from docfactory.tools.proposal_tools import proposal_package

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-type-proposal-agent.md"
ACTOR_PREFIX = "okf-type-proposal-agent"
MAX_TURNS = 6


class TypeProposer:
    """The LLM step that proposes new entity types: one small call per batch of chunks that are in no fact, each a fresh AgentLoop with exactly one tool (submit_type_proposal).

    A call sees the ontology summary and one batch of chunks and returns zero or more proposals; storing them is the pipeline's job and creating the
    model from one is a separate developer step. A call that fails, or ends without an accepted answer, returns nothing.
    """

    def __init__(self, client: ModelClient, system: str | None = None) -> None:
        self.client = client
        self.actor = f"{ACTOR_PREFIX}/{getattr(client, 'model', 'unknown')}"  # set by code, never by the model
        self.system = system if system is not None else load_prompt(PROMPT_FILE)

    def propose_batch(self, source_path: str, batch: list[DocChunk], focus: str | None = None) -> tuple[list[TypeProposal] | None, str]:
        """(proposals, '') for one batch (possibly none), or (None, what went wrong). `focus` names a kind of thing recognition found that no
        entity type covers (with examples); the call then drafts that kind, or proposes nothing when it fits an existing entity."""
        text = batch_text(batch)
        accepted: list[list[TypeProposal]] = []
        message = f"Knowledge entities the system already stores:\n{ontology_summary()}\n\nDocument: {source_path}\n\n"
        if focus:
            message += f"Recognition found things of a kind no entity type covers:\n{focus}\nPropose that kind (with items) if it is worth keeping, else nothing.\n\n"
        message += f"Chunks none of them claimed:\n\n{text}"
        try:
            AgentLoop(self.client, proposal_package({c.chunk_no for c in batch}, accepted), self.system, message, MAX_TURNS, "type proposer").run()
        except Exception as error:  # one failed batch never stops the others
            return (accepted[-1], "") if accepted else (None, str(error))
        return (accepted[-1], "") if accepted else (None, "the model ended without an accepted submit_type_proposal call")
