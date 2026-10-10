from docfactory.agents.agent_loop import AgentLoop
from docfactory.agents.model_client import ModelClient
from docfactory.agents.prompt_file import load_prompt
from docfactory.db import PROJECT_ROOT
from docfactory.documentmodels.document_gap import DocumentGap
from docfactory.documentmodels.document_need import DocumentNeed
from docfactory.tools.needs_tools import needs_package

PROMPT_FILE = PROJECT_ROOT / ".claude" / "agents" / "docfactory-needs-list-agent.md"
MAX_TURNS = 6


class NeedsWriter:
    """The LLM step of generation: one fresh AgentLoop with exactly one tool (submit_needs) that turns a document's gaps into its needs list.

    It sees the application, the document name and the numbered gaps, nothing else; the tool checks that every gap is covered and no
    unknown gap is cited. Called as writer(app_id, doc_name, gaps) -> (needs, '') or (None, what went wrong); it never raises.
    """

    def __init__(self, client: ModelClient, system: str | None = None) -> None:
        self.client = client
        self.system = system if system is not None else load_prompt(PROMPT_FILE)

    @staticmethod
    def gap_lines(gaps: list[DocumentGap]) -> str:
        """The numbered gaps as the model sees them: field, question, source, 'missing in k of n' and the example items."""
        lines = []
        for gap in gaps:
            counts = f" (missing in {gap.missing_in} of {gap.item_count} items)" if gap.missing_in is not None and gap.item_count is not None else ""
            lines.append(f"#{gap.number} {gap.field}{counts}: {gap.question} [source: {gap.expected_source}]")
            lines += [f"    e.g. {example}" for example in gap.example_items]
        return "\n".join(lines)

    def __call__(self, app_id: str, doc_name: str, gaps: list[DocumentGap]) -> tuple[list[DocumentNeed] | None, str]:
        accepted: list[list[DocumentNeed]] = []
        message = f"Application: {app_id}\nDocument: {doc_name}\n\nGaps ({len(gaps)}):\n{self.gap_lines(gaps)}"
        try:
            AgentLoop(self.client, needs_package(gaps, accepted), self.system, message, MAX_TURNS, "needs writer").run()
        except Exception as error:  # a failed call falls back to one need per gap; it never blocks the document
            if accepted:  # the answer was accepted; only the closing reply failed
                return accepted[-1], ""
            return None, str(error)
        if not accepted:
            return None, "the model ended without an accepted submit_needs call"
        return accepted[-1], ""
