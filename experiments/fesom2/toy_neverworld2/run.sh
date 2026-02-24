#!/usr/bin/env bash
# Run the toy_neverworld2 FESOM2 experiment.
#
# Usage:
#   bash experiments/fesom2/toy_neverworld2/run.sh
#
# Override the image with:
#   FESOM2_IMAGE=ghcr.io/... bash experiments/fesom2/toy_neverworld2/run.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${FESOM2_IMAGE:-fesom2:latest}"

mkdir -p "$DIR/output"

docker run --rm \
    -v "$DIR/mesh:/mesh:ro" \
    -v "$DIR/input:/input:ro" \
    -v "$DIR/output:/output" \
    "$IMAGE"
