"""FactContributions: what each DocStore file contributed to a fact (Phase 3 redesign, step 2)."""
from docfactory import contributions, db
from docfactory.canonical import sha256_hex

KEY = "Acme.FunctionalRequirements"


def test_a_contribution_round_trips_as_canonical_json(tmp_db):
    stored = contributions.save_contribution(KEY, "Acme/srs.pdf", {"summary": "S", "requirements": []}, "a" * 64, "One line.",
                                             "okf-extraction-agent/fake", "2026-10-04T10:00:00Z")
    assert stored.value_json == '{"requirements":[],"summary":"S"}'
    assert stored.hashcode == sha256_hex(stored.value_json)
    assert (stored.chunks_hash, stored.description, stored.generated_by) == ("a" * 64, "One line.", "okf-extraction-agent/fake")
    assert contributions.get_contribution(KEY, "Acme/srs.pdf") == stored


def test_saving_again_replaces_the_files_contribution(tmp_db):
    contributions.save_contribution(KEY, "Acme/srs.pdf", {"summary": "old"}, None, None, "x", "t1")
    contributions.save_contribution(KEY, "Acme/srs.pdf", {"summary": "new"}, None, None, "x", "t2")
    assert [c.value_json for c in contributions.list_contributions(KEY)] == ['{"summary":"new"}']


def test_list_by_key_or_resource_and_remove(tmp_db):
    contributions.save_contribution(KEY, "Acme/a.pdf", {"summary": "a"}, None, None, "x", "t")
    contributions.save_contribution(KEY, "Acme/b.pdf", {"summary": "b"}, None, None, "x", "t")
    contributions.save_contribution("Acme.Architecture", "Acme/a.pdf", {"notes": "n"}, None, None, "x", "t")
    assert [c.resource for c in contributions.list_contributions(KEY)] == ["Acme/a.pdf", "Acme/b.pdf"]
    assert [c.fact_key for c in contributions.list_contributions(resource="Acme/a.pdf")] == ["Acme.Architecture", KEY]
    contributions.remove_contribution(KEY, "Acme/a.pdf")
    assert contributions.get_contribution(KEY, "Acme/a.pdf") is None
    assert len(db.list_contributions()) == 2
