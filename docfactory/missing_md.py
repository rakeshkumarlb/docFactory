"""The text of a fact's <Entity>.missing.md: its open questions as a simple Markdown list. Same questions in, same bytes out."""
from docfactory.models.fact_question import FactQuestion


def _line(number: int, question: FactQuestion) -> str:
    where = f"`{question.path}`"
    if question.item_count is not None:
        where += f" (missing in {question.missing_in} of {question.item_count} items)"
    return f"{number}. {where}: {question.question}\n   Assumed until answered: {question.default_assumed}\n"


def missing_md(key: str, questions: list[FactQuestion]) -> str:
    """The file content for the fact `key` (call it only when `questions` is not empty)."""
    header = (f"# Open questions: {key}\n\n"
              "These fields are not answered yet. Until someone answers them, the default shown is assumed.\n\n")
    return header + "".join(_line(number, question) for number, question in enumerate(questions, 1))
