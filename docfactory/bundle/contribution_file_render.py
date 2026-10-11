"""The text of a contribution concept file: OKF frontmatter and the partial fact the original states under `# Value`. Same record, same bytes."""
import json

from docfactory.bundle.fact_file_render import FENCE, VALUE_HEADING
from docfactory.bundle.paths import EXISTING_RESOURCE
from docfactory.models.fact_contribution import FactContribution

CONTRIBUTION_TYPE = "Contribution"


def _text(value: str) -> str:
    """A YAML double-quoted scalar (JSON strings are valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def render_contribution_file(record: FactContribution) -> str:
    """The whole file for `record`."""
    origin = "the system" if record.resource == EXISTING_RESOURCE else record.resource.rsplit("/", 1)[-1]
    lines = [f"type: {_text(CONTRIBUTION_TYPE)}", f"title: {_text(f'{record.fact_key} from {origin}')}"]
    if record.description:
        lines.append(f"description: {_text(record.description)}")
    lines.append("sources:" if record.resource != EXISTING_RESOURCE else "sources: []")
    if record.resource != EXISTING_RESOURCE:
        lines.append(f"  - resource: {_text(record.resource)}")
    lines += [
        f"generated: {{ by: {_text(record.generated_by)}, at: {_text(record.timestamp)} }}",
        f"fact_key: {_text(record.fact_key)}",
        f"hashcode: {_text(record.hashcode)}",
    ]
    if record.chunks_hash:
        lines.append(f"chunks_hash: {_text(record.chunks_hash)}")
    value = json.dumps(json.loads(record.value_json), indent=2, ensure_ascii=False)
    return "---\n" + "\n".join(lines) + f"\n---\n\n{VALUE_HEADING}\n\n{FENCE}json\n{value}\n{FENCE}\n"
