# FESOM2 MCP Smoke Test Report — Run 2

**Date**: 2026-02-24 (post-fix)
**Test plan**: `plans/fesom2-smoke-test.md`
**Tester**: Claude Sonnet 4.6 (automated via MCP tool calls)

---

## Pass / Fail Summary

| # | Test | Verdict | Notes |
|---|------|---------|-------|
| A1 | `get_workflow_tool` null | PASS | All 4 workflows; each has non-empty steps |
| A2 | `get_workflow_tool` design_experiment | PASS | Single workflow; steps include list_setups_tool and lookup_gotcha_tool |
| A3 | `get_workflow_tool` xyzzy | PASS | Returns `{}` |
| A4 | `get_namelist_structure_tool` | PASS | namelist.config, namelist.ice, timestep group all present |
| A5 | `lookup_gotcha_tool` ALE | PASS | 1 result with title, summary, detail |
| A6 | `lookup_gotcha_tool` step_per_day | PASS | Matches timing gotcha |
| A7 | `lookup_gotcha_tool` xyzzy_not_real | PASS | Returns `[]` |
| A8 | `suggest_experiment_config_tool` baroclinic_channel | PASS | namelists present; no cpp_options key; notes now say "do NOT set namelist.forcing" |
| A9 | `suggest_experiment_config_tool` neverworld2 | PASS | Alias returns identical result to A8 |
| A10 | `suggest_experiment_config_tool` unknown | PASS | Returns `null` |
| A11 | `translate_lab_params_tool` | FAIL | `derived` present, `f0` present; `dt` still absent |
| A12 | `check_scales_tool` | PASS | `numbers` has Ro and Ek_v; `flags` list present |
| A13 | `list_setups_tool` (no args) | FAIL | Still 86 782 chars; overflows token budget |
| A14 | `list_setups_tool` toy_neverworld2 | PASS | `name=` filter returns inline; `{value, comment}` leaves confirmed |
| A15 | `list_setups_tool` test_pi_cavity | PASS | `name=` filter returns inline; fcheck non-empty, use_cavity=True confirmed |
| B1 | `find_modules_tool` oce_ale | FAIL | Returns `[]` |
| B2 | `get_module_tool` oce_ale | FAIL | Returns `null`; cascades from B1 |
| B3 | `find_subroutines_tool` (substitute: initial_state_neverworld2) | PASS | Returns match with module_name and file |
| B4 | `get_subroutine_tool` (unambiguous name) | PASS | Returns metadata; no source_text field |
| B5 | `get_source_tool` offset=0 limit=20 | PASS | lines non-empty; total_lines=128 |
| B6 | `get_source_tool` offset=20 limit=20 | PASS | Next page returned correctly |
| B7 | `get_callers_tool` | PASS | Returns `[{caller_name, caller_module}]` |
| B8 | `get_callees_tool` | PASS | Returns `[{callee_name}]` list |
| B9 | `get_module_uses_tool` | PASS | Non-empty list of USE'd module strings |
| B10 | `namelist_to_code_tool` step_per_day | PASS | module_name, namelist_group, non-null description all present |
| B11 | `namelist_to_code_tool` K_GM_max | PASS | config_file present |
| B12 | `namelist_to_code_tool` xyzzy_not_a_param | PASS | Single-item list with warning key |
| B13 | `find_modules_tool` xyzzy | PASS | Returns `[]` |
| C1 | `search_code_tool` GM eddy top_k=3 | FAIL | 3 results; file present in all; module_name="" in all 3 |
| C2 | `search_code_tool` EVP rheology | PASS | Top result EVPdynamics_a in ice_maEVP.F90 (ice_ file) |
| C3 | `search_docs_tool` ALE vertical top_k=5 | PASS | Mix of source="doc" and source="namelist" |
| C4 | `search_docs_tool` step_per_day | PASS | Top result source="namelist", param_name="step_per_day" |
| C5 | `get_doc_source_tool` (from C3) | PASS | lines non-empty; total_lines=43 |
| C6 | `get_doc_source_tool` offset past end | PASS | offset=50 > total_lines=43 → empty lines |
| D1 | A5 → `namelist_to_code_tool` min_hnode | PARTIAL | Chain runs; min_hnode has description=null, config_file=null |
| D2 | B1 → B2 → B5 | FAIL | B1 and B2 both fail; chain cannot complete |
| D3 | C1 → callees → source | PARTIAL | C1 GM results have module_name=""; chain only works via C2 EVP result as substitute |
| D4 | A13 → A8 | PARTIAL | A13 overflows; A8 works; name-filtered A14/A15 are a viable workaround |
| D5 | A12 flags CFL → A6 | PASS | End-to-end chain works |

