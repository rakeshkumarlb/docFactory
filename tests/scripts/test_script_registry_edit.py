import pytest

import registry_edit

REGISTRY = """from docfactory.entitymodels.facts.alpha import Alpha
from docfactory.entitymodels.facts.gamma import Gamma
from docfactory.key_patterns import pattern_matches

FACT_SPECS = {
    "Alpha": {"model": Alpha, "shared": False},
    "Gamma": {"model": Gamma, "shared": True},
}
"""


def test_registered_lists_the_entities_of_fact_specs():
    assert registry_edit.registered(REGISTRY) == {"Alpha", "Gamma"}
    assert registry_edit.registered("FACT_SPECS = {\n}\n") == set()
    assert registry_edit.registered("x = 1\n") == set()


def test_add_entry_imports_in_order_and_adds_the_spec():
    text = registry_edit.add_entry(REGISTRY, "Beta", "docfactory.entitymodels.facts.beta", shared=False)
    lines = text.split("\n")
    assert lines.index("from docfactory.entitymodels.facts.alpha import Alpha") < lines.index("from docfactory.entitymodels.facts.beta import Beta") < lines.index("from docfactory.entitymodels.facts.gamma import Gamma")
    assert '    "Beta": {"model": Beta, "shared": False},' in lines
    assert registry_edit.registered(text) == {"Alpha", "Beta", "Gamma"}
    compile(text.replace("from docfactory", "#"), "registry", "exec")


def test_a_shared_fact_is_flagged_shared_and_a_last_name_sorts_after_the_rest():
    text = registry_edit.add_entry(REGISTRY, "Zeta", "docfactory.entitymodels.facts.zeta", shared=True)
    assert '"Zeta": {"model": Zeta, "shared": True},' in text
    assert text.split("\n").index("from docfactory.entitymodels.facts.zeta import Zeta") > text.split("\n").index("from docfactory.entitymodels.facts.gamma import Gamma")


def test_the_first_fact_goes_after_the_other_imports():
    text = registry_edit.add_entry("from docfactory.key_patterns import pattern_matches\n\nFACT_SPECS = {\n}\n", "Alpha", "docfactory.entitymodels.facts.alpha", False)
    assert text.startswith("from docfactory.key_patterns import pattern_matches\nfrom docfactory.entitymodels.facts.alpha import Alpha\n")


def test_refusals():
    with pytest.raises(ValueError, match="already registered"):
        registry_edit.add_entry(REGISTRY, "Alpha", "docfactory.entitymodels.facts.alpha", False)
    with pytest.raises(ValueError, match="no FACT_SPECS"):
        registry_edit.add_entry("x = 1\n", "Beta", "m", False)
