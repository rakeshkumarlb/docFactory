"""Deterministic chunking of originals (Phase 2 redesign, step 2): the assembler and the PDF, Word, HTML and text readers."""
import hashlib
from pathlib import Path

import pytest

from docfactory.ingest.chunking import FRONT_MATTER, assemble_chunks, chunk_file

CORPUS = Path(__file__).parent / "corpus" / "incoming"


# --- the assembler ------------------------------------------------------------------------------------------------------------

def test_sections_get_their_heading_trail_and_text_before_the_first_heading_is_front_matter():
    chunks = assemble_chunks([
        ("text", "Cover title", 1),
        ("heading", 1, "3. Features", 2),
        ("text", "Intro to features.", 2),
        ("heading", 2, "3.1. Accounts", 2),
        ("text", "Accounts text.", 3),
        ("heading", 3, "3.1.1. Sign up", 3),
        ("text", "Sign up text.", 3),
        ("heading", 2, "3.2. Jobs", 4),
        ("text", "Jobs text.", 4),
    ])
    assert [c.heading for c in chunks] == [FRONT_MATTER, "3. Features", "3. Features > 3.1. Accounts",
                                           "3. Features > 3.1. Accounts > 3.1.1. Sign up", "3. Features > 3.2. Jobs"]
    assert [c.chunk_no for c in chunks] == [1, 2, 3, 4, 5]
    assert (chunks[2].page_from, chunks[2].page_to) == (3, 3)


def test_a_heading_without_body_makes_no_chunk_but_stays_in_the_trail():
    chunks = assemble_chunks([("heading", 1, "1. A", None), ("heading", 2, "1.1. B", None), ("text", "body", None)])
    assert [c.heading for c in chunks] == ["1. A > 1.1. B"]


def test_a_repeated_table_header_is_kept_once_per_section():
    chunks = assemble_chunks([
        ("heading", 1, "1. Reqs", 1),
        ("header", "ID | Requirement", 1), ("row", "FR-01. | The system SHALL a.", 1),
        ("header", "ID | Requirement", 2), ("row", "FR-02. | The system SHALL b.", 2),
        ("heading", 1, "2. More", 3),
        ("header", "ID | Requirement", 3), ("row", "FR-03. | The system SHALL c.", 3),
    ])
    assert chunks[0].text == "ID | Requirement\nFR-01. | The system SHALL a.\nFR-02. | The system SHALL b."
    assert (chunks[0].page_from, chunks[0].page_to) == (1, 2)
    assert chunks[1].text.startswith("ID | Requirement\nFR-03.")


def test_a_long_section_is_split_at_element_boundaries_into_numbered_parts():
    rows = [("row", f"FR-{n:02}. | " + "x" * 90, 1) for n in range(1, 31)]
    chunks = assemble_chunks([("heading", 1, "3. Reqs", 1), *rows], max_chars=1000)
    assert len(chunks) > 1 and all(len(c.text) <= 1000 for c in chunks)
    assert [c.heading for c in chunks] == [f"3. Reqs (part {i})" for i in range(1, len(chunks) + 1)]
    assert "\n".join(c.text for c in chunks) == "\n".join(r[1] for r in rows)  # nothing lost, no row split


def test_a_document_without_headings_is_cut_smaller():
    chunks = assemble_chunks([("text", "y" * 900, None) for _ in range(4)])
    assert len(chunks) == 4 and chunks[0].heading == f"{FRONT_MATTER} (part 1)"


def test_whitespace_is_normalised_empty_text_dropped_and_the_hash_is_the_sha256_of_the_text():
    chunk = assemble_chunks([("heading", 1, "1. A", None), ("text", "  two   words \n", None), ("text", "   ", None)])[0]
    assert chunk.text == "two words"
    assert chunk.text_hash == hashlib.sha256(b"two words").hexdigest()


def test_same_elements_give_the_same_chunks():
    elements = [("heading", 1, "1. A", 1), ("text", "body", 1)]
    assert assemble_chunks(elements) == assemble_chunks(elements)


def test_no_text_gives_no_chunks_and_an_unknown_type_is_refused(tmp_path):
    assert assemble_chunks([]) == []
    with pytest.raises(ValueError, match="no chunker"):
        chunk_file(tmp_path / "picture.png")


# --- PDF ----------------------------------------------------------------------------------------------------------------------

