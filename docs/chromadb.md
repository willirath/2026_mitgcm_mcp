# ChromaDB semantic index

## Overview

The ChromaDB index stores vector embeddings for semantic search over MITgcm
source and documentation. It lives at `data/chroma/` (gitignored).

Three collections are maintained, each built by a separate pipeline:

| Collection | Pipeline | Content |
|---|---|---|
| `subroutines` | `pixi run embed` | `.F` / `.F90` subroutine source |
| `mitgcm_docs` | `pixi run embed-docs` | RST documentation + `.h` header files |
| `mitgcm_verification` | `pixi run embed-verification` | Verification experiment namelists and code |

All three share the same `data/chroma/` path and embedding model
(`nomic-embed-text` via Ollama).

## File type coverage

| File type | Location | Count | Indexed in | Notes |
|---|---|---|---|---|
| `.F` | `model/src/`, `pkg/*/` | ~2100 | `subroutines` | Full coverage |
| `.F90` | various | ~37 | `subroutines` | Full coverage |
| `.h` (experiment) | `verification/*/code/` | ~500 | `mitgcm_docs` | Experiment-level overrides |
| `.h` (model/inc) | `model/inc/` | 46 | `mitgcm_docs` | PARAMS.h, DYNVARS.h, GRID.h, … |
| `.h` (eesupp/inc) | `eesupp/inc/` | 16 | `mitgcm_docs` | EXCH.h, EEPARAMS.h, … |
| `.rst` | `doc/` | ~85 | `mitgcm_docs` | Full RST documentation |
| namelist (`data*`) | `verification/*/input/` | — | `mitgcm_verification` | Per-experiment physics config |
| `packages.conf` | `verification/*/code/` | — | `mitgcm_verification` | Package selection |
| `.py`, `.m`, `.c` | various | many | — | Build/analysis tools; not indexed |
| `.bin`, `.nc`, `.data` | various | many | — | Binary data; not indexed |

## Modules

### `store.py` — client setup

Defines `CHROMA_PATH` (`data/chroma/`) and `COLLECTION_NAME` (`subroutines`).
Exposes a single function:

```python
get_collection(path: Path = CHROMA_PATH) -> chromadb.Collection
```

Opens or creates a `PersistentClient` at `path` and returns the collection,
creating it with cosine similarity if it does not yet exist. The caller is
responsible for not holding the client across process boundaries.

### `pipeline.py` — embedding pipeline

Reads all subroutines from DuckDB, chunks them, embeds each chunk via ollama,
and upserts into ChromaDB.

Key constants:

| Constant | Value | Meaning |
|---|---|---|
| `EMBED_MODEL` | `nomic-embed-text` | ollama embedding model |
| `MAX_CHARS` | 4000 | maximum chars per chunk |
| `OVERLAP` | 200 | chars shared between adjacent chunks |
| `BATCH_SIZE` | 10 | chunks sent to ollama per request |

### Error handling

Each batch embed is wrapped in a two-level fallback:

1. **Retry once** after a 10-second pause — handles transient server errors.
   Observed cause: resource contention when concurrent MCP calls saturate
   the ollama container, causing spurious HTTP 400 "context length" rejections
   even for documents well within the 8192-token limit.
2. **One-at-a-time fallback** — if the retry also fails, each document in the
   batch is embedded individually, each with up to 3 attempts (10s apart).
   If a document fails all attempts with "input length exceeds context length",
   it is skipped with a warning and excluded from the upsert. All retries,
   fallbacks, and skips are logged to stdout.

Chunks that still exceed the context limit after the first retry are split
at the midpoint and both halves embedded separately (ids get `_a`/`_b` suffix).
Halves at ~2000 chars are reliably within the 2048-token window.

Progress is printed every 100 chunks.

## Chunking

`nomic-embed-text` has a context window of approximately 2000 tokens, which
corresponds to roughly 4000 characters of Fortran source. Many MITgcm
subroutines are larger than this — the largest exceeds 100 000 characters.

To avoid truncation, each subroutine is split into overlapping chunks:

```
_chunk_text(source_text, max_chars=4000, overlap=200)
```

Short subroutines (≤ 4000 chars) produce a single chunk. Longer ones produce
multiple chunks, each sharing 200 characters with its neighbours so that
content near a boundary is not missed by either chunk's embedding.

Each chunk is stored as a separate ChromaDB entry. The ChromaDB id is
`"{db_id}_{chunk_index}"`, e.g. `"42_0"`, `"42_1"`. All chunks carry the
same `db_id` metadata field for join-back to the DuckDB `subroutines` table.

