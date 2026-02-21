# M6 — MITgcm Runtime Environment

## Purpose

Provide a reproducible, compile-on-demand build and run environment for
MITgcm experiments. The container is the toolchain; the experiment directory
is the workspace. Works locally via Docker; translates directly to Singularity
on HPC (no daemon, no privileged mode needed for the run step).

---

## Design

### Container role

The image provides:
- gfortran, OpenMPI, NetCDF-Fortran (build toolchain)
- MITgcm source tree (mounted from the submodule, not baked in)
- genmake2 entry point

The image does NOT contain:
- A pre-compiled binary (grid dimensions are compile-time constants in SIZE.h)
- Any experiment-specific files

### Experiment directory layout

An experiment directory follows MITgcm convention:

```
experiments/<name>/
├── code/
│   ├── CPP_OPTIONS.h
│   ├── SIZE.h
│   ├── packages.conf
│   └── <any custom .F overrides>
├── input/
│   ├── data
│   ├── data.pkg
│   ├── eedata
│   └── <binary .bin initial condition files>
└── build/        (created by pixi run build-experiment)
```

The system does not dictate how `input/` is populated beyond the above
structure. Binary `.bin` files are generated separately (M7 concern).

### pixi tasks

```
pixi run build-image          # docker build → mitgcm:latest
pixi run build-experiment DIR # compile mitgcmuv for experiments/<DIR>/
pixi run run-experiment DIR   # run mitgcmuv in experiments/<DIR>/run/
```

`build-experiment` and `run-experiment` accept the experiment directory as
a positional argument. They fail with a clear message if the directory does
not exist or is missing required subdirectories.

### Volume mounts (docker run)

| Host path | Container path | Purpose |
|---|---|---|
| `./MITgcm` | `/MITgcm` | Source tree (read-only) |
| `./experiments/<name>` | `/experiment` | Experiment workspace (read-write) |

The container runs as the host user (via `--user $(id -u):$(id -g)`) so
output files are owned correctly.

### Build step (inside container)

```sh
mkdir -p /experiment/build
cd /experiment/build
/MITgcm/tools/genmake2 \
    -mods /experiment/code \
    -optfile /MITgcm/tools/build_options/linux_amd64_gfortran \
    -mpi
make depend
make -j$(nproc)
```

Output: `/experiment/build/mitgcmuv`

### Run step (inside container)

```sh
mkdir -p /experiment/run
cd /experiment/run
ln -sf /experiment/build/mitgcmuv .
ln -sf /experiment/input/* .
mpirun -np 1 ./mitgcmuv
```

`-np 1` by default; overrideable via `MITGCM_NP` env variable.

---

## Files to create

### `Dockerfile`

Multi-stage build:

**Stage 1 — toolchain** (based on `debian:bookworm-slim`):
- Install: `gfortran libopenmpi-dev openmpi-bin libnetcdf-dev libnetcdff-dev make perl`
- No MITgcm source baked in

Single stage is sufficient (no need to shed build deps — this is a science
container, not a production service).

### `scripts/build-experiment.sh`

Wrapper that:
1. Validates `$1` is a directory with `code/` and `input/` subdirectories
2. Runs `docker run` with appropriate mounts and the build command above
3. Exits with the container's exit code

### `scripts/run-experiment.sh`

Wrapper that:
1. Validates `$1` has `build/mitgcmuv`
2. Runs `docker run` with mounts and the run command above
3. Streams stdout/stderr (no `-d`)

### `pixi.toml` additions

```toml
[tasks]
build-image      = "docker build -t mitgcm:latest ."
build-experiment = { cmd = "scripts/build-experiment.sh", args = ["DIR"] }
run-experiment   = { cmd = "scripts/run-experiment.sh",   args = ["DIR"] }
```

Note: pixi tasks cannot easily forward arbitrary positional args. Use shell
scripts that read `$1`; invoke as `pixi run build-experiment -- rotating_tank`.
Alternatively, use plain `bash scripts/build-experiment.sh <DIR>` and document
this clearly in the docs.

### `docs/runtime.md`

Cover:
- Prerequisites (Docker installed and running)
- How to build the image (`pixi run build-image`)
- Experiment directory layout
- How to build and run an experiment
- How to translate to Singularity on HPC (drop-in: `singularity exec` instead
  of `docker run`, same mounts via `--bind`)
- Known limitation: SIZE.h is compiled in — changing grid dimensions requires
  a rebuild

---

## Done-when

`verification/tutorial_rotating_tank` runs to completion inside the container
and produces output files.

Concretely:
1. `pixi run build-image` succeeds
2. Copy the tutorial into `experiments/tutorial_rotating_tank/` (symlink or
   copy `code/` and `input/` from `MITgcm/verification/tutorial_rotating_tank/`)
3. `bash scripts/build-experiment.sh tutorial_rotating_tank` produces
   `experiments/tutorial_rotating_tank/build/mitgcmuv`
4. `bash scripts/run-experiment.sh tutorial_rotating_tank` runs to completion
   (20 time steps per the tutorial's `data` namelist) and writes monitor output
   to stdout and `mnc_test_*/` files in `experiments/tutorial_rotating_tank/run/`

---

## Singularity translation (HPC note)

```sh
# Build image locally, export to .sif
docker save mitgcm:latest | gzip > mitgcm.tar.gz
singularity build mitgcm.sif docker-archive://mitgcm.tar.gz

# Run on HPC (no daemon required)
singularity exec \
  --bind ./MITgcm:/MITgcm:ro \
  --bind ./experiments/my_exp:/experiment \
  mitgcm.sif bash /experiment/build.sh
```

No code changes needed — same scripts, same mounts.

---

## Open questions (not blocking M6)

- **optfile**: `linux_amd64_gfortran` assumes x86. On ARM (Apple Silicon +
  Rosetta or native Linux ARM), a different optfile or `--platform linux/amd64`
  flag for Docker is needed. Document in `docs/runtime.md`.
- **MPI process count**: single-process run is sufficient for M6. Tiling
  (SIZE.h `nPx`/`nPy`) and `mpirun -np N` can be introduced in M7.
- **Binary input files**: the tutorial ships `bathyPolR.bin` and `thetaPolR.bin`.
  For new experiments, these need to be generated (numpy + `>.tofile()`). This
  is an M7 concern.
- **Output format**: the tutorial uses MNC (NetCDF via the `mnc` package).
  Plain binary pickup files and monitor output are always produced. Diagnostics
  output (via `data.diagnostics`) is optional. M7 will decide what to read.
