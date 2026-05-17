#!/usr/bin/env bash
# Storebro CLI quickstart — copy/paste-friendly walkthrough.
# Requires: pip install freecad-storebro && FreeCAD 1.1+ on PATH.

set -euo pipefail

OUT_DIR="${1:-./storebro_demo}"
mkdir -p "$OUT_DIR"

echo "==> 1. Diagnostic info"
storebro info

echo
echo "==> 2. List canonical layouts"
storebro list-layouts

echo
echo "==> 3. Build the canonical Storebro (Alternativ3) as .FCStd"
storebro build --out "$OUT_DIR/boat.FCStd"

echo
echo "==> 4. Build a different layout"
storebro build --layout Alternativ1 --out "$OUT_DIR/boat_alt1.FCStd"

echo
echo "==> 5. Export to STEP for interchange with other CAD tools"
storebro build --format step --out "$OUT_DIR/boat.step"

echo
echo "==> 6. Export to a finely-tessellated STL"
storebro build --format stl --out "$OUT_DIR/boat_fine.stl" --tessellation 0.0005

echo
echo "==> 7. Refuse-to-overwrite mode (will fail second time)"
if storebro build --out "$OUT_DIR/boat.FCStd" --no-overwrite; then
    echo "unexpected: second --no-overwrite build should have failed"
    exit 1
fi || true

echo
echo "==> 8. Debug mode (full Python traceback on error)"
storebro --debug build --layout BogusLayout --out "$OUT_DIR/x.FCStd" || true

echo
echo "Done. Artifacts written to $OUT_DIR/"
