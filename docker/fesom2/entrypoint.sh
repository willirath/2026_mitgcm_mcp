#!/usr/bin/env bash
# Run a FESOM2 experiment from mounted directories.
#
# Mounts (all required):
#   /mesh    — mesh files (nod2d.out, elem2d.out, aux3d.out, dist_N/, ...)
#   /input   — namelist files (namelist.config, namelist.oce, ...)
#   /output  — output directory (NetCDF files, fesom.clock written here)
#
# All experiment parameters (run_length, step_per_day, n_part, which_toy, ...)
# are read from /input/namelist.config. The entrypoint patches only the three
# container-internal paths: MeshPath, ResultPath, ClimateDataPath.
set -euo pipefail

# --- Validate mounts ----------------------------------------------------------
for mount in /mesh /input /output; do
    if [ ! -d "$mount" ]; then
        echo "ERROR: $mount is not mounted" >&2
        exit 1
    fi
done

if [ ! -f /input/namelist.config ]; then
    echo "ERROR: /input/namelist.config not found" >&2
    exit 1
fi

# --- Setup --------------------------------------------------------------------
WORK_DIR=$(mktemp -d)
cd "${WORK_DIR}"

echo "=== FESOM2 experiment ==="
echo "    workdir : ${WORK_DIR}"
echo "    mesh    : /mesh"
echo "    input   : /input"
echo "    output  : /output"
echo ""

# --- Copy namelists from /input -----------------------------------------------
cp /input/namelist.* .

# --- Patch paths and write fesom.clock ----------------------------------------
python3 - <<'PYEOF'
import re

with open('namelist.config') as fh:
    text = fh.read()

text = re.sub(r"(MeshPath\s*=\s*)('[^']*'|\"[^\"]*\")",        r"\1'/mesh/'",     text)
text = re.sub(r"(ResultPath\s*=\s*)('[^']*'|\"[^\"]*\")",      r"\1'/output/'",   text)
text = re.sub(r"(ClimateDataPath\s*=\s*)('[^']*'|\"[^\"]*\")", r"\1'/dev/null/'", text)

with open('namelist.config', 'w') as fh:
    fh.write(text)

# Write fesom.clock for a cold start (two identical lines = cold start).
m_t = re.search(r'timenew\s*=\s*([\d.]+)', text)
m_d = re.search(r'daynew\s*=\s*(\d+)',     text)
m_y = re.search(r'yearnew\s*=\s*(\d+)',    text)
t = m_t.group(1) if m_t else '0.0'
d = m_d.group(1) if m_d else '1'
y = m_y.group(1) if m_y else '1900'
clock_line = f'{t} {d} {y}\n'
with open('/output/fesom.clock', 'w') as fh:
    fh.write(clock_line)
    fh.write(clock_line)
PYEOF

# --- Read n_part from patched namelist.config ---------------------------------
NRANKS=$(grep -E '^\s*n_part\s*=' namelist.config | grep -oE '[0-9]+' | head -1)

echo "=== Patched namelist.config (key values) ==="
grep -E "MeshPath|ResultPath|ClimateDataPath|run_length|step_per_day|n_part|which_toy" \
    namelist.config | grep -v "^!"
echo ""

# --- Run FESOM2 ---------------------------------------------------------------
echo "=== Running fesom.x (n_part=${NRANKS}) ==="
mpirun --allow-run-as-root -np "${NRANKS}" /fesom2/bin/fesom.x

echo ""
echo "=== Done. Output files in /output ==="
ls /output/
