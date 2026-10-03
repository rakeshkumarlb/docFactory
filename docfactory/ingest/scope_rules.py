"""Deterministic scope decision for a NEW file: which DocStore folder (application name, `shared` or `general`) it belongs to.

1. Tags decide `shared`: a document whose tags name only shared entities (keys `Shared.<Name>`, e.g. Slo, Kpis) is a common standard.
2. Otherwise the application name is looked for in the front matter, most reliable first:
   a. a document-control row 'Title | ...', 'Project | ...', 'Application | ...', 'System | ...' or 'Product | ...';
   b. the first lines of the document (the cover title, the first heading).
   Document-type wording ('Software Requirements Specification for', 'Requirements', '(working draft 0.3)', ...) is removed; a line
   broken inside a word ('AI- Driven') is mended.
3. A candidate that matches an existing scope folder (ignoring case and punctuation, or one containing the other) reuses that folder.
4. Confident = matched an existing folder, came from a document-control row, or had document-type wording removed (so what is
   left is the name). Anything else is returned unconfident: the LLM fallback (or a human) decides.
The folder name is the candidate with runs of other characters replaced by '-': 'AI-Driven Job Matching Platform' ->
'AI-Driven-Job-Matching-Platform'.
"""
import re

from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.doc_chunk import DocChunk
from docfactory.saver_resolution import entity_saver_classes

SHARED, GENERAL = "shared", "general"
FRONT_LINES = 4  # first lines of the document looked at for a title
_TITLE_ROW = re.compile(r"^(title|project|project name|application|application name|system|system name|product|product name)\s*\|\s*(.+)$",
                        re.IGNORECASE)
_DOC_TYPES = [
    "software requirements specification", "requirements specification", "functional specification", "system requirements",
    "requirements", "srs", "system management technical document", "system management", "smtd", "technical design document",
    "technical design", "design document", "architecture document", "standard operating procedures", "operating procedures", "sop",
    "on-call runbooks", "runbooks", "runbook", "user guide", "user manual", "manual", "how we run it", "working draft", "draft",
    "document control", "specification", "document",
]
_DOC_TYPE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(t).replace(r"\ ", r"\s+") for t in _DOC_TYPES) + r")(?![\w-])", re.IGNORECASE)
_EDGE_WORDS = re.compile(r"^(?:(?:for|of|the|and|to|-|:|–)\s+)+|(?:\s+(?:for|of|the|and|to|-|:|–))+$", re.IGNORECASE)


def shared_entities() -> set[str]:
    """Entities stored only under `Shared.` keys (common to all applications)."""
    return {cls.model.__name__ for cls in entity_saver_classes() if all(p.startswith("Shared.") for p in cls.key_patterns)}


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def folder_name(name: str) -> str:
    """A legal scope folder name: letters, digits, '.', '_' and '-' only, e.g. 'AI-Driven Job Matching Platform' -> 'AI-Driven-Job-Matching-Platform'."""
    return re.sub(r"-{2,}", "-", re.sub(r"[^A-Za-z0-9._-]+", "-", name)).strip("-._")


def clean_title(text: str) -> tuple[str, bool]:
    """(the name left after removing document-type wording, whether any was removed)."""
    text = re.sub(r"(\w)- (\w)", r"\1-\2", " ".join(text.split()))  # 'AI- Driven' -> 'AI-Driven'
    text = re.sub(r"\([^)]*\)", " ", text)  # '(SRS)', '(working draft 0.3)'
    stripped = _DOC_TYPE.sub(" ", text)
    removed = stripped != text
    stripped = re.sub(r"\bv?\d+(\.\d+)+\b", " ", stripped)  # versions
    stripped = " ".join(stripped.split())
    stripped = re.split(r"\s+[-–:]\s+", stripped)[0] if re.search(r"\s+[-–:]\s+", stripped) else stripped
    previous = None
    while previous != stripped:
        previous, stripped = stripped, _EDGE_WORDS.sub("", stripped).strip(" -–:,.")
    return stripped, removed


def _candidates(chunks: list[DocChunk]) -> list[tuple[str, bool, str]]:
    """(name, confident, source) candidates, most reliable first."""
    found = []
    lines = [line for chunk in chunks[:3] for line in chunk.text.splitlines()]
    for line in lines:
        match = _TITLE_ROW.match(line)
        if match:
            name, _ = clean_title(match.group(2))
            if name:
                found.append((name, True, f"document control row '{match.group(1)}'"))
    heads = [chunk.heading.split(" > ")[0] for chunk in chunks[:1] if chunk.heading != "Front matter"]
    for line in heads + lines[:FRONT_LINES]:
        name, removed = clean_title(line)
        if name and len(name.split()) <= 8:
            found.append((name, removed, f"title line '{line[:60]}'"))
    return found


def decide_scope(chunks: list[DocChunk], tags: list[ChunkTag], existing: list[str]) -> tuple[str | None, bool, str]:
    """(scope folder or None, confident, reason). `existing` are the scope folders already in the DocStore."""
    tagged = {tag.entity for tag in tags}
    if tagged and tagged <= shared_entities():
        match = next((folder for folder in existing if folder.lower() == SHARED), SHARED)
        return match, True, f"only shared entities tagged ({', '.join(sorted(tagged))})"
    candidates = _candidates(chunks)
    for name, _, source in candidates:
        key = _key(name)
        for folder in existing:
            other = _key(folder)
            if key and other and folder.lower() not in (SHARED, GENERAL) and (key == other or key in other or other in key):
                return folder, True, f"matches existing folder '{folder}' ({source})"
    for name, confident, source in candidates:
        if confident:
            return folder_name(name), True, f"{source} -> '{name}'"
    if candidates:
        name, _, source = candidates[0]
        return folder_name(name), False, f"unconfident: {source} -> '{name}'"
    return None, False, "no title found"
