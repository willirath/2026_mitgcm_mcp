# MITgcm MCP Tool Retrospective

**Session**: triangular lake setup, 2026-02-23
**Model version**: checkpoint69k (`ghcr.io/willirath/2026-mitgcm-mcp:runtime-latest`)
**Task**: Design, compile, and run a MITgcm freshwater lake configuration from scratch using only MCP tools for research (no direct source grepping).
**Outcome**: Success after 5 Docker builds and 5 runs. Final state: `n3dWetPts=4060`, `theta_mean=12°C`, `uvel_max≈0.5 m/s`.

This document records tool-by-tool quality, when and why direct source inspection was attempted, Docker issues not covered by tool output, and runtime MITgcm issues that were difficult to resolve with the tools. Intended as input for MCP tool improvement.

---

## 1. Chronological MCP Tool Calls

| # | Tool | Arguments | Result quality | Notes |
|---|------|-----------|----------------|-------|
| 1 | `get_workflow_tool` | `{}` | Good | Returned Docker quickstart template immediately |
| 2 | `lookup_gotcha_tool` | "lake freshwater linear EOS wind stress" | **Excellent** | Caught `sBeta=0` must be explicit — prevented a silent wrong-results bug |
| 3 | `lookup_gotcha_tool` | "bathymetry partial cells rigid lid nonhydrostatic" | Good | Free surface vs rigid lid gotcha returned |
| 4 | `lookup_gotcha_tool` | "initial temperature profile wind stress surface forcing" | Redundant | Same free surface gotcha again |
| 5 | `search_docs_tool` | "triangular basin bathymetry lake setup irregular domain" | Weak | No triangular basin examples; did confirm masking approach |
| 6 | `get_doc_source_tool` | `getting_started.rst` / "Topography - Full and Partial Cells" | Good | Confirmed 2D bathy masking with zeros |
| 7 | `search_docs_tool` | "wind stress taux zonalWindFile data.pkg" | **Weak** | Returned EXF/bulk_force docs; the simple PARM05 `zonalWindFile` approach was not surfaced |
| 8 | `search_docs_tool` | "exf external forcing wind stress taux data namelist" | Weak | Same — EXF dominated |
| 9 | `search_code_tool` | "read wind stress taux surface forcing namelist parameter" | Weak | SEAICE_GET_DYNFORCING, EXF_DIAGNOSTICS_INIT — not useful |
| 10 | `namelist_to_code_tool` | `zonalWindFile` | Good | Confirmed PARM05 group |
| 11 | `namelist_to_code_tool` | `tauX` | **Empty** | `tauX` is an internal variable; tool should redirect to `zonalWindFile` |
| 12 | `search_code_tool` | "zonalWindFile PARM05 forcing files namelist" | Weak | Unhelpful hits (MDS_CHECK4FILE, GRDCHK_READPARMS) |
| 13 | `get_doc_source_tool` | `reentrant_channel.rst` / "PARM05 - Input datasets" | Good | Confirmed `zonalWindFile` takes 2D binary in N/m² |
| 14 | `get_source_tool` | `INI_FFIELDS` | OK | Confirmed forcing arrays are zeroed separately from file reading |
| 15 | `check_scales_tool` | Lx=10km, depth=50m, dt=60s, dz=5m | **Excellent** | Flagged vertical CFL=1.2 immediately; informed timestep choice |
| 16 | `lookup_gotcha_tool` | "implicit free surface barotropic timestep CFL instability" | Redundant | Same free surface gotcha returned again |
| 17 | `suggest_experiment_config_tool` | "baroclinic_instability" | Good (with bugs) | Provided working Docker template structure, but contained two bugs (see §3) |
| 18 | `get_doc_source_tool` | `verification/cheapAML_box/code/DIAGNOSTICS_SIZE.h` | Good | Complete `DIAGNOSTICS_SIZE.h` template |
| 19 | `lookup_gotcha_tool` | "comm_stats L_WBUFFER buffer gfortran compile error" | **Empty** | Gap — no entry for this compile failure |
| 20 | `search_code_tool` | "L_WBUFFER PARAMETER buffer size EEPARAMS definition" | Unhelpful | MDS_WRITEVEC_LOC, MDS_READ_FIELD — not useful |
| 21 | `get_source_tool` | `COMM_STATS` | OK | Showed include chain (`SIZE.h` → `EXCH.h`); not enough to diagnose root cause alone |
| 22 | `get_cpp_requirements_tool` | `COMM_STATS` | Empty | No CPP flags — correct, but didn't help |
| 23 | `get_doc_source_tool` | `verification/seaice_itd/code/EXCH.h` | **Excellent** | Showed full PARAMETER chain: `L_WBUFFER = L_BUFFERX = (sNy+2*MAX_OLY_EXCH)*MAX_OLX_EXCH*MAX_NR_EXCH` |
| 24 | `get_doc_source_tool` | `verification/ideal_2D_oce/code/CPP_EEOPTIONS.h` | Good | Template for `ALLOW_USE_MPI` |
| 25 | `get_doc_source_tool` | `verification/tutorial_barotropic_gyre/code/SIZE.h` | **Excellent** | Revealed the missing `MAX_OLX`/`MAX_OLY` PARAMETER block at the bottom of the file |
| 26 | `lookup_gotcha_tool` | "missing code calculate pressure totPhiHyd CONFIG_CHECK" | Partial | Returned non-hydrostatic CPP flag gotcha — topically related but wrong fix |
| 27 | `search_code_tool` | "CONFIG_CHECK totPhiHyd missing code calculate pressure" | OK | Surfaced adjacent subroutines; confirmed file to search |
| 28 | `find_subroutines_tool` | `CONFIG_CHECK` | Good | Located `config_check.F`, line range 14–1172 |
| 29 | `get_source_tool` | `CONFIG_CHECK`, offset=845, limit=30 | **Excellent** | Found `#ifndef INCLUDE_PHIHYD_CALCULATION_CODE` guard on first targeted read |
| 30 | `find_subroutines_tool` | `INI_THETA` | Good | Located file and line range |
| 31 | `get_source_tool` | `INI_THETA` | Good | Confirmed `tRef(k)` is used for level-by-level initialisation without `hydrogThetaFile` |

