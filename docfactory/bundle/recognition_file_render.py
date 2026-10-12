"""The text of a recognition concept file: OKF frontmatter and what recognition found in one original, window by window, under `# Value`. Same record, same bytes."""
import json

from docfactory.bundle.fact_file_render import FENCE, VALUE_HEADING
from docfactory.models.file_recognition import FileRecognition

RECOGNITION_TYPE = "Recognition"


def _text(value: str) -> str:
    """A YAML double-quoted scalar (JSON strings are valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def render_recognition_file(record: FileRecognition) -> str:
    """The whole file for `record`."""
    name = record.resource.rsplit("/", 1)[-1]
    entities = sum(len(w.entities) for w in record.windows)
    relations = sum(len(w.relations) for w in record.windows)
    lines = [
        f"type: {_text(RECOGNITION_TYPE)}",
        f"title: {_text(f'Recognition of {name}')}",
        f"description: {_text(f'{entities} entities and {relations} relationships recognized in {len(record.windows)} windows of {name}.')}",
        "sources:",
        f"  - resource: {_text(record.resource)}",
        f"generated: {{ by: {_text(record.generated_by)}, at: {_text(record.timestamp)} }}",
        f"hashcode: {_text(record.hashcode)}",
    ]
    value = json.dumps([w.model_dump(mode="json") for w in record.windows], indent=2, ensure_ascii=False)
    return "---\n" + "\n".join(lines) + f"\n---\n\n{VALUE_HEADING}\n\n{FENCE}json\n{value}\n{FENCE}\n"
