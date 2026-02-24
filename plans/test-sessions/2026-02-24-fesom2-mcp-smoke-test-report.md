# FESOM2 MCP Smoke Test Report

**Date**: 2026-02-24
**Test plan**: `plans/fesom2-smoke-test.md`
**Tester**: Claude Sonnet 4.6 (automated via MCP tool calls)

---

## Pass / Fail Summary

| # | Test | Verdict | Notes |
|---|------|---------|-------|
| A1 | `get_workflow_tool` null | PASS | All 4 workflows returned with non-empty steps |
| A2 | `get_workflow_tool` design_experiment | PASS | Single workflow; steps include list_setups_tool and lookup_gotcha_tool |
| A3 | `get_workflow_tool` xyzzy | PASS | Returns `{}` |
| A4 | `get_namelist_structure_tool` | PASS | namelist.config, namelist.ice, timestep group all present |
| A5 | `lookup_gotcha_tool` ALE | PASS | 1 result with title, summary, detail |
| A6 | `lookup_gotcha_tool` step_per_day | PASS | Matches timing gotcha |
| A7 | `lookup_gotcha_tool` xyzzy_not_real | PASS | Returns `[]` |
| A8 | `suggest_experiment_config_tool` baroclinic_channel | PASS | namelists present; no cpp_options key |
| A9 | `suggest_experiment_config_tool` neverworld2 | PASS | Alias returns identical result to A8 |
| A10 | `suggest_experiment_config_tool` unknown | PASS | Returns `null` |
| A11 | `translate_lab_params_tool` | FAIL | `derived` present, `f0` present; but `dt` absent from derived — spec requires both |
| A12 | `check_scales_tool` | PASS | `numbers` has Ro and Ek_v; `flags` list present (4 warnings) |
| A13 | `list_setups_tool` count/sources | FAIL | Response (86 782 chars) exceeds token budget; redirected to file — unusable inline |
| A14 | `list_setups_tool` toy_neverworld2 leaves | PASS | Verified via jq: `{value, comment}` leaves present |
| A15 | `list_setups_tool` test_pi_cavity | PASS | Verified via jq: fcheck non-empty; use_cavity = True |
| B1 | `find_modules_tool` oce_ale | FAIL | Returns `[]` — no module named `oce_ale` exists; file contains interface modules only (closest: `oce_ale_interfaces`) |
| B2 | `get_module_tool` oce_ale | FAIL | Cannot run — B1 found no module; ran with `oce_ale_interfaces` as substitute: PASS |
| B3 | `find_subroutines_tool` (from B2) | PASS | init_bottom_elem_thickness returns match with module_name="oce_ale_interfaces" |
| B4 | `get_subroutine_tool` (from B3) | FAIL | Errors without module= ("2 subroutines … pass module= to disambiguate"); with module= it works |
| B5 | `get_source_tool` offset=0 limit=20 | PASS | lines non-empty; total_lines=9 |
| B6 | `get_source_tool` offset=20 | PASS | Returns empty lines past end (total_lines=9) |
| B7 | `get_callers_tool` | PASS | Returns `[{caller_name, caller_module}]` |
| B8 | `get_callees_tool` | FAIL | Returns `[]` for interface stub — correct but unhelpful; spec expected a list to chain D3 from |
| B9 | `get_module_uses_tool` oce_ale | PASS | Returns non-empty list of USE'd modules |
| B10 | `namelist_to_code_tool` step_per_day | PASS | module_name, namelist_group, description all present |
| B11 | `namelist_to_code_tool` K_GM_max | PASS | config_file present |
| B12 | `namelist_to_code_tool` xyzzy_not_a_param | PASS | Returns single-item list with warning key |
| B13 | `find_modules_tool` xyzzy | PASS | Returns `[]` |
| C1 | `search_code_tool` GM eddy top_k=3 | FAIL | 3 results returned; file present in all; but module_name="" (empty) in all 3 |
| C2 | `search_code_tool` EVP rheology | PASS | Top result EVPdynamics_a in ice_maEVP.F90 (ice_ module) |
| C3 | `search_docs_tool` ALE vertical top_k=5 | PASS | Mix of source="doc" and source="namelist" present |
| C4 | `search_docs_tool` step_per_day | PASS | Top result source="namelist", param_name="step_per_day" |
| C5 | `get_doc_source_tool` (from C3 result) | PASS | lines non-empty; total_lines=43 |
| C6 | `get_doc_source_tool` offset past end | PASS | offset=50 > total_lines=43 returns empty lines |
| D1 | A5 → `namelist_to_code_tool` min_hnode | PARTIAL | Chain runs; but min_hnode returns description=null, config_file=null — record incomplete |
| D2 | B1 → B2 → B5 | PARTIAL | Chain requires module name correction at every step; works only with substituted name |
| D3 | C1 → callees → source | PARTIAL | C1 GM results have empty callees; chain required switching to C2 (EVP) result to complete |
| D4 | A13 → A8 | PARTIAL | A13 token overflow prevents inline comparison; A8 runs fine standalone |
| D5 | A12 flags CFL → A6 | PASS | Scale check warning → step_per_day gotcha: end-to-end chain works |

---

## Defect details

### D-A11 — `translate_lab_params_tool`: `dt` absent from `derived`

