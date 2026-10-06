#!/usr/bin/env bash
# Regenerate every figure in the manuscript and its supplement.
#
#   bash paper/figures/make_all.sh [OUTDIR]
#
# Default OUTDIR is paper/figures/output.  Needs only pandas and matplotlib:
# no GPU, no CUDA toolkit and no commercial solver licence.  All inputs are
# committed under benchmarks/results/ and paper/figures/data/.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTDIR="${1:-$HERE/output}"

for s in make_fig1 make_figS1 make_figS2 make_figS3 make_figS4; do
    echo "--- $s"
    python "$HERE/$s.py" --outdir "$OUTDIR"
done

echo
echo "figures written to $OUTDIR"
