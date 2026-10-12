"""The author an original document names in its own properties (OKF source credibility signal `author`). Deterministic, read-only, never raises.

PDF: the /Author entry of the document information; Word: the core property `author`; HTML: `<meta name="author">`. Anything else, an
empty value or an unreadable file gives None. The value is the document's own claim; nothing is inferred.
"""
from pathlib import Path


def _clean(value) -> str | None:
    text = " ".join(str(value).split()) if value else ""
    return text or None


def file_author(path: Path) -> str | None:
    """The author named in the properties of the file at `path`, or None."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return _clean((pdf.metadata or {}).get("Author"))
        if suffix == ".docx":
            import docx
            return _clean(docx.Document(str(path)).core_properties.author)
        if suffix in (".html", ".htm"):
            from bs4 import BeautifulSoup
            tag = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser").find("meta", attrs={"name": "author"})
            return _clean(tag.get("content")) if tag else None
    except Exception:  # an unreadable file simply names no author
        return None
    return None
