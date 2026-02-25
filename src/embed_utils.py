"""Shared embedding utilities: chunking constants and the _chunk_text helper.

Used by both MITgcm and FESOM2 embedding pipelines.
"""

EMBED_MODEL = "nomic-embed-text"
BATCH_SIZE = 10
# nomic-embed-text context window is ~2000 tokens; ~4000 chars of Fortran code
# fits safely within that budget.
MAX_CHARS = 4000
# Overlap between consecutive chunks so that content near a boundary
# appears in two chunks and is not lost to either.
OVERLAP = 200


def _chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks of at most max_chars characters each.

    Short texts (len <= max_chars) are returned as a single-element list.
    Each chunk after the first starts overlap characters before the end of
    the previous chunk.
    """
    if len(text) <= max_chars:
        return [text]
    step = max_chars - overlap
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + max_chars])
        start += step
    return chunks