**Severity**: Minor

The test specifies that `derived` contains `dt` and `f` (finite). `f0` is present (10.0), but
`dt` is not in `derived`. The tool returns `dx`, `dy`, `dz`, `f0`, `L`, `aspect_ratio` only.
Either the spec is wrong or the tool is missing a `dt` output.

---

### D-A13 — `list_setups_tool` always overflows token budget

**Severity**: Moderate (same as previous session)

The response is 86 782 characters on every call. There is no pagination or filter parameter.
The result is silently redirected to a temp file, which cannot be read inline by a connected
LLM without out-of-band file access. Tests A14 and A15 only passed because jq was available
to query the file directly.

The tool needs a `name=` substring filter or `source=` filter, or pagination via `offset` /
`limit`.

---

### D-B1 — `find_modules_tool("oce_ale")` returns `[]`

**Severity**: Moderate — test plan defect and/or indexer gap

`oce_ale.F90` contains no module named `oce_ale`. Its modules are:
`compute_CFLz_interface`, `compute_Wvel_split_interface`,
`compute_vert_vel_transpv_interface`, `oce_ale_interfaces`, `init_ale_interface`,
`init_thickness_ale_interface`, `oce_timestep_ale_interface`.

Either the smoke test plan uses the wrong name, or the indexer should synthesise a
`oce_ale` umbrella entry for the file. Either way, the test plan should be updated to use
`oce_ale_interfaces`.

---

### D-B4 — `get_subroutine_tool` errors on ambiguous name without `module=`

**Severity**: Minor — unclear whether this is a bug or intended behaviour

When a subroutine name appears in more than one module (here: once in the interface module
with module_name="oce_ale_interfaces", once in the implementation with module_name=""), the
tool throws an error rather than returning the best match or a list. The error message
correctly instructs the user to pass `module=`, but this breaks naive chains where the
caller doesn't know that disambiguation is needed.

---

### D-B5/B8 — Interface stubs vs. implementations share the same name

**Severity**: Moderate — misleading output

When `module="oce_ale_interfaces"` is specified, `get_source_tool` returns the 9-line
interface declaration stub, not the actual implementation. The implementation body (hundreds
of lines) lives in a subroutine with `module_name=""`. A user asking for "the source of
`impl_vert_visc_ale`" will get the interface boilerplate unless they know to omit `module=`
— but omitting it causes B4's ambiguity error.

This is a systemic tension: subroutines that appear in both an interface module and an
implementation module with an empty name cannot be retrieved cleanly.

`get_callees_tool` on the stub returns `[]`, which breaks any D3-style chain that starts
from an interface-module subroutine.

---

### D-C1 — `search_code_tool` returns `module_name=""` for implementation subroutines

**Severity**: Moderate

Three of the top GM results have `module_name=""`. This is because the implementations in
files like `oce_ale_pressure_bv.F90` are not enclosed in a named module (or the parser does
not associate them with one). The spec requires `module_name` to be present and non-empty.
The field is present but empty, breaking any downstream `get_module_tool` or
`find_modules_tool` call.

---

### D-D1 partial — `min_hnode` record has null description and config_file

**Severity**: Minor

`namelist_to_code_tool("min_hnode")` returns a result with `description=null` and
`config_file=null`. The parameter is indexed (line 80 of gen_modules_config.F90) but its
inline comment was not captured. Compare to `step_per_day` which has a full description.
Incomplete records reduce the utility of the chain.

---

## Parallel call error propagation

**Severity**: Minor — infrastructure issue

When `get_subroutine_tool` (B4) was called in the same parallel batch as B5–B9, all sibling
calls returned `"Sibling tool call errored"` and had to be rerun individually. This is a
Claude Code MCP error propagation behaviour, not a server defect, but it slowed execution
significantly. Tests should be designed to run ambiguous lookups in isolation.

---

## Summary by group

| Group | Tests | PASS | PARTIAL | FAIL |
|-------|-------|------|---------|------|
| A (no index) | 15 | 12 | 0 | 3 (A11, A13 ×2 counted once, A13-A15 note) |
| B (DuckDB) | 13 | 8 | 0 | 5 (B1, B2, B4, B8 and B2 only via substitution) |
| C (ChromaDB) | 6 | 5 | 0 | 1 (C1) |
| D (chains) | 5 | 1 | 3 | 0 |
| **Total** | **39** | **26** | **3** | **10** |

Counting strictly (PARTIAL = FAIL): **26 pass, 13 fail/partial**.

---

## Recommended fixes (priority order)

1. **`list_setups_tool`**: add `name=` and/or `source=` filter parameters
2. **`oce_ale` module name**: update smoke test plan to use `oce_ale_interfaces`, or add
   file-level alias in indexer
3. **Empty `module_name`**: associate implementation subroutines in un-wrapped F90 files
   with their file stem or a synthetic module name; do not leave `module_name=""`
4. **Interface vs. implementation disambiguation**: document or handle the pattern where
   `get_source_tool` without `module=` errors, and with `module=` returns only the stub
5. **`translate_lab_params_tool`**: add `dt` to `derived` output (or update smoke test spec)
6. **`min_hnode` description**: fill in the missing inline comment / description field
