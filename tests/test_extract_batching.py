"""Batching an entity's chunks for the extraction calls (Phase 3 redesign, step 1)."""
from docfactory.extract.batching import batch_chunks, batch_text, chunks_hash
from docfactory.models.doc_chunk import DocChunk


def chunk(no, size, heading="3. Features"):
    return DocChunk(chunk_no=no, heading=heading, text="x" * size, text_hash="0" * 64)


def test_chunks_are_packed_in_order_within_the_budget():
    batches = batch_chunks([chunk(3, 400), chunk(1, 500), chunk(2, 300)], budget=1000)
    assert [[c.chunk_no for c in b] for b in batches] == [[1, 2], [3]]


def test_an_oversized_chunk_is_a_batch_of_its_own_and_never_split():
    batches = batch_chunks([chunk(1, 100), chunk(2, 5000), chunk(3, 100)], budget=1000)
    assert [[c.chunk_no for c in b] for b in batches] == [[1], [2], [3]]
    assert len(batches[1][0].text) == 5000


def test_no_chunks_give_no_batches():
    assert batch_chunks([]) == []


def test_batch_text_names_each_chunk_with_its_heading_trail():
    text = batch_text([DocChunk(chunk_no=7, heading="3. F > 3.1. Login", text="FR-01. | The system SHALL ...", text_hash="0" * 64)])
    assert text == "[chunk 7] 3. F > 3.1. Login\nFR-01. | The system SHALL ..."


def test_chunks_hash_ignores_order_and_changes_with_the_text():
    a, b = chunk(1, 10), chunk(2, 20)
    assert chunks_hash([a, b]) == chunks_hash([b, a])
    assert chunks_hash([a, b]) != chunks_hash([a, chunk(2, 21)])
    assert chunks_hash([a]) != chunks_hash([chunk(1, 10, heading="4. Other")])
