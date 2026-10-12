"""Recognition windows: whole sections in document order within a word budget; a long section takes windows of its own."""
import hashlib

from docfactory.models.doc_chunk import DocChunk
from docfactory.recognize.windows import DEFAULT_WORD_CAP, WORD_CAP_ENV, build_windows, outline_text, section_of, window_hash, word_cap, words


def chunk(no, heading, n_words):
    text = " ".join(["word"] * n_words)
    return DocChunk(chunk_no=no, heading=heading, text=text, text_hash=hashlib.sha256(text.encode()).hexdigest())


def numbers(windows):
    return [[c.chunk_no for c in w] for w in windows]


def test_the_cap_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv(WORD_CAP_ENV, raising=False)
    assert word_cap() == DEFAULT_WORD_CAP
    monkeypatch.setenv(WORD_CAP_ENV, "500")
    assert word_cap() == 500


def test_words_counts_heading_and_text():
    assert words(chunk(1, "A > B", 10)) == 13


def test_parts_belong_to_their_section():
    assert section_of(chunk(1, "3. Ops > 3.1 Backup (part 2)", 1)) == "3. Ops > 3.1 Backup"


def test_sections_are_packed_in_order_until_the_cap():
    chunks = [chunk(1, "A", 299), chunk(2, "B", 299), chunk(3, "C", 299), chunk(4, "D", 299)]
    assert numbers(build_windows(chunks, cap=1000)) == [[1, 2, 3], [4]]


def test_a_section_is_never_split_while_it_fits_a_window():
    chunks = [chunk(1, "A", 499), chunk(2, "B", 299), chunk(3, "B (part 2)", 299)]
    assert numbers(build_windows(chunks, cap=1000)) == [[1], [2, 3]]


def test_a_section_over_the_cap_gets_windows_of_its_own():
    chunks = [chunk(1, "A", 99), chunk(2, "Big", 599), chunk(3, "Big (part 2)", 599), chunk(4, "Big (part 3)", 99), chunk(5, "C", 99)]
    assert numbers(build_windows(chunks, cap=1000)) == [[1], [2], [3, 4], [5]]


def test_a_single_chunk_over_the_cap_is_a_window_alone():
    assert numbers(build_windows([chunk(1, "A", 50), chunk(2, "Huge", 5000), chunk(3, "C", 50)], cap=1000)) == [[1], [2], [3]]


def test_windows_are_deterministic_and_order_independent():
    chunks = [chunk(n, f"S{n}", 300) for n in range(1, 8)]
    assert numbers(build_windows(chunks, cap=1000)) == numbers(build_windows(list(reversed(chunks)), cap=1000))


def test_the_window_hash_changes_with_the_text():
    a, b = [chunk(1, "A", 5)], [chunk(1, "A", 6)]
    assert window_hash(a) == window_hash([chunk(1, "A", 5)]) != window_hash(b)


def test_the_outline_lists_each_section_once():
    chunks = [chunk(1, "A", 1), chunk(2, "B", 1), chunk(3, "B (part 2)", 1)]
    assert outline_text(chunks) == "- A\n- B"