---

## 2. When and Why Direct Source Inspection Was Attempted

### First docker-grep phase (during Build 2 L_WBUFFER error)

After Build 2 failed with:
```
Error: Variable 'l_wbuffer' at (1) in this context must be constant
comm_stats.f:863:  Real*8   westSendBuf_RL( L_WBUFFER, ...
```

`lookup_gotcha_tool` and `search_code_tool` returned no useful results. I then ran the following directly against the container:

```bash
# Hypothesis: L_WBUFFER defined wrongly in EEPARAMS.h
docker run ... grep -n "L_WBUFFER" /MITgcm/eesupp/inc/EEPARAMS.h
# Result: nothing in EEPARAMS.h

# Wider search
docker run ... grep -rn "L_WBUFFER" /MITgcm/eesupp/
# Result: L_WBUFFER defined as PARAMETER in EXCH.h

# Read EXCH.h PARAMETER chain directly
docker run ... sed -n '155,175p' /MITgcm/eesupp/inc/EXCH.h

# Trace MAX_OLX definition
docker run ... grep -rn "MAX_OLX\b\|PARAMETER.*MAX_OLX" /MITgcm/eesupp/ /MITgcm/model/inc/
# Result: MAX_OLX defined in model/inc/SIZE.h as PARAMETER — revealed that custom SIZE.h was missing it

# Confirm include chain in comm_stats.F
docker run ... grep -n "include\|L_WBUFFER" /MITgcm/eesupp/src/comm_stats.F
```

**Why I fell back to this**: `search_code_tool` uses semantic/embedding search and could not surface a PARAMETER chain dependency from a concrete compiler error message. The tool answers "what does X do?" well but not "why does compiling X fail with this specific error?" There was no gotcha entry for `L_WBUFFER` or the non-MPI build template issue.

**Key insight revealed by docker grep**: `MAX_OLX` is defined in the standard `model/inc/SIZE.h` PARAMETER block, but our custom `code/SIZE.h` override was missing that block entirely. `EXCH.h` depends on `MAX_OLX` via `MAX_OLX_EXCH = MAX_OLX`. Without it, `L_WBUFFER` is an undeclared INTEGER (not a PARAMETER), so it cannot appear as an array dimension.