---

## Changes since run 1

| Defect | Status |
|--------|--------|
| D-A8: skeleton included CORE2 wind for toy run | **FIXED** — notes now say "toy_ocean=.true. bypasses bulk forcing — do NOT set namelist.forcing" |
| D-B4: get_subroutine_tool errored on ambiguous name | **FIXED** — now returns `{disambiguation_needed, matches}` dict |
| D-A14/A15: list_setups_tool unusable for targeted lookups | **FIXED** — name= filter added; both tests now pass inline |
| D-A13: list_setups_tool unfiltered overflow | **NOT FIXED** |
| D-B1: find_modules_tool("oce_ale") returns [] | **NOT FIXED** |
| D-A11: dt absent from translate_lab_params_tool derived | **NOT FIXED** |
| D-C1: search_code_tool returns module_name="" | **NOT FIXED** |
| D-D1: min_hnode description=null | **NOT FIXED** |

---

## Remaining defects

### B1/B2 — `oce_ale` module not found (cascade failure)

**Severity**: Moderate

`find_modules_tool("oce_ale")` → `[]`; `get_module_tool("oce_ale")` → `null`. The file
`oce_ale.F90` contains only interface modules (`oce_ale_interfaces`, etc.) — no module
named `oce_ale` exists. Cascades to D2 which cannot complete. Either update the smoke test
plan to use `oce_ale_interfaces`, or add a file-level alias in the indexer.

---

### A13 — `list_setups_tool()` unfiltered still overflows

**Severity**: Moderate

Still 86 782 chars on every unfiltered call; redirected to a temp file that is not usable
inline. The `name=` filter (new in this release) resolves A14/A15 but A13's check (count ≥
16 records; both source types present) cannot be satisfied without it. Options: add a
`source=` filter, a `names_only=True` mode, or update the test plan to verify counts via two
filtered calls.

---

### A11 — `dt` absent from `translate_lab_params_tool` derived

**Severity**: Minor

`derived` still contains only `f0`, `L`, `aspect_ratio`, `dx`, `dy`, `dz`. Spec requires
`dt` to be finite and present.

---

### C1 — `search_code_tool` returns `module_name=""` for implementation subroutines

**Severity**: Moderate

All three GM results have `module_name=""`. Subroutines defined outside a named F90 `MODULE`
block get an empty module_name. Breaks downstream chains that try to call `get_module_tool`.

---

### D1 — `min_hnode` record incomplete

**Severity**: Minor

`namelist_to_code_tool("min_hnode")` returns `description=null`, `config_file=null`. The
parameter is indexed but its inline comment and config path were not captured.

---

## Score

| Group | Tests | PASS | PARTIAL | FAIL |
|-------|-------|------|---------|------|
| A | 15 | 12 | 0 | 3 |
| B | 13 | 9 | 0 | 4 (B1, B2 fail; B3–B9 pass with substitute subroutine) |
| C | 6 | 5 | 0 | 1 |
| D | 5 | 1 | 2 | 2 |
| **Total** | **39** | **27** | **2** | **10** |

**27 pass, 10 fail/partial** (run 1 was 26/13). Net gain: +1 clean pass (A8), A14/A15
upgraded from partial to pass, B4 upgraded from fail to pass.
