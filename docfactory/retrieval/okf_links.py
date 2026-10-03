"""Bundle-relative links (OKF: they start with `/`) inside an OKF file: the files a reader should follow."""
import re

_LINK = re.compile(r"\]\((/[^)\s#]+?)(?:#[^)\s]*)?\)")


def bundle_links(text: str) -> list[str]:
    """The bundle-relative targets of the markdown links in `text`, in order of first appearance, without duplicates."""
    return list(dict.fromkeys(_LINK.findall(text)))


def fact_key_of_link(link: str) -> str | None:
    """The fact key a bundle link points to (`/ReadmeForge/Architecture.md` -> `ReadmeForge.Architecture`), or None when it is not a .md file."""
    if not link.startswith("/") or not link.endswith(".md"):
        return None
    return link[1:-3].replace("/", ".")
