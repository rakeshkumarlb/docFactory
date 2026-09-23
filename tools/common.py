"""Shared helpers for docFactory tools (stdlib only)."""
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(os.environ.get("DOCFACTORY_ROOT") or Path(__file__).resolve().parent.parent)
TEMPLATES = ROOT / "templates"
STORE = ROOT / "store"
KNOWLEDGE = ROOT / "knowledge"
REVIEW = ROOT / "review"
OUTPUT = ROOT / "output"
INCOMING = ROOT / "incoming"
DB_PATH = ROOT / "db" / "docfactory.sqlite"

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FIELD_RE = re.compile(r"<!--\s*field\s+(.*?)\s*-->")
INCLUDE_RE = re.compile(r"<!--\s*include:\s*(\S+?)(?:\s+shift=(-?\d+))?\s*-->")
ATTR_RE = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
NUMBER_PREFIX_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+")


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def write_text(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel(path):
    """Repo-root-relative posix path."""
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, text[m.end():]


def dump_frontmatter(meta):
    return "---\n" + "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n---\n"


def parse_attrs(s):
    return {m.group(1): (m.group(2) if m.group(2) is not None else m.group(3)) for m in ATTR_RE.finditer(s)}


class Section:
    def __init__(self, level, title, start):
        self.level = level
        self.title = title
        self.start = start  # line index of heading (-1 for preamble)
        self.body = []  # raw lines after heading up to next heading
        self.field = None  # attrs dict if a field directive is present
        self.field_line = None  # absolute line index of the directive

    @property
    def end(self):
        return self.start + 1 + len(self.body)


def split_sections(lines):
    """Split lines into sections by markdown headings, ignoring fenced code blocks."""
    sections = [Section(0, "", -1)]
    fence = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
        m = None if fence else HEADING_RE.match(line)
        if m:
            sections.append(Section(len(m.group(1)), m.group(2), i))
        else:
            sections[-1].body.append(line)
    for s in sections:
        for j, line in enumerate(s.body):
            fm = FIELD_RE.search(line)
            if fm and s.field is None:
                s.field = parse_attrs(fm.group(1))
                s.field_line = s.start + 1 + j
    return sections


def strip_number(title):
    return NUMBER_PREFIX_RE.sub("", title)


def load_json(path):
    return json.loads(read_text(path))
