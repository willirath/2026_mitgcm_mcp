# FESOM2 MCP smoke test plan

Touch all 19 tools in their intended ways. Groups A–C ordered by dependency;
group D covers multi-tool chains.

---

## A — No index required (always runnable)

| # | Tool | Call | Verify |
|---|------|------|--------|
| A1 | `get_workflow_tool` | `task=null` | Returns all 4 workflows; each has non-empty `steps` |
| A2 | `get_workflow_tool` | `task="design_experiment"` | Single workflow; steps include `list_setups_tool` and `lookup_gotcha_tool` |
| A3 | `get_workflow_tool` | `task="xyzzy"` | Returns `{}` |
| A4 | `get_namelist_structure_tool` | (no args) | Keys include `namelist.config`, `namelist.ice`; `timestep` group present |
| A5 | `lookup_gotcha_tool` | `topic="ALE"` | ≥1 result with `title`, `summary`, `detail` |
| A6 | `lookup_gotcha_tool` | `topic="step_per_day"` | Matches the timing gotcha |
| A7 | `lookup_gotcha_tool` | `topic="xyzzy_not_real"` | Returns `[]` |
| A8 | `suggest_experiment_config_tool` | `experiment_type="baroclinic_channel"` | Has `namelists`; no `cpp_options` key |
| A9 | `suggest_experiment_config_tool` | `experiment_type="neverworld2"` | Same result as A8 (alias works) |
| A10 | `suggest_experiment_config_tool` | `experiment_type="unknown"` | Returns `null` |
| A11 | `translate_lab_params_tool` | `Lx=0.5, Ly=0.5, depth=0.2, Omega=5.0, delta_T=4.0, Nx=100, Ny=100, Nz=20` | `derived` key present; `dt` finite and non-null; `f0` finite |
| A12 | `check_scales_tool` | `Lx=0.5, Ly=0.5, depth=0.2, Omega=5.0, delta_T=4.0, dx=0.005, dz=0.01, dt=2.0, U=0.01` | `numbers` has `Ro` and `Ek`; `flags` list present |
| A13 | `list_setups_tool` | `names_only=True` | ≥16 records; both `source` values present; no `namelists` key in records |
| A14 | `list_setups_tool` | `name="toy_neverworld2"` | `toy_neverworld2` record has `namelist.config` with `{value, comment}` leaves |
| A15 | `list_setups_tool` | `name="test_pi_cavity"` | `fcheck` non-empty; `use_cavity` is `True` in namelist overrides |

---

## B — Needs DuckDB index (`pixi run fesom2-index`)

| # | Tool | Call | Verify |
|---|------|------|--------|
| B1 | `find_modules_tool` | `name="oce_ale_interfaces"` | ≥1 result with `file`, `start_line` (note: `oce_ale.F90` defines `oce_ale_interfaces`, not `oce_ale`) |
| B2 | `get_module_tool` | `name="oce_ale_interfaces"` | `subroutines` list non-empty |
| B3 | `find_subroutines_tool` | a name from B2's subroutines list | Returns match with `module_name="oce_ale_interfaces"` |
| B4 | `get_subroutine_tool` | same name | Returns metadata; no `source_text` field |
| B5 | `get_source_tool` | same name, `offset=0, limit=20` | `lines` list non-empty; `total_lines > 0` |
| B6 | `get_source_tool` | same name, `offset=20, limit=20` | Next page returned (fewer lines near end is fine) |
| B7 | `get_callers_tool` | same name | List of `{caller_name, caller_module}` (may be empty for init routines) |
| B8 | `get_callees_tool` | same name | List of `{callee_name}` |
| B9 | `get_module_uses_tool` | `module_name="oce_ale_interfaces"` | Non-empty list of module name strings |
| B10 | `namelist_to_code_tool` | `param="step_per_day"` | Has `module_name`, `namelist_group`, non-null `description` |
| B11 | `namelist_to_code_tool` | `param="K_GM_max"` | Result includes `config_file` |
| B12 | `namelist_to_code_tool` | `param="xyzzy_not_a_param"` | Single-item list with `warning` key |
| B13 | `find_modules_tool` | `name="xyzzy"` | Returns `[]` |

---

## C — Needs ChromaDB (`pixi run fesom2-embed[-docs|-namelists]`)

| # | Tool | Call | Verify |
|---|------|------|--------|
| C1 | `search_code_tool` | `query="GM eddy parameterisation", top_k=3` | 3 results each with non-empty `module_name`, `file` |
| C2 | `search_code_tool` | `query="EVP sea ice rheology subcycling"` | Top result in an `ice_` module |
| C3 | `search_docs_tool` | `query="ALE vertical coordinate", top_k=5` | Mix of `source="doc"` and `source="namelist"` |
| C4 | `search_docs_tool` | `query="step_per_day time step"` | Top result likely `source="namelist"` with `param_name="step_per_day"` |
| C5 | `get_doc_source_tool` | `file` and `section` from a C3 doc result | `lines` list non-empty; `total_lines > 0` |
| C6 | `get_doc_source_tool` | same, `offset=total_lines+1` | Returns empty `lines` (past end) |

---

## D — Multi-tool chains

| # | Chain | Purpose |
|---|-------|---------|
| D1 | A5 → B10 | Find ALE gotcha, then look up `min_hnode` via `namelist_to_code_tool`; note `description=null` is expected (param not in any config file) |
| D2 | B1 → B2 → B5 | `find_modules("oce_ale_interfaces")` → `get_module` → `get_source` on first listed subroutine |
| D3 | C1 → B8 → B5 | `search_code` → `get_callees` → read source of a callee |
| D4 | A13 → A8 | `list_setups` (find neverworld2 reference) → `suggest_experiment_config` to compare |
| D5 | A12 flags CFL → A6 | Scale check warning → `lookup_gotcha_tool("step_per_day")` |
