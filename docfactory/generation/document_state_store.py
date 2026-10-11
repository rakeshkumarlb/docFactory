import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.file_io import put_text
from docfactory.bundle.paths import is_safe_segment, resolve_in
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.completeness import completeness
from docfactory.generation.document_parts import PART_MODELS, part_key
from docfactory.generation.generation_steps import output_dir
from docfactory.models.document_record import DocumentRecord
from docfactory.models.save_action import SaveAction
from docfactory.models.save_result import SaveResult
from docfactory.validation_errors import validation_errors

STATE_DIR = "state"


class DocumentStateStore:
    """The stored state of the generated documents: one JSON file per part, `output/<App>/state/<DocType>.<part>.json`.

    Each file holds the validated object with its key, version, hash and completeness. `save` validates with the part's model, hashes
    and versions it like any stored object (same hash = UNCHANGED, a new value CREATED at version 1 or UPDATED at version + 1) and writes
    the file only when something changed. Written only by the generate process and the seeds; a file whose JSON no longer matches its hash
    was edited outside the system and is refused on read. The rendered `.md` files beside it are views of these.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else output_dir()

    def path(self, app_id: str, doc_type: str, part: str) -> Path:
        """The state file of one part (ValueError when the application or document name is not a plain folder or file name)."""
        for name in (app_id, doc_type):
            if not is_safe_segment(name):
                raise ValueError(f"{name!r} cannot be used as a folder or file name")
        return resolve_in(self.root, f"{app_id}/{STATE_DIR}/{doc_type}.{part}.json")

    def read(self, app_id: str, doc_type: str, part: str) -> DocumentRecord | None:
        """The stored part as a record (`value` is canonical JSON), or None. BundleError when the file cannot be trusted."""
        path = self.path(app_id, doc_type, part)
        return self._parse(path) if path.is_file() else None

    def model(self, app_id: str, doc_type: str, part: str):
        """The stored part validated as its model (DocumentBody, DocumentControl, RevisionHistory or MissingInfo), or None."""
        record = self.read(app_id, doc_type, part)
        return PART_MODELS[part].model_validate_json(record.value) if record else None

    def list(self, app_id: str | None = None) -> list[DocumentRecord]:
        """Every stored part ordered by key; with `app_id`, only that application's."""
        pattern = f"{app_id}/{STATE_DIR}/*.json" if app_id else f"*/{STATE_DIR}/*.json"
        paths = [p for p in self.root.glob(pattern) if p.is_file()] if self.root.is_dir() else []
        return sorted((self._parse(p) for p in paths), key=lambda record: record.key)

    def save(self, app_id: str, doc_type: str, part: str, payload) -> SaveResult:
        """Save the whole part (`payload` is a model instance or a dict). Never raises for bad input: a rejection is returned, nothing is written."""
        key = part_key(app_id, doc_type, part)
        model = PART_MODELS[part]
        try:
            instance = model.model_validate(payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload)
        except ValidationError as error:
            return SaveResult(ok=False, key=key, action=SaveAction.REJECTED, errors=validation_errors(model, error))
        dumped = instance.model_dump(mode="json")
        hashcode = sha256_hex(canonical_json(dumped))
        existing = self.read(app_id, doc_type, part)
        if existing is not None and existing.hashcode == hashcode:
            return SaveResult(ok=True, key=key, action=SaveAction.UNCHANGED, version=existing.version, hashcode=hashcode,
                              completeness=existing.completeness)
        action, version = (SaveAction.CREATED, 1) if existing is None else (SaveAction.UPDATED, existing.version + 1)
        score = completeness(instance)
        state = {"key": key, "version": version, "hashcode": hashcode, "completeness": score, "value": dumped}
        put_text(self.path(app_id, doc_type, part), json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        return SaveResult(ok=True, key=key, action=action, version=version, hashcode=hashcode, completeness=score)

    def _parse(self, path: Path) -> DocumentRecord:
        label = path.relative_to(self.root).as_posix()
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            value = canonical_json(state["value"])
            if sha256_hex(value) != state["hashcode"]:
                raise ValueError("the stored JSON does not match its hashcode; the file was edited outside the system")
            key = state["key"]
            return DocumentRecord(key=key, value=value, hashcode=state["hashcode"], completeness=state["completeness"], version=state["version"],
                                  app_id=key.split(".")[0])
        except (ValueError, KeyError, TypeError, ValidationError) as error:
            raise BundleError(f"{label}: not a readable document state: {error}") from error
