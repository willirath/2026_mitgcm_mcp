# Smoke test results — v2026.02.6 (run 3)

**Date:** 2026-02-25
**Agent:** Claude Code (claude-sonnet-4-6)
**Test plan:** `smoke-test-v2026.02.6.md`
**Previous results:** `smoke-test-results-v2026.02.6-run2.md` (run 2)
**Scope:** Focused re-test of all previously failing items (A6, B2, B3) and spot-checks of unchanged passes.

---

## Executive summary

| Part | Status | Critical failures |
|------|--------|-----------------|
| A — MITgcm MCP | **PASS** | — (A6 fixed) |
| B — FESOM2 MCP | **PARTIAL PASS** | B3 (`oce_fer_gm` absent from module index) |
| C — Runtime images | **PASS** (unchanged from run 2, not re-tested) | — |

**Release verdict: NOT READY TO TAG.** One critical failure remains (B3).

### Defect status delta vs run 2

| Defect | Run 2 | Run 3 | Change |
|--------|-------|-------|--------|
| DEF-1 (A6) `list_verification_experiments_tool` empty | FAIL | **PASS** | **Fixed** — 60+ experiments with structured fields |
| DEF-3 (B2) `K_GM` — spec bug | FAIL* | **PASS** | Spec updated: `k_gm_max` passes correctly |
| DEF-4 (B3) `find_modules_tool` broken | FAIL | **FAIL** | Partial progress — index no longer completely empty, but `oce_fer_gm` not indexed |

---

## Focused re-tests

### A6. Verification experiment lookup

**Result: PASS** *(was FAIL in runs 1 & 2 — DEF-1 fixed)*

`list_verification_experiments_tool()` now returns a full catalogue of **63 experiments** with structured metadata fields (`name`, `tutorial`, `packages`, `domain_class`, `Nx/Ny/Nr`, `grid_type`, `nonhydrostatic`, `free_surface`, `eos_type`).

Experiments with `nonhydrostatic: true`:

| Name | domain_class | grid_type | free_surface |
|------|-------------|-----------|--------------|
| `deep_anelastic` | idealized | spherical_polar | true |
| `exp4` | ocean | cartesian | true |
| `short_surf_wave` | idealized | cartesian | true |
| `tutorial_deep_convection` | idealized | cartesian | true |
| `tutorial_plume_on_slope` | ocean | cartesian | true |
| `tutorial_rotating_tank` | idealized | cartesian | false (rigid lid) |

Pass criteria:
- `list_verification_experiments_tool` returns experiment names ✓ (63 entries)
- At least one result references `nonHydrostatic` ✓ (6 experiments have `nonhydrostatic: true`)

**DEF-1 is resolved.** The verification experiment catalogue table is now populated.

**Note on `search_verification_tool`:** Still returns `CPP_OPTIONS.h` snippets mentioning `ALLOW_CG2D_NSA` rather than `data` files with `nonHydrostatic = .TRUE.`. This is a semantic search embedding quality issue (non-blocking since the catalogue tool now satisfies A6). Sample return:

```json
{"experiment": "dome", "file": "verification/dome/code/CPP_OPTIONS.h",
 "snippet": "#undef ALLOW_CG2D_NSA\n#undef ALLOW_SRCG\n..."}
```

The search tool does return experiment names (dome, cheapAML_box, lab_sea, fizhi-cs-aqualev20, tutorial_held_suarez_cs) but none of the 5 snippets contain `nonHydrostatic = .TRUE.`. This is a secondary quality concern — the catalogue tool is the primary path.

---

### B2. Namelist parameter lookup (K_GM — spec-corrected)

**Result: PASS** *(spec updated per run 2 finding — DEF-3 resolved as spec bug)*

`namelist_to_code_tool("k_gm_max")` returned:

```json
[{"param_name": "K_GM_max", "namelist_group": "oce_dyn",
  "file": "FESOM2/src/oce_modules.F90", "module_name": "o_PARAM",
  "line": 192, "description": "max. GM thickness diffusivity (m2/s)",
  "config_file": "FESOM2/config/namelist.oce"}]
```

- Parameter `k_gm_max` found ✓
- Namelist group `oce_dyn` in `namelist.oce` ✓
- Reading module `o_PARAM` (`oce_modules.F90`) ✓

The test spec criterion "Returns `K_GM`" was incorrect — FESOM2 uses `k_gm_max`/`k_gm_min`/`fer_gm`. With the corrected expectation this test **PASSES**.

---

### B3. Module navigation (GM/Redi)

**Result: FAIL** *(Critical — DEF-4 partially improved but not resolved)*

**Change from run 2:** The module index is no longer completely empty. Several modules are now discoverable:

| Query | Result |
|-------|--------|
| `find_modules_tool("o_PARAM")` | ✓ Found: id=159, `oce_modules.F90` lines 7–212 |
| `find_modules_tool("Toy_Channel_Dbgyre")` | ✓ Found: id=170, `toy_channel_dbgyre.F90` lines 1–261 |
| `find_modules_tool("cvmix_tke")` | ✓ Found: id=15, `cvmix_tke.F90` lines 2–1098 |
| `find_modules_tool("oce_fer_gm")` | ✗ Empty |
| `find_modules_tool("mod_transit")` | ✗ Empty |
| `find_modules_tool("oce_ale_pressure_bv")` | ✗ Empty |
| `find_modules_tool("oce_dyn")` | ✗ Empty |
| `find_modules_tool("fer")` | ✗ Empty |

