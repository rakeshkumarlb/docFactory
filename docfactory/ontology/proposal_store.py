import json
from pathlib import Path

from docfactory.bundle.file_io import put_text
from docfactory.ingest.paths import staging_dir
from docfactory.models.type_proposal import TypeProposal

PENDING = "pending"
APPLIED = "applied"
ASKED_FILE = "_asked.json"


class ProposalStore:
    """The proposed new entity types: the only writer and reader of `staging/type_proposals/`.

    One file per proposal (`<Entity>.json`: its status, `pending` until a developer step has applied it, and the proposal). The file `_asked.json`
    remembers, per original, the hash of the chunks that were last looked at, so unchanged chunks are not asked again. Proposals are working
    state outside the bundle: they become part of the system only when applied (model, registry entry, signals) and reviewed.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else staging_dir() / "type_proposals"

    def _path(self, entity: str) -> Path:
        return self.root / f"{entity}.json"

    def save(self, proposal: TypeProposal) -> bool:
        """Store `proposal` as pending. False, touching nothing, when a proposal with this entity name is stored already."""
        if self._path(proposal.entity).is_file():
            return False
        put_text(self._path(proposal.entity), json.dumps({"status": PENDING, "proposal": json.loads(proposal.model_dump_json())}, indent=2, ensure_ascii=False) + "\n")
        return True

    def get(self, entity: str) -> tuple[str, TypeProposal] | None:
        """(status, proposal) of the stored proposal, or None."""
        path = self._path(entity)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["status"], TypeProposal.model_validate(data["proposal"])

    def list(self) -> list[tuple[str, TypeProposal]]:
        """Every stored proposal as (status, proposal), ordered by entity name."""
        names = sorted(p.stem for p in self.root.glob("*.json") if p.name != ASKED_FILE) if self.root.is_dir() else []
        return [self.get(name) for name in names]

    def mark_applied(self, entity: str) -> None:
        """Record that the developer step created the entity from its proposal. FileNotFoundError when there is no such proposal."""
        found = self.get(entity)
        if found is None:
            raise FileNotFoundError(f"no proposal for {entity!r}")
        put_text(self._path(entity), json.dumps({"status": APPLIED, "proposal": json.loads(found[1].model_dump_json())}, indent=2, ensure_ascii=False) + "\n")

    def asked(self, path: str) -> str | None:
        """The hash of the chunks of the original `path` that were last looked at, or None."""
        file = self.root / ASKED_FILE
        return json.loads(file.read_text(encoding="utf-8")).get(path) if file.is_file() else None

    def mark_asked(self, path: str, chunks_hash: str) -> None:
        """Remember that the chunks of `path` with this hash were looked at."""
        file = self.root / ASKED_FILE
        data = json.loads(file.read_text(encoding="utf-8")) if file.is_file() else {}
        data[path] = chunks_hash
        put_text(file, json.dumps(data, indent=2, sort_keys=True) + "\n")