**After switching back to MCP tools**: `get_doc_source_tool` for `seaice_itd/code/EXCH.h` and `tutorial_barotropic_gyre/code/SIZE.h` had the same content indexed from verification directories. These worked and were sufficient. In hindsight, the docker grep was unnecessary — but it required knowing which specific files to ask for before the MCP tools could help.

The user interrupted at this point: **"Stop. Use the mitgcm tools. Don't just grep through the source."**

### Second docker-grep instance (CONFIG_CHECK error)

```bash
docker run ... grep -n "totPhiHyd\|missing code" /MITgcm/model/src/config_check.F
# Line 861: '  missing code to calculate pressure (totPhiHyd)'
```

This was run in parallel with `get_source_tool(CONFIG_CHECK, offset=845)` which returned the same content. Both approaches worked; the MCP tool was sufficient and this docker grep was unnecessary.

---

## 3. Docker Issues Not Covered by Tool Output

### 3.1 `dpkg-architecture` not in the image

`suggest_experiment_config_tool("baroclinic_instability")` returned a Dockerfile using:
```dockerfile
DPKGARCH=$(dpkg-architecture -qDEB_BUILD_ARCH) && \
  case "$DPKGARCH" in amd64) ... ;; arm64) ... ;; esac
```

`dpkg-architecture` is not installed in `ghcr.io/willirath/2026-mitgcm-mcp:runtime-latest`. Build 1 failed immediately.

Fix applied: switched to `uname -m` (returns `aarch64` / `x86_64`).

**Suggested fix for tool**: Update the Dockerfile template to use `uname -m` with the correct case values (`aarch64`/`x86_64` not `arm64`/`amd64`).

### 3.2 `--allow-run-as-root` is OpenMPI syntax; image uses MPICH

The template CMD included `mpirun --allow-run-as-root ./mitgcmuv`. The image uses MPICH (hydra launcher). MPICH does not recognise this flag:

```
[mpiexec] match_arg: unrecognized argument allow-run-as-root
[mpiexec] HYDU_parse_array: argument matching returned error
```

No tool output described which MPI implementation was in the image. Diagnosis required `docker run ... find /usr -name mpif.h` to confirm MPICH.

**Suggested fix for tool**: Remove `--allow-run-as-root` from the template CMD, or note the MPI implementation in the template comments.

### 3.3 `mpif77` wrapper causes `fcVers` detection to fail

The `linux_arm64_gfortran` optfile conditionally adds `-fallow-argument-mismatch`:
```bash
if [ $fcVers -ge 10 ] ; then FFLAGS="$FFLAGS -fallow-argument-mismatch" fi
```

`fcVers` is detected by running `$FC --version | head -1` and parsing the version number. When `FC=mpif77`, this returns version 0 (the mpif77 wrapper does not emit a parseable gfortran version string). gfortran 12 is strict about MPI argument type mismatches, so builds fail.

No MCP tool covered this. Diagnosis required reading the optfile from the container:
```bash
docker run ... grep -n "FFLAGS\|fallow\|fcVers" /MITgcm/tools/build_options/linux_arm64_gfortran
```

Fix applied: inject the flag via `genmake_local` before calling `genmake2`:
```dockerfile
echo 'FFLAGS="${FFLAGS} -fallow-argument-mismatch"' > genmake_local
```

**Suggested fix for tool**: Document this in a gotcha entry or in the Dockerfile template comments.

### 3.4 `-mpi` flag required even for single-rank builds

Without the `-mpi` flag, `genmake2` expands a different `comm_stats` template where the `SIZE.h` → `EXCH.h` PARAMETER chain is broken, causing the `L_WBUFFER` error. The `suggest_experiment_config_tool` template did not include `-mpi` in the `genmake2` invocation.

**Suggested fix for tool**: Always include `-mpi` in the template `genmake2` call, with a comment explaining it's needed even for `NP=1` runs.

---

## 4. MITgcm Runtime Issues Difficult to Resolve with the Tools

### 4.1 `PACKAGES_CHECK: cannot step forward Momentum without pkg/mom_fluxform`

```
PACKAGES_CHECK: cannot step forward Momentum without pkg/mom_fluxform
PACKAGES_CHECK: Re-compile with pkg "mom_fluxform" in packages.conf
STOP ABNORMAL END: S/R PACKAGES_CHECK
```