def _srs_like_pdf(path: Path) -> None:
    """A small SRS-shaped PDF: cover title, a TOC line, 12pt numbered headings, 11pt body, a requirements table split over two
    pages with its header row repeated, and page numbers."""
    reportlab = pytest.importorskip("reportlab")  # noqa: F841 - dev-only dependency
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

    body = ParagraphStyle("body", fontName="Helvetica", fontSize=11, leading=14)
    heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=12, leading=16, spaceBefore=8)
    title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=16, leading=20)
    toc = ParagraphStyle("toc", fontName="Helvetica", fontSize=8, leading=10)
    grid = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)])

    def table(rows):
        t = Table([["ID", "Requirement"], *rows], colWidths=[60, 380])
        t.setStyle(grid)
        return t

    story = [
        Paragraph("Software Requirements Specification", title),
        Paragraph("Acme Job Board", body),
        Paragraph("1. Introduction " + "." * 40 + " 2", toc),
        PageBreak(),
        Paragraph("1. Introduction", heading),
        Paragraph("1.1. Purpose", heading),
        Paragraph("This document describes the Acme Job Board.", body),
        Paragraph("3. Functional Requirements", heading),
        Paragraph("3.1. Accounts", heading),
        table([["FR-01.", "The system SHALL let job seekers register."], ["FR-02.", "The system SHALL verify email addresses."]]),
        PageBreak(),
        table([["FR-03.", "The system SHALL let employers post jobs."]]),
    ]

    def number(canvas, doc):
        canvas.setFont("Helvetica", 11)
        canvas.drawString(290, 30, str(doc.page))

    SimpleDocTemplate(str(path), pagesize=A4).build(story, onFirstPage=number, onLaterPages=number)


def test_pdf_headings_tables_and_noise(tmp_path):
    path = tmp_path / "srs.pdf"
    _srs_like_pdf(path)
    chunks = chunk_file(path)
    by_heading = {c.heading: c for c in chunks}
    assert list(by_heading) == [FRONT_MATTER, "1. Introduction > 1.1. Purpose", "3. Functional Requirements > 3.1. Accounts"]
    front = by_heading[FRONT_MATTER].text
    assert "Software Requirements Specification" in front and "Acme Job Board" in front  # the cover title stays text
    assert "....." not in front  # table-of-contents line dropped
    accounts = by_heading["3. Functional Requirements > 3.1. Accounts"]
    assert accounts.text.splitlines() == [
        "ID | Requirement",
        "FR-01. | The system SHALL let job seekers register.",
        "FR-02. | The system SHALL verify email addresses.",
        "FR-03. | The system SHALL let employers post jobs.",
    ]  # identifier and statement in one row; header kept once across the page break; no page numbers
    assert (accounts.page_from, accounts.page_to) == (2, 3)


def test_the_corpus_srs_pdf_is_chunked_by_its_numbered_headings():
    chunks = chunk_file(CORPUS / "ReadmeForge SRS v0.3.pdf")
    assert [c.heading for c in chunks][:3] == [FRONT_MATTER, "0. About this paper", "1. What it has to do"]
    assert "1.1 Whenever somebody pushes" in chunks[2].text  # numbered body lines in 11pt are text, not headings


# --- Word, HTML, text ---------------------------------------------------------------------------------------------------------

def test_word_heading_styles_and_tables():
    chunks = chunk_file(CORPUS / "ReadmeForge_SystemMgmt.docx")
    environments = next(c for c in chunks if c.heading.endswith("Environments"))
    assert environments.text.splitlines()[:2] == ["Env | Purpose | Notes", "dev | Developer testing | Single replica, shared Postgres"]
    assert all(c.page_from is None for c in chunks)


def test_html_heading_levels_build_the_trail():
    chunks = chunk_file(CORPUS / "readmeforge-runbooks.html")
    assert chunks[0].heading == "ReadmeForge on-call runbooks"
    assert chunks[1].heading.startswith("ReadmeForge on-call runbooks > API 5xx spike")
    assert "Acknowledge the PagerDuty incident" in chunks[1].text


def test_html_does_not_read_nested_blocks_twice(tmp_path):
    path = tmp_path / "page.html"
    path.write_text("<h1>T</h1><ul><li><p>Only once</p></li></ul><table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>",
                    encoding="utf-8")
    assert chunk_file(path)[0].text == "Only once\nA | B\n1 | 2"


def test_markdown_and_numbered_text(tmp_path):
    path = tmp_path / "doc.md"
    path.write_text("# Title\nIntro line one\nline two\n\n## 2 Tables\n| ID | Text |\n|---|---|\n| FR-1 | Do it |\n\n2.1 Details\nMore.\n",
                    encoding="utf-8")
    chunks = chunk_file(path)
    assert [c.heading for c in chunks] == ["Title", "Title > 2 Tables", "Title > 2.1. Details"]  # '##' and '2.1' are both level 2
    assert chunks[0].text == "Intro line one line two"
    assert chunks[1].text == "ID | Text\nFR-1 | Do it"


def test_unstructured_notes_are_front_matter():
    chunks = chunk_file(CORPUS / "notes.txt")
    assert len(chunks) == 1 and chunks[0].heading == FRONT_MATTER
