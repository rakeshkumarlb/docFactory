"""Checks a bundle folder against OKF v0.2 conformance (docs/okf/SPEC.md section 11).

    python -m docfactory.okf_check [bundle folder]

Every non-reserved .md file must start with a parseable YAML frontmatter mapping holding a non-empty `type`; `index.md` may only carry
`okf_version`; links in a body must be absolute URLs or bundle-relative (start with `/`). Prints problems and exits 1, or exits 0.
"""
import re
import sys
from pathlib import Path

from docfactory.bundle import bundles_root

RESERVED = {"index.md", "log.md"}
_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_ABSOLUTE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


def _yaml():
    try:
        import yaml
    except ImportError as error:  # PyYAML is a dev dependency, used only for checking
        raise SystemExit("okf_check needs PyYAML: pip install pyyaml") from error
    return yaml


def _frontmatter(text: str, yaml):
    """(mapping, body) or (None, problem)."""
    match = _FRONTMATTER.match(text.replace("\r\n", "\n"))
    if not match:
        return None, "no YAML frontmatter block"
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        return None, f"frontmatter is not valid YAML ({error})"
    if not isinstance(data, dict):
        return None, "frontmatter is not a mapping"
    return data, text[match.end():]


def check_bundle(root: Path) -> list[str]:
    """Problems found under `root`, as 'relative/path.md: what is wrong'. Empty means conformant."""
    yaml = _yaml()
    problems = []
    for path in sorted(root.rglob("*.md")):
        name = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        data, rest = _frontmatter(text, yaml)
        if path.name == "index.md":
            if data is not None and set(data) - {"okf_version"}:
                problems.append(f"{name}: index.md may only carry okf_version in its frontmatter")
            continue
        if path.name == "log.md":
            continue
        if data is None:
            problems.append(f"{name}: {rest}")
            continue
        if not isinstance(data.get("type"), str) or not data["type"].strip():
            problems.append(f"{name}: frontmatter has no non-empty `type`")
        for target in _LINK.findall(rest):
            if not target.startswith("/") and not _ABSOLUTE.match(target) and not target.startswith("#"):
                problems.append(f"{name}: link {target!r} is neither bundle-relative (starting with /) nor absolute")
    return problems


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv else bundles_root()
    if not root.is_dir():
        print(f"no bundle folder at {root}")
        return 1
    problems = check_bundle(root)
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s) in {root}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
