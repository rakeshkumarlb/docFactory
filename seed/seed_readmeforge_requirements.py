"""Seeds the ReadmeForge functional and non-functional requirements from the samples.

Hard-coded, Phase 1 seed script (CLAUDE.md "Data flow"): no parsing of source documents, just tool calls.

    python -m seed.seed_readmeforge_requirements

No document uses these facts yet, so this script only stores them. The minimal functional sample is saved first
and the full one after it, so the run also exercises versioning. Saving a payload that is already stored is a
no-op (UNCHANGED), so the script can be re-run.
"""
import json
from pathlib import Path

from docfactory.entitysaver.functional_requirements_saver import FunctionalRequirementsSaver
from docfactory.entitysaver.non_functional_requirements_saver import NonFunctionalRequirementsSaver

ROOT = Path(__file__).resolve().parents[1]
APP = "ReadmeForge"

# (saver, fact key, sample folder under samples/, sample file)
FACTS = (
    (FunctionalRequirementsSaver, f"{APP}.FunctionalRequirements", "functional_requirements", "readmeforge_minimal.json"),
    (FunctionalRequirementsSaver, f"{APP}.FunctionalRequirements", "functional_requirements", "readmeforge_full.json"),
    (NonFunctionalRequirementsSaver, f"{APP}.NonFunctionalRequirements", "non_functional_requirements", "readmeforge_full.json"),
)


def main() -> None:
    for saver, key, folder, name in FACTS:
        payload = json.loads((ROOT / "samples" / folder / name).read_text(encoding="utf-8"))
        result = saver().save(key, payload)
        print(f"{name}: {key} {result.action} version={result.version} completeness={result.completeness}")
        assert result.ok, result.errors


if __name__ == "__main__":
    main()
