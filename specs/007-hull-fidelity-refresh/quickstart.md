# Quickstart: Hull Fidelity Refresh

**Spec**: [spec.md](./spec.md) | **Contract**: [contracts/python-api-preserved.md](./contracts/python-api-preserved.md) | **Date**: 2026-05-17

A walkthrough of what changes for users after spec 007 lands. Public Python and CLI API surfaces are unchanged; what changes is the hull SHAPE inside the generated `.FCStd`.

---

## 1. Build a hull (same command as before)

```bash
uv run storebro build --out boat.FCStd
```

The CLI invocation is byte-identical to v1.0.0's command. What's inside `boat.FCStd` is now a recognizable Storebro RC34 1972 silhouette instead of a faceted wedge.

---

## 2. Open in FreeCAD GUI — what's different

Press `3` for right-side view. Compare against `docs/references/Alternativ3.JPG`'s upper-half profile (the storebropassion.de side drawing):

| Feature | v1.0.0 | v1.0.1 |
|---|---|---|
| **Stem (bow)** | sharp knife-edge point at the right | finite 80mm-wide blunt face, leans forward 6° from vertical |
| **Transom (stern)** | 12° aft rake | 5° aft rake (near-vertical) |
| **Sheer line** | rises 450mm from aft (0.85m) to bow (1.30m) — very visible slope | rises 210mm from aft (0.95m) to bow (1.16m) — near-flat |
| **Hull surface** | faceted, piecewise-linear creases between stations | smoothly curved (B-spline interpolation) |
| **Bilge** | sharp pentagon corner where bottom meets sides | rounded quarter-circle bilge transitioning bottom → topsides |
| **Deadrise at amidships** | 16° (planing hull) | 8° (semi-displacement — flatter bottom) |
| **Draft** | 0.95 m | 1.10 m (matches the real RC34 spec) |

---

## 3. Inspect the new 9th property

Select `HullBody` in the tree. In the Property panel:

```
Hull
├── LOA               : 10.35 m
├── BeamMax           :  3.20 m
├── Draft             :  1.10 m   ← CHANGED
├── Freeboard         :  0.95 m
├── DeadriseAmidships :  8.00 °   ← CHANGED
├── SheerHeightAft    :  0.95 m   ← CHANGED
├── SheerHeightFwd    :  1.16 m   ← CHANGED
├── TransomAngle      :  5.00 °   ← CHANGED
└── StemRakeAngle     :  6.00 °   ← NEW
```

All 9 are still informational only (v1.1+ deferred: expression-engine bindings).

---

## 4. Edit a station sketch (the parametric editing path)

The same workflow as v1.0.0:

1. Expand `HullBody` in the tree
2. Double-click `HullStationAmidships`
3. The sketcher view opens — but now you see a **rounded-bilge** profile (4 line segments + 1 quarter-circle arc) instead of the v1.0.0 pentagon
4. Drag the outer top point outward to widen the beam at amidships
5. Close the sketch, recompute (F5)
6. Hull recomputes with the new shape

The arc's center point can also be dragged to change the bilge radius without changing the beam.

The Stem sketch (`HullStationStem`) is now a **rectangle** (5 line segments) instead of a degenerate point. Double-clicking it lets you edit the stem face dimensions directly.

---

## 5. Verify the B-spline loft mode

Select `HullLoft` (PartDesign::AdditiveLoft) in the tree. In the Property panel under "Loft":

```
Ruled       : false  ← was: true in v1.0.0
Closed      : false
```

The `Ruled = false` setting is the smooth B-spline interpolation. If you see `Ruled = true` instead, the auto-fall-back was triggered — check the build's stderr for a `WARNING` line like:

```
WARNING:root:PartDesign::AdditiveLoft Ruled=False produced invalid shape ... falling back to Ruled=True
```

That happens only for extreme `HullParameters` combinations the B-spline interpolator can't handle. For defaults (Storebro RC34 1972), the smooth loft works.

---

## 6. Out-of-envelope stem rake

The new `stem_rake_angle` parameter has a `[0, 30]` degree range:

```python
from storebro import build_hull, HullParameters

# Default — 6° forward rake
hull = build_hull()

# Plumb stem (vertical bow)
hull = build_hull(HullParameters(stem_rake_angle=0.0))

# Strongly raked clipper-style bow
hull = build_hull(HullParameters(stem_rake_angle=20.0))

# Out of range — raises HullParameterError
try:
    build_hull(HullParameters(stem_rake_angle=45.0))
except Exception as e:
    print(f"Error: {e}")
# Error: HullParameterError: stem_rake_angle = 45.0 is outside the valid range [0, 30] degrees
```

---

## 7. Visual signoff workflow

After v1.0.1 lands:

```bash
# 1. Build the signoff artifact
uv run storebro build --out storebro_v1.0.1_signoff.FCStd

# 2. Open in FreeCAD GUI
open storebro_v1.0.1_signoff.FCStd
# Press 3 for right-side view

# 3. Compare against the reference
open docs/references/Alternativ3.JPG
# Look at the upper half — the side-profile drawing

# 4. Capture screenshot, save to docs/signoff/ (gitignored)
# 5. Record the constitution V line in the v1.0.1 release commit:
#    "Visually verified in FreeCAD: 1.1.x on macOS arm64 — silhouette matches Alternativ3.JPG within tolerance"
```

---

## 8. What's NOT changed by spec 007

- `Hull` dataclass shape (5 fields)
- `build_hull()` signature
- `HullParameterError` / `HullConstructionError` attribute shapes
- The CLI's exit-code dispatch
- The PartDesign feature graph topology (5 datums + 5 sketches + AdditiveLoft + Mirrored)
- Rollback discipline on construction failure
- The constitution's principle II / III / V / VI / VII

---

## 9. What's NOT in scope for spec 007

- Hard chine variant (`HullModule.hard_chine_variant`) — v1.1+
- Compound cubic-spline bilge curves (`HullModule.compound_curved_sections`) — v1.1+
- Lines-drawing-level fidelity (`HullModule.body_plan_from_primary_source`) — v1.1+ if primary source is acquired
- Expression-engine bindings between Body properties and sketch constraints — deferred from spec 006
- Full-assembly STEP/STL/BREP export — deferred from spec 005
- Cross-invocation FCStd byte determinism — deferred from spec 006

---

## Where to next

- **Verify your install**: `uv run storebro info`
- **Build the canonical boat**: `uv run storebro build --out boat.FCStd`
- **Refresh hash baselines**: `uv run python tests/geometry/fixtures/refresh_hashes.py && git diff tests/geometry/fixtures/expected_hashes.toml`
- **Re-run all tests**: `uv run pytest`
- **Tag v1.0.1**: `git tag v1.0.1` after visual signoff
