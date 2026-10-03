from pathlib import Path

from docx import Document

from docfactory.ingest.text_extraction import file_text, is_text_file, sidecar_path

CORPUS = Path(__file__).parent / "corpus" / "incoming"


def test_text_files_are_read_as_is(tmp_path):
    path = tmp_path / "n.txt"
    path.write_text("hello\n- x\n", encoding="utf-8")
    assert is_text_file(path) and file_text(path) == "hello\n- x\n"


def test_word_keeps_headings_and_tables():
    md = file_text(CORPUS / "ReadmeForge_SystemMgmt.docx")
    assert "# Where it lives" in md and "| dev | Developer testing |" in md


def test_html_keeps_headings_and_lists():
    md = file_text(CORPUS / "readmeforge-runbooks.html")
    assert "## API 5xx spike" in md and "1. Acknowledge the PagerDuty incident" in md


def test_pdf_text_is_extracted():
    assert "Requirements" in file_text(CORPUS / "ReadmeForge SRS v0.3.pdf")


def test_sidecar_sits_next_to_the_original():
    assert sidecar_path(Path("DocStore/App/a.pdf")) == Path("DocStore/App/a.pdf.md")
