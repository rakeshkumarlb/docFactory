import json
from pathlib import Path

from pydantic import ValidationError

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_log import append_entry
from docfactory.bundle.fact_file_parse import split_frontmatter, value_block
from docfactory.bundle.fact_file_render import FENCE, VALUE_HEADING
from docfactory.bundle.file_io import put_text
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.bundle.paths import bundle_root, resolution_relpath
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.resolution_group import ResolutionGroup
from docfactory.models.scope_resolution import ScopeResolution

RESOLUTION_TYPE = "Entity Resolution"


def _text(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _value(groups: list[ResolutionGroup], asked: list[str]) -> dict:
    return {"groups": [g.model_dump(mode="json") for g in groups], "asked": list(asked)}


class ResolutionStore:
    """The entity resolution decisions of each scope: one concept, `<scope>/recognition/resolution/decisions.md`, holding which entities of
    one type are the same thing and, per type, the hash of the entities the decision was based on. The merge applies the decisions every time
    the entity graph is rebuilt. Written only by the resolution step; a file whose JSON no longer matches its hash is refused on read.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else bundle_root()

    def get(self, scope: str) -> ScopeResolution | None:
        """The decisions of `scope`, or None. BundleError when the file cannot be trusted."""
        path = self.root / resolution_relpath(scope)
        if not path.is_file():
            return None
        try:
            frontmatter_text, body = split_frontmatter(path.read_text(encoding="utf-8"))
            meta = load_frontmatter(frontmatter_text)
            value = json.loads(value_block(body))
            if meta.get("type") != RESOLUTION_TYPE or sha256_hex(canonical_json(value)) != meta["hashcode"]:
                raise ValueError("not a resolution concept, or the stored JSON does not match its hashcode (edited outside the system)")
            return ScopeResolution(scope=scope, groups=[ResolutionGroup.model_validate(g) for g in value["groups"]], asked=value["asked"],
                                   hashcode=meta["hashcode"], generated_by=meta["generated"]["by"], timestamp=meta["generated"]["at"])
        except (ValueError, KeyError, TypeError, ValidationError) as error:
            raise BundleError(f"{resolution_relpath(scope)}: not a readable resolution: {error}") from error

    def save(self, scope: str, groups: list[ResolutionGroup], asked: list[str], generated_by: str, timestamp: str) -> ScopeResolution:
        """Store the decisions of `scope` (replacing earlier ones) and return them."""
        value = _value(groups, asked)
        hashcode = sha256_hex(canonical_json(value))
        record = ScopeResolution(scope=scope, groups=groups, asked=asked, hashcode=hashcode, generated_by=generated_by, timestamp=timestamp)
        before = self.get(scope)
        lines = [f"type: {_text(RESOLUTION_TYPE)}", f"title: {_text(f'Entity resolution of {scope}')}",
                 f"description: {_text(f'{len(groups)} groups of entities that are the same thing.')}",
                 f"generated: {{ by: {_text(generated_by)}, at: {_text(timestamp)} }}", f"hashcode: {_text(hashcode)}"]
        body = json.dumps(value, indent=2, ensure_ascii=False)
        relpath = resolution_relpath(scope)
        put_text(self.root / relpath, "---\n" + "\n".join(lines) + f"\n---\n\n{VALUE_HEADING}\n\n{FENCE}json\n{body}\n{FENCE}\n")
        if before is None or before.hashcode != hashcode:
            append_entry(self.root, timestamp[:10], f"* **{'Creation' if before is None else 'Update'}**: [entity resolution of {scope}](/{relpath}) by {generated_by}")
        return record
