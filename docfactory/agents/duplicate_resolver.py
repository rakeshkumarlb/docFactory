from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.models.entity_record import EntityRecord
from docfactory.models.resolution_group import ResolutionGroup
from docfactory.project_root import PROJECT_ROOT
from docfactory.tools.resolution_tools import resolution_package

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-duplicate-resolver-agent.md"
ACTOR_PREFIX = "okf-resolution-agent"
MAX_TURNS = 6


class DuplicateResolver:
    """The LLM step of entity resolution: one small call per entity type of a scope, a fresh AgentLoop with exactly one tool (submit_merges).

    A call sees every entity of one type (id, name, aliases, summary) and returns the groups that are the same thing; storing the decisions
    and applying them in the merge are code's job. A call that fails, or ends without an accepted answer, returns nothing.
    """

    def __init__(self, client: ModelClient, system: str | None = None) -> None:
        self.client = client
        self.actor = f"{ACTOR_PREFIX}/{getattr(client, 'model', 'unknown')}"  # set by code, never by the model
        self.system = system if system is not None else load_prompt(PROMPT_FILE)

    def resolve_type(self, scope: str, type_name: str, entities: list[EntityRecord]) -> tuple[list[ResolutionGroup] | None, str]:
        """(the groups of duplicates among `entities`, possibly none, '') or (None, what went wrong)."""
        accepted: list[list[ResolutionGroup]] = []
        lines = "\n".join(f"{e.entity_id} | {e.name}" + (f" | aka {', '.join(e.aliases)}" if e.aliases else "") + (f" | {e.summary}" if e.summary else "")
                          for e in entities)
        message = f"Application: {scope}\nEntity type: {type_name}\n\nEntities:\n{lines}"
        try:
            AgentLoop(self.client, resolution_package({e.entity_id for e in entities}, accepted), self.system, message, MAX_TURNS,
                      f"{type_name} resolver").run()
        except Exception as error:  # one failed type never stops the others
            if not accepted:
                return None, str(error)
        if not accepted:
            return None, "the model ended without an accepted submit_merges call"
        return accepted[-1], ""
