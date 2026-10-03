"""Rule tagging of chunks against the ontology and the deterministic scope decision (Phase 2 redesign, step 3)."""
import hashlib
from pathlib import Path

import pytest

from docfactory.ingest.chunking import assemble_chunks, chunk_file
from docfactory.ingest.scope_rules import clean_title, decide_scope, folder_name, shared_entities
from docfactory.ingest.tagging import ORIGIN, entity_map, tag_chunk, tag_chunks
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.doc_chunk import DocChunk
from docfactory.ontology.signals import load_signals

CORPUS = Path(__file__).parent / "corpus" / "incoming"


@pytest.fixture(scope="module")
def signals():
    return load_signals()


def chunk(heading, text, no=1):
    return DocChunk(chunk_no=no, heading=heading, text=text, text_hash=hashlib.sha256(text.encode()).hexdigest())


def entities(tags):
    return [t.entity for t in tags]


# --- tagging -----------------------------------------------------------------------------------------------------------------

def test_own_heading_and_identifiers_tag_with_evidence(signals):
    tags = tag_chunk(chunk("3. Features > 3.1. Accounts", "FR-01. | The system SHALL x.\nFR-02. | The system SHALL y."), signals)
    assert entities(tags) == ["FunctionalRequirements"]
    tag = tags[0]
    assert tag.origin == ORIGIN and tag.score >= 7 and "FR-01..FR-02 (2)" in tag.evidence


def test_a_parent_heading_is_inherited_by_sub_sections(signals):
    tags = tag_chunk(chunk("5. Non-Functional Requirements > 5.1. Response Time", "Pages load in 2 seconds."), signals)
    assert entities(tags) == ["NonFunctionalRequirements"] and "parent heading" in tags[0].evidence


def test_the_longest_heading_term_wins_non_functional_is_not_functional(signals):
    tags = tag_chunk(chunk("5. Non-Functional Requirements", "Quality targets follow."), signals)
    assert entities(tags) == ["NonFunctionalRequirements"]


def test_a_heading_term_matches_its_plural(signals):
    tags = tag_chunk(chunk("5.6. Legal > 5.6.3. Service Level Agreements", "Uptime is agreed with MoL."), signals)
    assert "Slo" in entities(tags)


def test_a_chunk_can_carry_several_entities(signals):
    tags = tag_chunk(chunk("5. Non-Functional Requirements > 5.7.2. Backup and Recovery", "Daily backups; RPO 24 hours, RTO 4 hours."), signals)
    assert set(entities(tags)) == {"NonFunctionalRequirements", "BackupRecovery"}


def test_keywords_alone_never_tag(signals):
    text = "The database, the api and the cloud integration framework."  # many Architecture keywords, no heading or id
    assert tag_chunk(chunk("6.5. Appendix B: Issues List", text), signals) == []


def test_ids_do_not_cross_match(signals):
    assert entities(tag_chunk(chunk("Annex", "NFR-12. | Pages load fast."), signals)) == ["NonFunctionalRequirements"]


def test_tag_chunks_reports_unmapped_and_entity_map_lists_chunks(signals):
    chunks = [chunk("3. Functional Requirements", "FR-01. | x", 1), chunk("4. User Interfaces", "Screens.", 2),
              chunk("3. Functional Requirements > 3.2. Jobs", "FR-02. | y", 3)]
    tags, unmapped = tag_chunks(chunks, signals)
    assert unmapped == [2]
    assert entity_map(tags) == {"FunctionalRequirements": [1, 3]}


def test_tagging_is_deterministic(signals):
    chunks = chunk_file(CORPUS / "readmeforge-runbooks.html")
    assert tag_chunks(chunks, signals) == tag_chunks(chunks, signals)


# --- scope -------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("title, name, removed", [
    ("Software Requirements Specification for AI- Driven Job Matching Platform", "AI-Driven Job Matching Platform", True),
    ("ReadmeForge - Requirements (working draft 0.3)", "ReadmeForge", True),
    ("ReadmeForge on-call runbooks", "ReadmeForge", True),
    ("ReadmeForge - How we run it", "ReadmeForge", True),
    ("Platform Reliability Standards 2026", "Platform Reliability Standards 2026", False),
])
def test_clean_title_removes_document_type_wording(title, name, removed):
    assert clean_title(title) == (name, removed)


def test_folder_names_are_legal():
    assert folder_name("AI-Driven Job Matching Platform") == "AI-Driven-Job-Matching-Platform"
    assert folder_name("  Acme: Jobs / Portal ") == "Acme-Jobs-Portal"


def test_shared_entities_are_the_shared_only_savers():
    assert shared_entities() == {"Kpis", "Slo"}


def _front(*lines):
    return assemble_chunks([("text", line, 1) for line in lines] + [("heading", 1, "1. Introduction", 2), ("text", "Body.", 2)])


def test_a_document_control_title_row_is_confident():
    chunks = _front("Software Requirements Specification (SRS)", "Title | Software Requirements Specification for AI- Driven Job Matching Platform")
    scope, confident, reason = decide_scope(chunks, [], [])
    assert (scope, confident) == ("AI-Driven-Job-Matching-Platform", True) and "document control row" in reason


def test_an_existing_folder_is_reused():
    chunks = _front("ReadmeForge on-call runbooks")
    assert decide_scope(chunks, [], ["ReadmeForge", "shared"])[:2] == ("ReadmeForge", True)


def test_only_shared_entity_tags_mean_shared():
    tags = [ChunkTag(chunk_no=2, entity="Slo", origin="rule")]
    assert decide_scope(_front("Platform Reliability Standards 2026"), tags, ["ReadmeForge"])[:2] == ("shared", True)


def test_a_plain_title_is_unconfident_and_no_title_is_none():
    scope, confident, _ = decide_scope(_front("Platform Reliability Standards 2026"), [], [])
    assert (scope, confident) == ("Platform-Reliability-Standards-2026", False)
    assert decide_scope([], [], []) == (None, False, "no title found")


def test_a_title_styled_as_a_heading_is_kept_as_front_matter():
    chunks = chunk_file(CORPUS / "ReadmeForge_SystemMgmt.docx")
    assert chunks[0].heading == "Front matter" and chunks[0].text == "ReadmeForge - How we run it"
    assert decide_scope(chunks, [], [])[:2] == ("ReadmeForge", True)
