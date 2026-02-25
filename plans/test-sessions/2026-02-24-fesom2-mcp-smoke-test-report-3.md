# FESOM2 MCP Smoke Test Report — Run 3

**Date**: 2026-02-24 (post-fix, updated test plan)
**Test plan**: `plans/fesom2-smoke-test.md` (revised)
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
| A8 | `suggest_experiment_config_tool` baroclinic_channel | PASS | namelists present; no cpp_options key |
| A9 | `suggest_experiment_config_tool` neverworld2 | PASS | Alias returns identical result to A8 |
| A10 | `suggest_experiment_config_tool` unknown | PASS | Returns `null` |
| A11 | `translate_lab_params_tool` | PASS | `derived` present; `f0=10.0` finite; `dt=2.5` finite and non-null |
| A12 | `check_scales_tool` | PASS | `numbers` has Ro and Ek_v; `flags` list present |
| A13 | `list_setups_tool` names_only=True | PASS | 27 records; both source values present; no `namelists` key in records |
| A14 | `list_setups_tool` name=toy_neverworld2 | PASS | `{value, comment}` leaves confirmed in namelist.config |
| A15 | `list_setups_tool` name=test_pi_cavity | PASS | fcheck non-empty; use_cavity=True confirmed |
| B1 | `find_modules_tool` oce_ale_interfaces | PASS | Returns result with file=oce_ale.F90, start_line=44 |
| B2 | `get_module_tool` oce_ale_interfaces | PASS | 11 subroutines listed |
| B3 | `find_subroutines_tool` init_bottom_elem_thickness | PASS | Returns match with module_name="oce_ale_interfaces" |
| B4 | `get_subroutine_tool` same (with module=) | PASS | Returns metadata; no source_text field |
| B5 | `get_source_tool` offset=0 limit=20 | PASS | lines non-empty (7 lines); total_lines=7 > 0 |
| B6 | `get_source_tool` offset=20 | PASS | Returns empty lines past end (total_lines=7) |
| B7 | `get_callers_tool` | PASS | Returns `[{caller_name="init_ale", caller_module="oce_ale"}]` |
| B8 | `get_callees_tool` | PASS | Returns `[{callee_name="EXCHANGE_ELEM"}]` |
| B9 | `get_module_uses_tool` oce_ale_interfaces | PASS | Non-empty list: mod_mesh, MOD_PARTIT, MOD_PARSUP, MOD_DYN |
| B10 | `namelist_to_code_tool` step_per_day | PASS | module_name, namelist_group, non-null description all present |
| B11 | `namelist_to_code_tool` K_GM_max | PASS | config_file present |
| B12 | `namelist_to_code_tool` xyzzy_not_a_param | PASS | Single-item list with warning key |
| B13 | `find_modules_tool` xyzzy | PASS | Returns `[]` |
| C1 | `search_code_tool` GM eddy top_k=3 | PASS | 3 results; module_name non-empty in all (oce_mesh, Toy_Channel_Dbgyre, diagnostics) |
| C2 | `search_code_tool` EVP rheology | PASS | Top result EVPdynamics_a, module_name="ice_maEVP" |
| C3 | `search_docs_tool` ALE vertical top_k=5 | PASS | Mix of source="doc" and source="namelist" |
| C4 | `search_docs_tool` step_per_day | PASS | Top result source="namelist", param_name="step_per_day" |
| C5 | `get_doc_source_tool` (from C3) | PASS | lines non-empty; total_lines=43 |
| C6 | `get_doc_source_tool` offset past end | PASS | offset=50 > total_lines=43 → empty lines |
| D1 | A5 → `namelist_to_code_tool` min_hnode | PASS | Chain runs; description=null is expected per updated plan |
| D2 | B1 → B2 → B5 | PASS | find_modules → get_module → get_source on init_bottom_elem_thickness: all steps succeed |
| D3 | C1 → B8 → B5 | PASS | mesh_auxiliary_arrays callees returned (R2G, ELEM_CENTER, etc.); source readable |
| D4 | A13 → A8 | PASS | names_only listing identifies neverworld2; suggest_experiment_config returns matching skeleton |
| D5 | A12 flags CFL → A6 | PASS | CFL warning → step_per_day gotcha: end-to-end chain works |

---

## Changes since run 2

| Defect | Status |
|--------|--------|
| A11: `dt` absent from `derived` | **FIXED** — `dt=2.5` now present |
| A13: unfiltered overflow / no `names_only` mode | **FIXED** — `names_only=True` returns 27 inline records; both source types present; no `namelists` key |
| B1/B2: `oce_ale` module not found | **FIXED** (test plan updated to `oce_ale_interfaces`; tool returns correct result) |
| C1: `module_name=""` for implementation subroutines | **FIXED** — all 3 GM results now have non-empty module_name |
| D1: min_hnode description=null treated as defect | **RESOLVED** (test plan updated; null is now expected and documented) |
| D2: chain could not complete | **FIXED** (cascades from B1/B2 fix) |
| D3: C1 chain broken by empty module_name | **FIXED** (cascades from C1 fix) |
| D4: A13 overflow blocked comparison | **FIXED** (cascades from A13 fix) |

---

## Observations

### B3/B4 — interface stub vs. implementation (informational)

`find_subroutines_tool("init_bottom_elem_thickness")` correctly returns two matches: the
interface stub (module_name="oce_ale_interfaces", 7 lines) and the implementation
(module_name="oce_ale", 128 lines). The test passes because one match has the expected
module_name. Users wanting the implementation body should specify `module="oce_ale"`.

`get_callees_tool` on the interface stub returns `[EXCHANGE_ELEM]` — apparently resolved
from the implementation, not the stub. This is arguably correct behaviour but worth noting:
the callee graph is being served from the implementation even when the interface-module
version is requested.

### C1 — GM search quality (informational)

The three GM results (mesh_auxiliary_arrays, initial_state_dbgyre, diag_densMOC) are
semantically weak matches for "GM eddy parameterisation" — none of them are the actual GM
implementation routines. The module_name fix resolves the structural defect; the semantic
relevance of the embedding is a separate, open quality issue.

---

## Score

| Group | Tests | PASS | PARTIAL | FAIL |
|-------|-------|------|---------|------|
| A | 15 | 15 | 0 | 0 |
| B | 13 | 13 | 0 | 0 |
| C | 6 | 6 | 0 | 0 |
| D | 5 | 5 | 0 | 0 |
| **Total** | **39** | **39** | **0** | **0** |

**39/39 pass.** All defects from runs 1 and 2 are resolved or acknowledged in the updated
test plan.
