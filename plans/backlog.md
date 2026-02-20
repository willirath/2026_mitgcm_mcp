# Backlog

Known limitations and deferred improvements, in no particular priority order.

---

## CPP guard attribution is per-subroutine, not per-line

**Where**: `src/indexer/extract.py`, `cpp_guards` table

**Problem**: The extractor attributes every `#ifdef` / `#ifndef` found anywhere
in a subroutine to the subroutine as a whole. For large routines like
`INI_PARMS` (~1500 lines), this produces many unrelated flags —
`SHORTWAVE_HEATING`, `ALLOW_EXCH2`, etc. — none of which guard the specific
line being queried.

**Observed via**: `get_cpp_requirements_tool("INI_PARMS")` after asking which
CPP flag guards the reading of `cg3dMaxIters`. The flags returned are
technically present in the subroutine but irrelevant to that parameter.

**Fix**: Track the active `#ifdef` stack at each line and store
`(subroutine_id, cpp_flag, line_start, line_end)` rather than just
`(subroutine_id, cpp_flag)`. `get_cpp_requirements` could then accept an
optional line range to filter to guards that actually wrap the target code.
This is a meaningful scope increase — the regex extractor would need to
maintain a CPP nesting stack across lines.

---

## INI_PARMS conflates "reads from namelist" with "uses the parameter"

**Where**: `namelist_refs` table, `namelist_to_code` tool

**Problem**: `INI_PARMS` reads every namelist parameter in MITgcm into COMMON
blocks. A query for `cg3dMaxIters` correctly returns `INI_PARMS` (it appears
in a `&PARM02` block there), but the semantically useful answer is often
`CG3D` — the subroutine that *uses* the parameter.

**Fix**: No schema change needed. Callers should be aware that
`namelist_to_code` finds declaration sites, not use sites. A follow-on
`get_callers` / semantic search step is needed to find the subroutine that
acts on the value. Could also add a `uses_variable` tool that searches
source_text for bare references to a variable name (imprecise but useful).
