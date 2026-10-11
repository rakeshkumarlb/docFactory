"""Seeds the ReadmeForge functional and non-functional requirements from the samples.

Hard-coded, Phase 1 seed script (CLAUDE.md "Data flow"): no parsing of source documents, just tool calls.

    python -m seed.seed_readmeforge_requirements

No document uses these facts yet, so this script only stores them. The minimal functional sample is saved first
and the full one after it, so the run also exercises versioning. Saving a payload that is already stored is a
no-op (UNCHANGED), so the script can be re-run.
"""
import json
from pathlib import Path

from docfactory.bundle.bundle_store import BundleStore
from seed.seed_meta import SEED_META

ROOT = Path(__file__).resolve().parents[1]
APP = "ReadmeForge"

# (fact key, sample folder under samples/json/, sample file)
FACTS = (
    (f"{APP}.FunctionalRequirements", "functional_requirements", "readmeforge_minimal.json"),
    (f"{APP}.FunctionalRequirements", "functional_requirements", "readmeforge_full.json"),
    (f"{APP}.NonFunctionalRequirements", "non_functional_requirements", "readmeforge_full.json"),
)


def main() -> None:
    for key, folder, name in FACTS:
        payload = json.loads((ROOT / "samples" / "json" / folder / name).read_text(encoding="utf-8"))
        result = BundleStore().write_fact(key, payload, SEED_META)
        print(f"{name}: {key} {result.action} version={result.version} completeness={result.completeness}")
        assert result.ok, result.errors


if __name__ == "__main__":
    main()
