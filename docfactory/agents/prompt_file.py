from pathlib import Path


def load_prompt(path: Path) -> str:
    """An agent's system prompt: the markdown file without its YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    return text.strip()
