"""Key pattern -> entity saver resolution (Phase 3b)."""
import json
from pathlib import Path

import pytest

from docfactory import saver_resolution
from docfactory.base_saver import BaseSaver
from docfactory.saver_resolution import entity_saver_classes, ordered_value, saver_for_key

ENTITYSAVER = Path(saver_resolution.__file__).parent / "entitysaver"
SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_every_entity_saver_module_is_found():
    modules = sorted(p.stem for p in ENTITYSAVER.glob("*_saver.py"))
    found = sorted(cls.__module__.rsplit(".", 1)[-1] for cls in entity_saver_classes())
    assert found == modules and len(found) == 13
    assert all(issubclass(cls, BaseSaver) for cls in entity_saver_classes())


def _example(pattern: str) -> str:
    return pattern.replace("{app}", "ReadmeForge").replace("{component}", "api server")


def test_every_key_pattern_resolves_to_exactly_its_own_saver():
    for cls in entity_saver_classes():
        for pattern in cls.key_patterns:
            saver = saver_for_key(_example(pattern))
            assert type(saver) is cls, (pattern, saver)


def test_no_two_savers_share_a_key_pattern():
    patterns = [p for cls in entity_saver_classes() for p in cls.key_patterns]
    assert len(patterns) == len(set(patterns))


@pytest.mark.parametrize("key", ["Shared.Architecture", "ReadmeForge.Nothing", "ReadmeForge", "", "ReadmeForge.Components.Architecture"])
def test_a_key_no_saver_accepts_resolves_to_none(key):
    assert saver_for_key(key) is None


def test_two_matching_savers_are_a_configuration_error(monkeypatch):
    from docfactory.entitysaver.architecture_saver import ArchitectureSaver

    class Twin(ArchitectureSaver):
        pass

    monkeypatch.setattr(saver_resolution, "entity_saver_classes", lambda: [ArchitectureSaver, Twin])
    with pytest.raises(RuntimeError, match="more than one saver"):
        saver_for_key("ReadmeForge.Architecture")


def test_ordered_value_follows_the_model_field_order_not_the_sorted_json():
    stored = json.dumps(json.loads((SAMPLES / "functional_requirements" / "readmeforge_full.json").read_text(encoding="utf-8")), sort_keys=True)
    assert list(json.loads(stored))[0] == "out_of_scope"  # canonical JSON is sorted
    ordered = json.loads(ordered_value("ReadmeForge.FunctionalRequirements", stored))
    assert list(ordered)[:2] == ["summary", "requirements"]
    assert list(ordered["requirements"][0])[:3] == ["id", "title", "description"]
    assert ordered_value("Unknown.Key", stored) == stored
