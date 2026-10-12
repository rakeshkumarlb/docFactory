"""Score the entity graph and facts of a scope against an expectations file (read-only, no LLM):
`python -m docfactory.agents.run_scoring <scope> [<expectations.json>]`, e.g. `AI-Driven-Job-Matching-Platform tests/corpus/jobmatch_expectations.json`.
"""
import sys
from pathlib import Path

from docfactory.project_root import PROJECT_ROOT
from docfactory.recognize.expectation_score import score

DEFAULT_EXPECTATIONS = PROJECT_ROOT / "tests" / "corpus" / "jobmatch_expectations.json"


def main(argv: list[str]) -> int:
    if not argv or len(argv) > 2:
        print(__doc__)
        return 2
    print(score(argv[0], Path(argv[1]) if len(argv) == 2 else DEFAULT_EXPECTATIONS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
