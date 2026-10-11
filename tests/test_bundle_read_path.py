"""The fact registry and the generation read path on the bundle (Step 2 of the OKF bundle redesign)."""
import json
from pathlib import Path

import pytest

from docfactory import build
from docfactory.build import load_fact
from docfactory.bundle import fact_registry
from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_store import BundleStore
from docfactory.generate import main

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "json"


@pytest.fixture
def bundle(tmp_bundle, tmp_path, monkeypatch):
    """A temporary database and bundle (tmp_bundle selects both) and output folder."""
    monkeypatch.setenv("DOCFACTORY_OUTPUT", str(tmp_path / "output"))
    return BundleStore()


def _overview(name="readmeforge_full.json"):
    return json.loads((SAMPLES / "application_overview" / name).read_text(encoding="utf-8"))


def test_every_fact_model_is_registered_exactly_once_with_key_patterns_that_match_its_scope():
    from docfactory.entitymodels.facts import __path__ as facts_path
    import pkgutil

    modules = {m.name for m in pkgutil.iter_modules(facts_path)}
    registered = {fact_registry.FACT_SPECS[name]["model"].__module__.rsplit(".", 1)[-1] for name in fact_registry.entity_names()}
    assert registered == modules  # a fact model without an entry, or an entry without a model, is a mistake
    for name in fact_registry.entity_names():
        shared = fact_registry.FACT_SPECS[name]["shared"]
        assert (name in fact_registry.shared_entities()) == shared
        assert all(p.startswith("Shared.") == shared for p in fact_registry.key_patterns_of(name)), name


def test_load_fact_returns_the_model_object_and_caches_it(bundle):
    bundle.write_fact("ReadmeForge.ApplicationOverview", _overview())
    cache = {}
    fact = load_fact("ReadmeForge", "ApplicationOverview", cache)
    assert fact.application_name == "ReadmeForge" and cache["ApplicationOverview"] is fact
    assert load_fact("ReadmeForge", "ApplicationOverview", cache) is fact


def test_load_fact_is_none_for_a_missing_fact_and_shared_facts_read_the_shared_scope(bundle):
    assert load_fact("ReadmeForge", "ApplicationOverview", {}) is None
    slo = json.loads(next((SAMPLES / "slo").glob("*.json")).read_text(encoding="utf-8"))
    bundle.write_fact("Shared.Slo", slo)
    assert load_fact("AnyApp", "Slo", {}) is not None
    assert build.fact_key("AnyApp", "Slo") == "Shared.Slo"


def test_load_fact_refuses_a_file_edited_outside_the_system(bundle):
    bundle.write_fact("ReadmeForge.ApplicationOverview", _overview())
    path = bundle.root / "ReadmeForge" / "ApplicationOverview.md"
    head, value = path.read_text(encoding="utf-8").split("# Value", 1)
    path.write_text(head + "# Value" + value.replace("ReadmeForge", "Hacked", 1), encoding="utf-8")
    with pytest.raises(BundleError):
        load_fact("ReadmeForge", "ApplicationOverview", {})


def test_generate_lists_the_applications_that_have_facts_in_the_bundle(bundle, capsys):
    bundle.write_fact("ReadmeForge.ApplicationOverview", _overview())
    assert main(["Nobody", "Overview", "--no-llm"]) == 1
    assert "applications with facts: ReadmeForge" in capsys.readouterr().out
    assert main(["ReadmeForge", "Overview", "--no-llm"]) == 0
