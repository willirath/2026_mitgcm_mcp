"""Tests for _doc_chunks in src/mitgcm_embedder/pipeline.py.

_chunk_text tests live in tests/embed_utils/test_utils.py.
All tests use synthetic strings — no DuckDB or ollama required.
"""

from src.embed_utils import MAX_CHARS, OVERLAP
from src.mitgcm.embedder.pipeline import _doc_chunks


# ---------------------------------------------------------------------------
# _doc_chunks
# ---------------------------------------------------------------------------

def test_short_subroutine_one_entry():
    entries = _doc_chunks(1, "SHORT", "model/src/short.F", "model", "X" * 100)
    assert len(entries) == 1
    assert entries[0][2]["n_chunks"] == 1


def test_long_subroutine_multiple_entries():
    entries = _doc_chunks(7, "LONG", "pkg/foo/long.F", "foo", "X" * (MAX_CHARS * 3))
    assert len(entries) >= 3


def test_chunk_ids_are_unique():
    entries = _doc_chunks(42, "BIG", "pkg/bar/big.F", "bar", "X" * (MAX_CHARS * 3))
    ids = [e[0] for e in entries]
    assert len(ids) == len(set(ids))


def test_chunk_ids_include_db_id():
    entries = _doc_chunks(99, "SUB", "model/src/sub.F", "model", "X" * (MAX_CHARS * 2))
    assert all(e[0].startswith("99_") for e in entries)


def test_all_chunks_carry_same_db_id():
    entries = _doc_chunks(42, "BIG", "pkg/bar/big.F", "bar", "X" * (MAX_CHARS * 3))
    assert all(e[2]["db_id"] == 42 for e in entries)


def test_chunk_index_is_sequential():
    entries = _doc_chunks(5, "SUB", "pkg/x/s.F", "x", "X" * (MAX_CHARS * 3))
    indices = [e[2]["chunk_index"] for e in entries]
    assert indices == list(range(len(entries)))


def test_n_chunks_consistent():
    entries = _doc_chunks(5, "SUB", "pkg/x/s.F", "x", "X" * (MAX_CHARS * 3))
    n = len(entries)
    assert all(e[2]["n_chunks"] == n for e in entries)


def test_doc_text_contains_subroutine_header():
    entries = _doc_chunks(1, "CG3D", "model/src/cg3d.F", "model", "X" * 100)
    assert entries[0][1].startswith("SUBROUTINE CG3D [model]")


def test_header_present_in_every_chunk():
    entries = _doc_chunks(3, "MYSUB", "pkg/p/s.F", "p", "X" * (MAX_CHARS * 3))
    assert all("SUBROUTINE MYSUB [p]" in e[1] for e in entries)
