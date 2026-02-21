#!/usr/bin/env bash
set -euo pipefail
EXP=${1:?Usage: build-experiment.sh <experiment-dir>}
EXP_ABS=$(realpath "$EXP")
REPO=$(realpath "$(dirname "$0")/..")
docker run --rm \
  --platform linux/amd64 \
  --user "$(id -u):$(id -g)" \
  -v "$REPO/MITgcm:/MITgcm" \
  -v "$EXP_ABS:/experiment" \
  mitgcm:latest bash -c "
    mkdir -p /experiment/build && cd /experiment/build &&
    MPI=true MPI_HOME=/usr/lib/x86_64-linux-gnu/openmpi /MITgcm/tools/genmake2 \
      -rootdir /MITgcm \
      -mods /experiment/code \
      -optfile /MITgcm/tools/build_options/linux_amd64_gfortran \
      -mpi &&
    make depend && make -j\$(nproc)"