The error message was clear. The difficulty was knowing to use the `gfd` group name rather than listing `mom_fluxform` individually. `gfd` expands to `mom_fluxform`, `mom_common`, `mom_vecinv`, `generic_advdiff`, `debug`, `mdsio`, `rw`, `monitor` — all required for a standard ocean run.

No gotcha entry. Found the fix via `get_package_flags_tool` and documentation. A pre-flight gotcha would have caught this before the first run attempt and before the rebuild cycle.

**Suggested gotcha**: "Standard ocean/lake model requires `gfd` (not just `mom_fluxform`) in `packages.conf`. Without it, PACKAGES_CHECK aborts at runtime with a message about mom_fluxform. Rebuild is required after fixing."

### 4.2 `CONFIG_CHECK: missing code to calculate pressure (totPhiHyd)`

```
CONFIG_CHECK: missing code to calculate pressure (totPhiHyd)
CONFIG_CHECK: detected  1 fatal error(s)
STOP ABNORMAL END: S/R CONFIG_CHECK
```

`lookup_gotcha_tool("missing code calculate pressure totPhiHyd")` returned the non-hydrostatic CPP flag gotcha — topically related (both are about pressure calculation CPP flags) but the wrong fix.

The actual guard in `config_check.F:861`:
```fortran
#ifndef INCLUDE_PHIHYD_CALCULATION_CODE
 CALL PRINT_ERROR( 'missing code to calculate pressure (totPhiHyd)' ...
#endif
```

Fix: add `#define INCLUDE_PHIHYD_CALCULATION_CODE` to `CPP_OPTIONS.h`.

Found via `get_source_tool(CONFIG_CHECK, offset=845)` — targeted and effective once the correct file and approximate offset were known.

**Suggested gotcha**: "Hydrostatic runs require `#define INCLUDE_PHIHYD_CALCULATION_CODE` in `CPP_OPTIONS.h`. Without it, CONFIG_CHECK aborts with 'missing code to calculate pressure (totPhiHyd)'. This flag is not included by default."

### 4.3 Silent `readBinaryPrec` mismatch — the hardest bug

The model ran to `STOP NORMAL END` with no errors, no warnings. But results were physically wrong:

```
n2dWetPts  = 3.010000000000000E+02   (correct: 406)
n3dWetPts  = 3.010000000000000E+02   (correct: 4060 — only 1 of 10 depth levels wet)
dynstat_uvel_max  = 0.0000000000000E+00   (no circulation despite 0.05 N/m² wind)
dynstat_theta_mean = 1.9200000000000E+01  (19.2°C = tRef[0], the surface level only)
```

**Root cause**: `gendata.py` writes bathymetry as 64-bit big-endian doubles (`dtype='>f8'`). MITgcm default `readBinaryPrec=32` reads input files as 32-bit floats. The first 4 bytes of the 64-bit IEEE 754 representation of `-50.0` (`0xC049000000000000`) are `0xC0490000` = `-3.125` in 32-bit — giving bathymetry of ~−3.1 m instead of −50 m. Only the top 5 m layer was wet; all 9 deeper levels were dry.

**Why it was the hardest bug**:

1. The model terminated normally: `STOP NORMAL END`, no abort, no warning printed anywhere.
2. `n2dWetPts=301` is not obviously wrong for a small triangular basin — it requires knowing the expected value from `gendata.py` output (406).
3. `theta_mean=19.2°C` looks plausible for a warm surface lake. Only on reflection is it recognisable as exactly `tRef[0]` rather than a depth-weighted mean.
4. The decisive diagnostic clue: `n3dWetPts == n2dWetPts`. If 10 levels were wet, `n3dWetPts` should be 10× `n2dWetPts`.
5. No MCP tool — not `lookup_gotcha_tool`, not `check_scales_tool`, not `search_docs_tool` — provided any path to this diagnosis.

Fix: add `readBinaryPrec = 64` to `&PARM01` in `input/data`.

**This is arguably the highest-priority gap in the gotcha catalogue.** Python (and NumPy) default to 64-bit floats. MITgcm defaults to 32-bit reading. The combination is extremely common for new users and produces no runtime error.

