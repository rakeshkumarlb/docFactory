"""Where the bundle is and where a fact's concept file sits in it. Facts are written only by BundleStore; nothing here writes."""
import os
import re
from pathlib import Path

from docfactory.project_root import PROJECT_ROOT

ENV_VAR = "DOCFACTORY_BUNDLE"
BUNDLE_DIR = "bundle"
RESERVED_FILES = ("index.md", "log.md")  # OKF section 3.1: never concept files
REFERENCES_DIR = "references"  # OKF section 6.3: the originals of a scope
SOURCES_DIR = "sources"  # the Source concept of each original (and, per original, its contributions)
NON_FACT_DIRS = (REFERENCES_DIR, SOURCES_DIR)  # inside a scope folder: not facts
EXISTING_RESOURCE = "(existing)"  # the resource of a fact value stored before any extraction (e.g. seed data): lowest precedence
SHARED_FOLDER = "Shared"  # the scope folder of common facts and of the originals ingested as `shared`
SUFFIX = ".md"
_UNSAFE = re.compile(r'[\x00-\x1f/\\:*?"<>|]')
_RESERVED_NAMES = {"con", "prn", "aux", "nul", *(f"com{n}" for n in range(1, 10)), *(f"lpt{n}" for n in range(1, 10))}


def bundle_root() -> Path:
    """The folder of the bundle: env DOCFACTORY_BUNDLE, else bundle/ under the project root."""
    override = os.environ.get(ENV_VAR)
    return Path(override) if override else PROJECT_ROOT / BUNDLE_DIR


def is_safe_segment(segment: str) -> bool:
    """True when `segment` can be one folder or file name: not empty, no separators or reserved characters, no edge spaces, not `.` or `..`, not a reserved device name."""
    return bool(segment) and segment == segment.strip() and not _UNSAFE.search(segment) and segment not in (".", "..") and segment.lower() not in _RESERVED_NAMES


def fact_relpath(key: str) -> str:
    """The path of a fact's concept file relative to the bundle, forward slashes: Shared.Kpis -> Shared/Kpis.md.

    Raises ValueError when a key segment (component names are free text) could leave the folder or is not a legal file name.
    """
    segments = key.split(".")
    for segment in segments:
        if not is_safe_segment(segment):
            raise ValueError(f"key segment {segment!r} of {key!r} cannot be used as a file name")
    if len(segments) < 2 or segments[1] in NON_FACT_DIRS:
        raise ValueError(f"key {key!r} must be <Scope>.<Name> and its second segment must not be one of {NON_FACT_DIRS}")
    return "/".join(segments) + SUFFIX


def resolve_in(root: Path, relative: str) -> Path:
    """The absolute path of `relative` under `root`; ValueError when it would leave the bundle."""
    base = root.resolve()
    target = (base / relative).resolve()
    if base not in target.parents:
        raise ValueError(f"{relative!r} is outside the bundle")
    return target


def scope_folder(scope: str) -> str:
    """The bundle folder of an ingestion scope: `shared` (any case) is the folder of the Shared facts, every other scope is its own name."""
    return SHARED_FOLDER if scope.lower() == SHARED_FOLDER.lower() else scope


def reference_path(scope: str, file_name: str) -> str:
    """The bundle-relative path of an original, forward slashes: ('Acme', 'srs.pdf') -> 'Acme/references/srs.pdf'. This is its resource everywhere."""
    return f"{scope_folder(scope)}/{REFERENCES_DIR}/{file_name}"


def source_relpath(resource: str) -> str:
    """The bundle-relative path of the Source concept of the original `resource`: 'Acme/references/srs.pdf' -> 'Acme/sources/srs.pdf.md'.

    Raises ValueError when `resource` is not '<scope>/references/<file name>'.
    """
    parts = resource.split("/")
    if len(parts) != 3 or parts[1] != REFERENCES_DIR or not parts[0] or not parts[2]:
        raise ValueError(f"{resource!r} is not '<scope>/{REFERENCES_DIR}/<file name>'")
    return f"{parts[0]}/{SOURCES_DIR}/{parts[2]}{SUFFIX}"


def contribution_relpath(key: str, resource: str) -> str:
    """The bundle-relative path of what the original `resource` contributes to the fact `key`: ('Acme.Sop', 'Acme/references/srs.pdf') ->
    'Acme/sources/srs.pdf/Sop.md'. The `(existing)` resource sits in the folder of the key's scope.

    Raises ValueError unless `key` is '<scope>.<Entity>' and `resource` is '<scope>/references/<file name>' or `(existing)`.
    """
    segments = key.split(".")
    if len(segments) != 2 or not all(segments):
        raise ValueError(f"{key!r} is not '<scope>.<Entity>'")
    if resource == EXISTING_RESOURCE:
        return f"{segments[0]}/{SOURCES_DIR}/{EXISTING_RESOURCE}/{segments[1]}{SUFFIX}"
    return source_relpath(resource).removesuffix(SUFFIX) + f"/{segments[1]}{SUFFIX}"
