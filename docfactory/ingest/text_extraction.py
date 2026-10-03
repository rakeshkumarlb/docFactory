from pathlib import Path

# Originals that already are text: no conversion and no sidecar.
TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".json", ".yaml", ".yml"}
SIDECAR_SUFFIX = ".md"


def is_text_file(path: Path) -> bool:
    """True when the original is plain text and needs no conversion."""
    return path.suffix.lower() in TEXT_SUFFIXES


def file_text(path: Path) -> str:
    """The text of a file: plain text read as UTF-8, anything else (PDF, Word, HTML, ...) converted with markitdown.

    Raises on an unreadable or unconvertible file; callers turn that into a structured error.
    """
    if is_text_file(path):
        return path.read_text(encoding="utf-8", errors="replace")
    from markitdown import MarkItDown  # imported here: heavy, and only non-text files need it

    return MarkItDown().convert(str(path)).text_content


def sidecar_path(original: Path) -> Path:
    """Where the text sidecar of `original` sits: next to it, with '.md' appended to the full name."""
    return original.with_name(original.name + SIDECAR_SUFFIX)