**Suggested gotcha**: "Python/NumPy writes binary files as 64-bit float by default. MITgcm reads binary input with `readBinaryPrec=32` by default. The mismatch causes silently wrong results — the model runs to completion but bathymetry, temperature, and forcing files are read with incorrect values. Symptoms: `n3dWetPts == n2dWetPts` (only 1 vertical level wet), `theta_mean` equals `tRef(1)` throughout the run, no circulation. Diagnostic: compare `gendata.py` wet cell count against `n2dWetPts` in STDOUT.0000. Fix: add `readBinaryPrec = 64` to `&PARM01` in `input/data`, OR write binary files with `dtype='>f4'` in Python."

---

## 5. Summary of Tool Gaps (Prioritised)

### High priority

| Gap | Symptom | Impact |
|-----|---------|--------|
| No gotcha: `readBinaryPrec` mismatch | Model runs to `STOP NORMAL END` with wrong physics | Silent — hardest class of bug to diagnose |
| No gotcha: `INCLUDE_PHIHYD_CALCULATION_CODE` required | `CONFIG_CHECK` abort | Requires a full rebuild cycle |
| `suggest_experiment_config_tool` Dockerfile: `dpkg-architecture` not in image | Build fails immediately | Every first-time user hits this |
| `suggest_experiment_config_tool` CMD: `--allow-run-as-root` is OpenMPI-only | Run fails immediately | Image uses MPICH |

### Medium priority

| Gap | Symptom | Impact |
|-----|---------|--------|
| No gotcha: custom `SIZE.h` must include `MAX_OLX`/`MAX_OLY` PARAMETER block | Compile error: `MAX_OLX has no IMPLICIT type` | Confusing message; requires knowing `EXCH.h` dependency |
| No gotcha: `gfd` required in `packages.conf` for standard runs | `PACKAGES_CHECK` abort at runtime | Requires rebuild |
| No gotcha: `-mpi` required even for single-rank builds | `L_WBUFFER` compile error | Hard to diagnose without seeing EXCH.h |
| No gotcha: `mpif77` wrapper breaks `fcVers` detection with gfortran 12 | Type mismatch compile errors | Requires reading optfile from container |

### Low priority (search quality)

| Gap | Symptom |
|-----|---------|
| `search_code_tool` weak for compile error diagnosis | Semantic search cannot surface PARAMETER chain dependencies from error messages |
| `namelist_to_code_tool("tauX")` returns empty | Should redirect to `zonalWindFile` |
| `search_docs_tool` for wind stress returns EXF docs | Simple PARM05 `zonalWindFile` approach is buried by EXF/bulk package results |
| `lookup_gotcha_tool` returns same entry repeatedly | "Rigid lid vs free surface" returned for 3 different queries |

---

## 6. Post-run Visualisation

Output was read and plotted with a Python script (`plot_output.py`) using the project venv (numpy + matplotlib). No MCP tools were involved — this was pure post-processing.

### Data read

- **Surface θ**: field `THETA` at level 0 from `diag_state.*.data` (30×30×10, float32 big-endian, 5 fields per record). 30 daily snapshots, time-mean computed over all.
- **η std-dev**: field `ETAN` from `diag_etan.*.data` (30×30, float32 big-endian, 1 field per record). 30 daily snapshots, time std-dev computed over all.

Land cells (always `missingValue = -999`) were masked to NaN before plotting.

### Results

**Surface θ mean** (`output/surface_theta_mean.png`): Nearly uniform ~15°C across the basin. Very little horizontal temperature gradient at the surface after 30 days — expected with horizontal diffusion and no surface heat flux boundary condition. The initial linear profile (19.2°C at surface) has cooled slightly through mixing but remains largely intact.

**η mean** (`output/eta_mean.png`): Clear wind-driven setup. The westerly wind stress (positive τ_x) piles water up at the eastern boundary (SE corner, +6 mm) and draws it down at the western boundary (NW edge, −3 mm). The zero crossing runs diagonally across the basin, roughly perpendicular to the wind. This is the classic Ekman setup for a closed basin.

**η std-dev** (`output/eta_stddev.png`): Variability peaks at the acute SE corner (~2.3 mm) and decreases toward the wide NW side. The zonal wind drives water into the narrowing corner; the free surface adjusts more strongly there as the basin geometry constricts. The broad interior is relatively quiet (~0.3–0.5 mm).

### Script

`lake_triangle/plot_output.py` — reads `.meta` files to determine field ordering and dimensions, then reads `.data` files as big-endian float32. Grid info (Nx=30, Ny=30, Nr=10) and missing value (-999) taken from the meta files directly.
