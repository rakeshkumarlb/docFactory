"""The text of a fact's concept file: OKF frontmatter, the validated JSON under `# Value` and the open questions. Same inputs, same bytes."""
import json

from pydantic import BaseModel

from docfactory.missing_md import missing_md
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord
from docfactory.okf_frontmatter import render_frontmatter
from docfactory.open_questions import open_questions

DEFAULT_GENERATED_BY = "docfactory/unspecified"
VALUE_HEADING = "# Value"
FENCE = "```"


def render_fact_file(record: FactRecord, fact: BaseModel, split: frozenset[str] = frozenset(), items: str = "") -> str:
    """The whole file for `record`; `fact` is the validated object whose JSON (model field order) is the content.

    The fields in `split` (lists stored as item concepts) are left out of the JSON block; `items` is the ready `# Items` section linking them.
    """
    meta = FactMeta(
        generated_by=record.generated_by or DEFAULT_GENERATED_BY, title=record.title, description=record.description,
        tags=record.tags, sources=record.sources, stale_after=record.stale_after,
    )
    frontmatter = render_frontmatter(record, record.type or record.key, meta) + f"hashcode: {json.dumps(record.hashcode)}\n"
    value = json.dumps(json.loads(fact.model_dump_json(exclude=set(split))), indent=2, ensure_ascii=False)
    text = f"---\n{frontmatter}---\n\n{VALUE_HEADING}\n\n{FENCE}json\n{value}\n{FENCE}\n"
    questions = open_questions(fact)
    if questions:
        text += "\n" + missing_md(record.key, questions)
    if items:
        text += "\n" + items
    return text
