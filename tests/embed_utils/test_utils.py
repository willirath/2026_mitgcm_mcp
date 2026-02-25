"""Tests for _chunk_text in src/embed_utils.py.

All tests use synthetic strings — no DuckDB or ollama required.
"""

from src.embed_utils import OVERLAP, MAX_CHARS, _chunk_text


def test_short_text_returns_single_chunk():
    text = "A" * (MAX_CHARS - 1)
    chunks = _chunk_text(text, MAX_CHARS, OVERLAP)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_exact_max_chars_returns_single_chunk():
    text = "A" * MAX_CHARS
    chunks = _chunk_text(text, MAX_CHARS, OVERLAP)
    assert len(chunks) == 1


def test_long_text_splits_into_multiple_chunks():
    text = "A" * (MAX_CHARS * 2)
    chunks = _chunk_text(text, MAX_CHARS, OVERLAP)
    assert len(chunks) >= 2


def test_each_chunk_at_most_max_chars():
    text = "A" * (MAX_CHARS * 3 + 77)
    chunks = _chunk_text(text, MAX_CHARS, OVERLAP)
    assert all(len(c) <= MAX_CHARS for c in chunks)


def test_overlap_shared_between_adjacent_chunks():
    # Make text long enough to produce at least two full-length chunks.
    text = "A" * MAX_CHARS + "B" * MAX_CHARS
    chunks = _chunk_text(text, MAX_CHARS, OVERLAP)
    assert len(chunks) >= 2
    # The tail of chunk 0 equals the head of chunk 1.
    assert chunks[0][-OVERLAP:] == chunks[1][:OVERLAP]


def test_no_overlap_joins_to_original():
    # With overlap=0 the chunks partition the text exactly.
    text = "ABCDE" * 1000  # 5000 chars, longer than MAX_CHARS
    chunks = _chunk_text(text, MAX_CHARS, 0)
    assert "".join(chunks) == text


def test_empty_string_returns_one_empty_chunk():
    chunks = _chunk_text("", MAX_CHARS, OVERLAP)
    assert chunks == [""]


def test_all_positions_covered():
    # Every character position in the original text appears in at least one chunk.
    text = "X" * (MAX_CHARS * 2 + 317)
    chunks = _chunk_text(text, MAX_CHARS, OVERLAP)
    step = MAX_CHARS - OVERLAP
    covered = [False] * len(text)
    pos = 0
    for chunk in chunks:
        for j in range(len(chunk)):
            if pos + j < len(text):
                covered[pos + j] = True
        pos += step
    assert all(covered)