## Document format

Every chunk document is prefixed with a header line:

```
SUBROUTINE <name> [<package>]
<chunk of source_text>
```

The header gives the embedding model context about what is being embedded,
anchoring the chunk to its subroutine name and package even when the source
text alone would be ambiguous.

## Metadata schema

Each ChromaDB entry carries:

| Field | Type | Content |
|---|---|---|
| `name` | str | subroutine name (uppercase) |
| `file` | str | path relative to project root |
| `package` | str | package name (`model`, `seaice`, …) |
| `db_id` | int | DuckDB `subroutines.id` for join-back |
| `chunk_index` | int | 0-based index within the subroutine |
| `n_chunks` | int | total chunks for this subroutine |

## Building the index

```sh
docker compose up -d                  # ollama must be running
pixi run embed
```

To rebuild from scratch:

```sh
rm -rf data/chroma
pixi run embed
```

The pipeline only needs to run once per MITgcm version. Because `data/chroma/`
is just a directory of files, it can be built on a more powerful host (e.g. a
GPU server with Ollama) and copied to the local machine for querying. The MCP
server itself does not need GPU access — it embeds only the user's search query
(one call per `search_code` invocation). See `plans/backlog.md` for the GPU
indexing path.

The DuckDB index must exist first (`pixi run index`). The embedder reads from
`data/index.duckdb` and writes to `data/chroma/`.

## Querying

```python
import ollama
from src.embedder.store import get_collection

collection = get_collection()

query = "non-hydrostatic pressure solve"
q_vec = ollama.embed(model="nomic-embed-text", input=[query])["embeddings"][0]

results = collection.query(
    query_embeddings=[q_vec],
    n_results=10,
    include=["metadatas", "distances", "documents"],
)

for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
    print(f"{dist:.3f}  {meta['name']}  [{meta['package']}]  chunk {meta['chunk_index']}/{meta['n_chunks']}")
```

Results may include multiple chunks from the same subroutine. Deduplicate by
`db_id` to get a ranked list of subroutines:

```python
seen = {}
for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
    db_id = meta["db_id"]
    if db_id not in seen or dist < seen[db_id][0]:
        seen[db_id] = (dist, meta["name"], meta["package"])

for dist, name, pkg in sorted(seen.values()):
    print(f"{dist:.3f}  {name}  [{pkg}]")
```

---

## `mitgcm_docs` collection

Built by `src/mitgcm/docs_indexer/` and populated with `pixi run embed-docs`.

### Content

Two sources are merged:

- **RST documentation** (`MITgcm/doc/**/*.rst`): parsed into sections (heading +
  body), RST markup stripped.
- **Header files** (`.h`): raw content from three locations:
  - `MITgcm/verification/*/code/*.h` — experiment-level header overrides
  - `MITgcm/model/inc/*.h` — core model headers (`PARAMS.h`, `DYNVARS.h`,
    `GRID.h`, `SIZE.h`, `CPP_OPTIONS.h`, etc.)
  - `MITgcm/eesupp/inc/*.h` — execution environment headers (`EXCH.h`,
    `EEPARAMS.h`, `CPP_EEOPTIONS.h`, etc.)

### Metadata schema

| Field | Type | Content |
|---|---|---|
| `file` | str | path relative to `MITgcm/` or the doc root |
| `section` | str | RST heading text, or filename for `.h` files |
| `chunk_index` | int | 0-based chunk index |
| `n_chunks` | int | total chunks for this section |
| `section_id` | str | stable id for join-back (`doc_N` or `hdr_N`) |

### Building

```sh
docker compose up -d
pixi run embed-docs
```

---

## `mitgcm_verification` collection

Built by `src/verification_indexer/` and populated with
`pixi run embed-verification`.

### Content

All text files under `MITgcm/verification/*/input/` and
`MITgcm/verification/*/code/`:

- **Namelists**: `input/data`, `input/data.pkg`, `input/data.*`, `input/eedata`
- **Headers and package config**: `code/*.h`, `code/packages.conf`
- **Source**: `code/*.F`, `code/*.F90`

Binary and generated files (`.bin`, `.nc`, `.data`, `.meta`, `.gz`) are skipped.

### Metadata schema

| Field | Type | Content |
|---|---|---|
| `experiment` | str | experiment directory name |
| `file` | str | `<experiment>/input/<name>` or `<experiment>/code/<name>` |
| `filename` | str | bare filename |
| `chunk_index` | int | 0-based chunk index |

### Building

```sh
docker compose up -d
pixi run embed-verification
```
