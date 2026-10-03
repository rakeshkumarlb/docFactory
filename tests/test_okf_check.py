"""The bundle conformance checker and the rebuild command."""
import pytest

from docfactory import bundle, bundle_rebuild, db, okf_check
from docfactory.entitysaver.kpis_saver import KpisSaver
from docfactory.models.fact_meta import FactMeta

pytest.importorskip("yaml")


def _write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_a_conformant_bundle_has_no_problems(tmp_path):
    _write(tmp_path, "a/Concept.md", "---\ntype: Metric\n---\n\n# T\n\n[other](/a/Other.md) [web](https://x.org) [top](#t)\n")
    _write(tmp_path, "index.md", "---\nokf_version: \"0.2\"\n---\n\n# Index\n")
    _write(tmp_path, "log.md", "# Directory Update Log\n")
    assert okf_check.check_bundle(tmp_path) == []


@pytest.mark.parametrize("text,fragment", [
    ("# no frontmatter\n", "no YAML frontmatter block"),
    ("---\ntitle: x\n---\n\nbody\n", "no non-empty `type`"),
    ("---\ntype: \"  \"\n---\n\nbody\n", "no non-empty `type`"),
    ("---\ntype: [unclosed\n---\n\nbody\n", "not valid YAML"),
    ("---\n- a\n- b\n---\n\nbody\n", "not a mapping"),
    ("---\ntype: X\n---\n\n[rel](other.md)\n", "neither bundle-relative"),
])
def test_each_violation_is_reported_with_the_file(tmp_path, text, fragment):
    _write(tmp_path, "Bad.md", text)
    problems = okf_check.check_bundle(tmp_path)
    assert len(problems) == 1 and problems[0].startswith("Bad.md:") and fragment in problems[0]


def test_index_may_only_carry_okf_version(tmp_path):
    _write(tmp_path, "index.md", "---\ntype: X\n---\n\n# Index\n")
    assert "index.md may only carry okf_version" in okf_check.check_bundle(tmp_path)[0]


def test_main_exit_codes(tmp_path, capsys):
    assert okf_check.main([str(tmp_path / "missing")]) == 1
    _write(tmp_path, "Ok.md", "---\ntype: X\n---\n")
    assert okf_check.main([str(tmp_path)]) == 0
    _write(tmp_path, "Bad.md", "no frontmatter")
    assert okf_check.main([str(tmp_path)]) == 1 and "Bad.md" in capsys.readouterr().out


def test_every_saved_fact_file_is_conformant(tmp_db):
    import json
    from pathlib import Path
    from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
    samples = Path(__file__).resolve().parents[1] / "samples"
    meta = FactMeta(generated_by="seed", description="One sentence.", tags=["t"])
    ApplicationOverviewSaver().save("ReadmeForge.ApplicationOverview",
                                    json.loads((samples / "application_overview" / "readmeforge_full.json").read_text(encoding="utf-8")), meta=meta)
    KpisSaver().save("Shared.Kpis", json.loads((samples / "kpis" / "shared_devex_kpis_full.json").read_text(encoding="utf-8")), meta=meta)
    assert okf_check.check_bundle(bundle.bundles_root()) == []
    assert {p.name for p in bundle.bundles_root().rglob("*.md")} == {"ApplicationOverview.md", "Kpis.md"}


def test_rebuild_restores_deleted_files_and_skips_facts_without_frontmatter(tmp_db):
    import json
    from pathlib import Path
    sample = json.loads((Path(__file__).resolve().parents[1] / "samples" / "kpis" / "shared_devex_kpis_minimal.json").read_text(encoding="utf-8"))
    KpisSaver().save("Shared.Kpis", sample, meta=FactMeta(generated_by="seed"))
    db.write_row("KnowledgeFacts", "Old.Fact", "{}", "h", "Old", 0.0, 1)
    (bundle.bundles_root() / "Shared" / "Kpis.md").unlink()
    assert bundle_rebuild.rebuild() == (1, 0, ["Old.Fact"])
    assert bundle_rebuild.rebuild() == (0, 1, ["Old.Fact"])
    assert okf_check.check_bundle(bundle.bundles_root()) == []
