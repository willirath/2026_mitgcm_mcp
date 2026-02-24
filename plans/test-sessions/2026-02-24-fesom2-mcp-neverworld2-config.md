# Test Session Report — FESOM2 MCP: Neverworld2-style rectangular channel config

**Date**: 2026-02-24
**Model under test**: FESOM2 MCP server (current HEAD, `fesom2` branch)
**Tester**: Claude Sonnet 4.6 (interactive session)
**Task**: Design a simple rectangular-domain FESOM2 ocean configuration with zonally symmetric
wind stress, temperature profile, no salinity, for a 2000 km × 4000 km domain with ~200 000
unstructured-mesh elements.

---

## What worked

### `get_workflow_tool`
Returned a clear, well-structured set of recommended tool sequences for the four main tasks
(design_experiment, debug_configuration, understand_module, explore_code). Useful orientation
at the start of a session.

### `get_namelist_structure_tool`
Returned a complete, accurate map of all namelist files and groups. This was the single most
useful tool in the session — it gave an immediate overview of where to look without needing
any prior FESOM2 knowledge.

### `suggest_experiment_config_tool` (baroclinic_channel)
Identified the right experiment class and returned a usable skeleton. Notes were accurate
(step_per_day constraint, METIS requirement, output field listing). One problem — see D1.

### `namelist_to_code_tool` (correctly bouncing non-namelist params)
When queried for `do_wind`, the tool correctly returned a warning that it was not a namelist
parameter and suggested `search_code_tool` as a follow-up. This is correct behaviour and
was informative.

### Source reading (`get_source_tool`, `find_modules_tool`, direct `Read`)
Once the right module was identified (`Toy_Neverworld2` in
`FESOM2/src/toy_channel_neverworld2.F90`), reading the source was reliable and accurate.
The wind stress, initial temperature stratification, and surface relaxation logic were all
clearly exposed in the source.

### `lookup_gotcha_tool` (step_per_day, namelist.io)
Both targeted lookups returned accurate, actionable entries. The `step_per_day` gotcha
correctly flagged the 86400-divisibility constraint. The `namelist.io` gotcha correctly
warned that unlisted fields produce no output silently.

### `translate_lab_params_tool` + `check_scales_tool`
The pipeline of: domain size → derived grid spacing → CFL check worked correctly and produced
a concrete `step_per_day` recommendation (192 instead of 144, to clear vertical CFL > 0.5).

---

## What did not work

### D1 — `suggest_experiment_config_tool` recommends CORE2 wind for a toy run

**Severity**: Moderate (misleading)

The skeleton config for `baroclinic_channel` included:

```fortran
&forcing
  wind_data_source = 'CORE2'
  CORE_forcing_dir = '<path to CORE2 wind files>'
```

This is wrong for a toy ocean run. Neverworld2 reads wind stress from a static mesh file
(`windstress@elem.out`) set up in `initial_state_neverworld2`. It does not use the bulk
forcing machinery or CORE2 at all. A user following this skeleton would waste time hunting
for CORE2 files that are never read.

The skeleton should either omit the `&forcing` block for toy setups, or explicitly note that
`toy_ocean = .true.` bypasses the forcing pipeline.

---

### D2 — `list_setups_tool` result exceeds token limit

**Severity**: Low (workaround exists, but awkward)

`list_setups_tool` returned 86 782 characters, which exceeded the inline token budget and was
redirected to a temporary file. A subsequent `Grep` on that file returned `[Omitted long
matching line]` — also useless. The tool effectively failed silently in this context.

In practice, the tool was not needed because `suggest_experiment_config_tool` and source
reading were sufficient. But for sessions where a user wants to browse available setups, this
is a dead end. The tool needs pagination or a filter parameter (e.g. `source=` or `name=`
substring filter).

---

### D3 — `lookup_gotcha_tool` misses toy-domain discovery queries

**Severity**: Low

Query `"toy ocean rectangular domain"` returned zero results. The gotcha catalogue has no
entries covering toy ocean setup at all — not for `toy_ocean = .true.`, `which_toy`,
`windstress@elem.out`, or the Neverworld2 wind file format. These are real traps for new
users (the wind file must pre-exist in `MeshPath` before the model starts, and its format is
undocumented outside the source).

---

### D4 — `translate_lab_params_tool` uses lab-rotation convention silently

**Severity**: Moderate (confusing)

The tool computes `f₀ = 2Ω` without a `sin(lat)` factor — the rotating-tank convention where
the rotation axis is vertical. For an ocean user specifying `Omega = 7.27e-5` (Earth's
rotation), this returns `f₀ = 1.454×10⁻⁴`, which corresponds to 90°N (the pole), not to any
physically meaningful mid-latitude f-plane.

The tool gives no indication that this convention is being used, and the output parameter
names (`f0`, `PARM01`, `EOS_PARM01`) are MITgcm-style, not FESOM2 namelist names. A FESOM2
user must manually translate these to `fplane_coriolis` in `namelist.config` and understand
that they need to pick their own latitude.

The tool should either:
(a) accept an optional `lat` parameter and compute `f = 2Ω sin(lat)`, or
(b) document explicitly in the return value that the lab convention is used and what latitude
it corresponds to.

---

### D5 — `check_scales_tool` vertical CFL is opaque

**Severity**: Low

The tool flagged `CFL_v = 0.60 > 0.5` for `dt = 600 s`, `dz = 100 m`, `U = 0.1 m/s`. The
horizontal CFL was straightforward to verify (`U × dt / dx = 0.006`), but the vertical CFL
formula is not documented and could not be reconstructed from the returned numbers. The
`flags` list gives the conclusion but not the quantity used or how to fix it other than
"reduce dt or increase dz".

The Ekman depth warning (`82.9 mm < dz`) was based on molecular viscosity (`ν = 1×10⁻⁶ m²/s`)
and is irrelevant for an ocean model with numerical eddy viscosity. It adds noise without
guidance on what to do.

---

### D6 — toy-ocean module variables not exposed as namelist parameters

**Severity**: Informational (a FESOM2 model limitation, not an MCP defect)

Key behavioural switches for the Neverworld2 toy — `do_wind`, `do_Trelax`, `do_Tpert`,
`tau_inv` — are module-level Fortran variables in `toy_channel_neverworld2.F90`, not namelist
parameters. They cannot be changed at runtime without recompiling. The MCP correctly reported
this when queried (`namelist_to_code_tool` returned the right warning), but there is no
gotcha entry pointing users toward this. Worth adding.

---

## Summary table

| # | Tool / area | Verdict |
|---|---|---|
| — | `get_workflow_tool` | OK |
| — | `get_namelist_structure_tool` | OK |
| — | `suggest_experiment_config_tool` skeleton | OK (but see D1) |
| D1 | Toy run skeleton includes CORE2 wind | Bug — misleading |
| D2 | `list_setups_tool` exceeds token budget | Bug — needs pagination/filter |
| D3 | Gotcha catalogue has no toy-ocean entries | Gap |
| D4 | `translate_lab_params_tool` lab-rotation convention undocumented | Bug — confusing for ocean users |
| D5 | `check_scales_tool` vertical CFL formula undocumented; Ekman warning noisy | Minor |
| D6 | `do_wind` etc not namelist-exposed | FESOM2 model limitation; worth a gotcha entry |