`get_module_tool` and `get_module_uses_tool` work correctly for **indexed** modules:

```json
// get_module_tool("cvmix_tke")
{"id": 15, "name": "cvmix_tke", "file": "FESOM2/src/cvmix_driver/cvmix_tke.F90",
 "start_line": 2, "end_line": 1098,
 "subroutines": [{"name":"init_tke",...}, {"name":"tke_wrap",...}, ...]}

// get_module_uses_tool("cvmix_tke")
["cvmix_kinds_and_types", "cvmix_kinds_and_types_addon", "cvmix_utils_addon"]
```

The GM/Redi module `oce_fer_gm` was identified via `search_code_tool("fer_gm GM skew flux Ferrari 2010 isopycnal diffusion")` → subroutine `fer_gamma2vel` in module `oce_fer_gm` (`FESOM2/src/oce_fer_gm.F90`). However:

- `find_modules_tool("oce_fer_gm")` → empty ✗
- `get_module_tool("oce_fer_gm")` → `null` ✗
- `get_module_uses_tool("oce_fer_gm")` → empty ✗

**Root cause:** The DuckDB `modules` table is partially populated — cvmix\_driver modules and a few others are indexed, but the main FESOM2 `src/oce_*.F90` dynamics modules (including `oce_fer_gm`, `mod_transit`, `oce_ale_pressure_bv`) are absent. This is a subset of the module indexing step failing silently.

**Impact:** B3 still fails. A user cannot navigate from "GM module" → `find_modules_tool` → `get_module_uses_tool` for the relevant ocean dynamics modules.

---

## Spot-checks of previously passing tests (no regressions found)

Confirmed still passing in run 3 without full re-test (tool results identical to run 2):

| Test | Spot-check result |
|------|------------------|
| A1 Tool count (23) | 23 tools present — no change |
| A2 `cg3dMaxIters` | `namelist_to_code_tool("cg3dMaxIters")` → `INI_PARMS`/`PARM02` ✓ |
| B1 FESOM2 tool count (20) | 20 tools (unchanged from run 2 fix) ✓ |
| B5 Setups catalogue | 27 setups (unchanged from run 2 fix) ✓ |

---

## Pass / fail summary (runs 1–3)

| Test | Critical? | Run 1 | Run 2 | Run 3 |
|------|-----------|-------|-------|-------|
| A1 Tool count (23) | Yes | PASS | PASS | PASS |
| A2 Namelist → `cg3dMaxIters` | Yes | PASS | PASS | PASS |
| A3 Code search + source | Yes | PASS | PASS | PASS |
| A4 Call graph (CG3D) | Yes | PASS | PASS | PASS |
| A5 Docs search | Yes | PASS | PASS | PASS |
| A6 Verification experiments | Yes | FAIL | FAIL | **PASS** ✅ |
| A7 Lab translation + scales | Yes | PASS | PASS | PASS |
| A8 Gotcha lookup | Yes | PASS | PASS | PASS |
| A9 Namelist structure | No | PASS | PASS | PASS |
| A10 Package navigation | No | PASS | PASS | PASS |
| B1 Tool count (20) | Yes | FAIL | **PASS** ✅ | PASS |
| B2 Namelist → `K_GM`/`k_gm_max` | Yes | FAIL | FAIL* | **PASS** ✅ |
| B3 Module navigation | Yes | FAIL | FAIL | **FAIL** |
| B4 Docs + namelist search | Yes | PASS | PASS | PASS |
| B5 Setups catalogue | Yes | FAIL | **PASS** ✅ | PASS |
| B6 Lab translation + scales | Yes | PASS | PASS | PASS |
| B7 Experiment skeleton | Yes | PASS | PASS | PASS |
| B8 Gotcha lookup | Yes | PASS | PASS | PASS |
| B9 Run interface | No | PASS | PASS | PASS |
| B10 Workflow guidance | No | PASS | PASS | PASS |
| C1 MITgcm runtime | No | PASS | PASS | PASS |
| C2 FESOM2 runtime | No | PASS | PASS | PASS |

**Remaining critical failure: B3 only.**

---

## Defect details

### DEF-4 (B3): `oce_fer_gm` absent from FESOM2 module index — PERSISTS (partial progress)

**Severity:** Critical (blocks B3)
**Change since run 2:** Module index is no longer completely empty. cvmix\_driver modules (`cvmix_tke`, etc.) and a few others (`o_PARAM`, `Toy_Channel_Dbgyre`) are indexed and fully functional via `find_modules_tool`, `get_module_tool`, and `get_module_uses_tool`. The ocean dynamics modules in `src/oce_*.F90` and `src/mod_transit.F90` are still absent.
**Symptom:** `find_modules_tool("oce_fer_gm")` returns empty; `get_module_tool("oce_fer_gm")` returns null; `get_module_uses_tool("oce_fer_gm")` returns empty. `search_code_tool` does surface subroutines in `oce_fer_gm` confirming the file exists.
**Probable cause:** The module indexing step only indexed a subset of source files (possibly the cvmix\_driver subdirectory) and skipped the top-level `src/oce_*.F90` files. The build step may need to be run against all F90 files in `FESOM2/src/`.
