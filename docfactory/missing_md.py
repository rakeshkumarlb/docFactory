"""The text of a fact's <Entity>.missing.md: its open questions as a simple Markdown list. Same questions in, same bytes out."""
from docfactory.models.fact_question import FactQuestion

LABEL_CHARS = 120  # an item label longer than this (a long statement among its mandatory fields) is cut with '...'


def _label(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= LABEL_CHARS else text[:LABEL_CHARS - 3].rstrip() + "..."


def _entry(number: int, question: FactQuestion) -> str:
    where = f"`{question.path}`"
    if question.item_count is not None:
        where += f" (missing in {question.missing_in} of {question.item_count} items)"
    lines = [f"{number}. {where}: {question.question}", f"   Assumed until answered: {question.default_assumed}"]
    if question.missing_items:
        lines.append("   Items:")
        lines += [f"   - {_label(item)}" for item in question.missing_items]
    return "\n".join(lines) + "\n"


def missing_md(key: str, questions: list[FactQuestion]) -> str:
    """The file content for the fact `key` (call it only when `questions` is not empty)."""
    header = (f"# Open questions: {key}\n\n"
              "These fields are not answered yet. Until someone answers them, the default shown is assumed.\n\n")
    return header + "".join(_entry(number, question) for number, question in enumerate(questions, 1))
