"""Usage: python .claude/scripts/find_usages.py <Name>

Lists every whole-word occurrence of a class or field name in the package, tests, seed data,
rendered output and golden files, grouped by what it is. Use it before changing a model.
"""
import re
import sys

import conventions as C
import naming

ROOTS = (C.PACKAGE, "tests", "seed", "output")
SUFFIXES = {".py", ".md", ".json"}


def category(path: str) -> str:
    parts = path.split("/")
    if parts[0] == "tests":
        return "tests"
    if parts[0] in ("seed", "output"):
        return parts[0]
    if len(parts) > 1 and parts[1] in C.ALL_FOLDERS:
        return parts[1]
    return "package"


def main(argv) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    word = re.compile(r"\b" + re.escape(argv[0]) + r"\b")
    hits = {}
    for root in ROOTS:
        base = C.ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in SUFFIXES or "__pycache__" in path.parts:
                continue
            rel = naming.rel(path)
            for number, text in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if word.search(text):
                    hits.setdefault(category(rel), []).append(f"{rel}:{number}: {text.strip()}")
    for name in sorted(hits):
        print(f"## {name}")
        print(*hits[name], sep="\n")
    print(f"{sum(len(v) for v in hits.values())} occurrence(s) of {argv[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
