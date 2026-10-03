from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.db import PROJECT_ROOT
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.chunk_tag_proposal import ChunkTagProposal
from docfactory.models.doc_chunk import DocChunk
from docfactory.ontology.ontology_render import ontology_summary
from docfactory.ontology.signals import entity_names
from docfactory.tools.ingestion_tools import scope_package, tagging_package

TAGGER_PROMPT = PROJECT_ROOT / ".claude" / "agents" / "docfactory-chunk-tagger-agent.md"
SCOPE_PROMPT = PROJECT_ROOT / ".claude" / "agents" / "docfactory-scope-agent.md"
EXCERPT_CHARS = 300
SCOPE_TEXT_CHARS = 2000
MAX_TURNS = 6


class IngestionFallback:
    """The LLM fallback of ingestion: two small calls, each a fresh AgentLoop with exactly one tool.

    `tag_chunks` tags the chunks the rules left unmapped; `decide_scope` places a file the rules could not place. Both send only what
    the decision needs (the compact ontology plus headings and short excerpts, or the first chunks), never the whole document. A call
    that fails, or ends without an accepted answer, returns nothing: the chunks stay unmapped / the file stays in staging.
    """

    def __init__(self, client: ModelClient) -> None:
        self.client = client
        self.origin = f"llm/{getattr(client, 'model', 'unknown')}"

    def tag_chunks(self, chunks: list[DocChunk]) -> tuple[list[ChunkTag], str]:
        """(tags for `chunks`, a note on what happened). Chunks the model says inform no entity get no tag."""
        if not chunks:
            return [], ""
        accepted: list[list[ChunkTagProposal]] = []
        package = tagging_package({c.chunk_no for c in chunks}, entity_names(), accepted)
        excerpts = "\n\n".join(f"[chunk {c.chunk_no}] {c.heading}\n{c.text[:EXCERPT_CHARS]}" for c in chunks)
        message = f"Entities:\n{ontology_summary()}\n\nChunks to tag:\n\n{excerpts}"
        try:
            AgentLoop(self.client, package, load_prompt(TAGGER_PROMPT), message, MAX_TURNS, "chunk tagger").run()
        except Exception as error:  # the fallback never breaks ingestion
            return [], f"tag fallback failed: {error}"
        if not accepted:
            return [], "tag fallback gave no answer"
        tags = [ChunkTag(chunk_no=p.chunk_no, entity=e, origin=self.origin, score=0, evidence=p.reason)
                for p in accepted[-1] for e in dict.fromkeys(p.entities)]
        return tags, ""

    def decide_scope(self, chunks: list[DocChunk], tags: list[ChunkTag], existing: list[str], rule_reason: str) -> tuple[str | None, str]:
        """(scope folder or None when unsure, reason)."""
        accepted: list[tuple[str | None, str]] = []
        text = "\n\n".join(f"[{c.heading}]\n{c.text}" for c in chunks)[:SCOPE_TEXT_CHARS]
        entities = sorted({t.entity for t in tags}) or ["none"]
        message = (f"Existing scope folders: {', '.join(existing) or 'none yet'}\n"
                   f"Entities found in the document: {', '.join(entities)}\n"
                   f"The rules could not decide: {rule_reason}\n\nStart of the document:\n{text}")
        try:
            AgentLoop(self.client, scope_package(accepted), load_prompt(SCOPE_PROMPT), message, MAX_TURNS, "scope decider").run()
        except Exception as error:
            return None, f"scope fallback failed: {error}"
        if not accepted:
            return None, "scope fallback gave no answer"
        scope, reason = accepted[-1]
        return scope, reason
