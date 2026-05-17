# Quickstart: PartDesign Hull Upgrade

**Spec**: [spec.md](./spec.md) | **Contract**: [contracts/python-api-preserved.md](./contracts/python-api-preserved.md) | **Date**: 2026-05-17

A walkthrough of what changes for users after spec 006 lands. The public Python and CLI API surfaces are unchanged; what changes is what you see when you open the generated `.FCStd` in the FreeCAD GUI.

---

## 1. Build a hull (same command as before)

```bash
uv run storebro build --out boat.FCStd
```

Expected output:

```
wrote fcstd to /Users/you/boat.FCStd (192884 bytes, SHA-256 4a1e9b...)
```

Exit code 0. File exists. The CLI invocation is byte-identical to spec 005's behavior — what changed is what's inside the file.

---

## 2. Open the file in FreeCAD GUI

```bash
open boat.FCStd     # macOS — or just double-click in Finder
```

In the FreeCAD tree view (left panel), expand the document:

```
boat
└── HullBody  (PartDesign Body)
    ├── Origin (the Body's local coordinate system)
    │   ├── X_Axis / Y_Axis / Z_Axis
    │   └── XY_Plane / XZ_Plane / YZ_Plane
    ├── HullDatumTransom    (PartDesign Plane at X = 0)
    ├── HullDatumAft        (PartDesign Plane at X = 2.59 m)
    ├── HullDatumAmidships  (PartDesign Plane at X = 5.18 m)
    ├── HullDatumFwd        (PartDesign Plane at X = 7.76 m)
    ├── HullDatumStem       (PartDesign Plane at X = 10.35 m)
    ├── HullStation1        (Sketch on HullDatumTransom)
    ├── HullStation2        (Sketch on HullDatumAft)
    ├── HullStation3        (Sketch on HullDatumAmidships)
    ├── HullStation4        (Sketch on HullDatumFwd)
    ├── HullStation5        (Sketch on HullDatumStem — degenerate point)
    ├── HullLoft            (PartDesign AdditiveLoft — port half-hull)
    └── HullMirror          (PartDesign Mirrored — full closed hull) ← Body.Tip
```

The Body's tip (the feature whose shape is exposed as `Body.Shape`) is `HullMirror`. That's what you see rendered in the 3D view.

---

## 3. Inspect the named informational properties

Select `HullBody` in the tree. In the Property panel (bottom-right by default):

```
Hull
├── LOA               : 10.35 m
├── BeamMax           :  3.20 m
├── Draft             :  0.95 m
├── Freeboard         :  0.95 m
├── DeadriseAmidships : 16.00 °
├── SheerHeightAft    :  0.85 m
├── SheerHeightFwd    :  1.30 m
└── TransomAngle      : 12.00 °
```

These reflect the parameters used to build the hull. **They are informational only for v1.0.0** — editing them in the GUI does NOT propagate to the sketches (per clarify Q2; bidirectional binding is deferred to v1.1+).

---

## 4. Edit a station sketch (the actual parametric editing path)

To change the hull's shape:

1. **Double-click `HullStation3`** in the tree (the amidships sketch). The sketcher view opens.
2. **Select a handle** — for example, the outer-top point at `(BeamMax/2, 0)`.
3. **Drag the handle** to a new position (e.g., move it 100 mm outward to widen the beam at amidships).
4. **Click OK / Close Sketch** to exit the sketcher.
5. **Right-click `HullBody` → Recompute** (or press F5 with the document selected).

The hull deforms — the additive loft re-interpolates between stations, and the mirror reflects the new half-hull. You see the change in the 3D view in real time.

Each station sketch can be edited independently. Constraints in each sketch lock the construction geometry against the station's parameters (deriving from `_compute_stations(p)` per the v0.1.0-alpha math).

---

## 5. Export to a different format (unchanged from spec 005)

```bash
uv run storebro build --format step --out boat.step
uv run storebro build --format stl --out boat.stl --tessellation 0.0005
uv run storebro build --format brep --out boat.brep
```

Note: STEP/STL/BREP export the hull body only (per spec 005's FR-004 + `deferred Cli.full_assembly_in_non_fcstd_export`). The Body's shape (read from `Body.Tip = HullMirror`) is the full closed hull — that's what gets exported.

---

## 6. Verify the feature graph from Python

If you want to confirm the PartDesign feature graph programmatically:

```python
from storebro import build_hull

hull = build_hull()

# Body is a PartDesign Body
assert hull.body.TypeId == "PartDesign::Body"

# Tip is the mirror feature
assert hull.body.Tip.TypeId == "PartDesign::Mirrored"

# Group contains all the children
type_ids = sorted({obj.TypeId for obj in hull.body.Group})
assert "PartDesign::Plane" in type_ids
assert "Sketcher::SketchObject" in type_ids
assert "PartDesign::AdditiveLoft" in type_ids
assert "PartDesign::Mirrored" in type_ids

# No legacy Part-workbench features anywhere in the Body
legacy = {"Part::Loft", "Part::Mirroring", "Part::MultiFuse", "Part::Feature"}
assert not (set(type_ids) & legacy)

# Eight named properties on the Body, same as v0.1.0-alpha
for name in ("LOA", "BeamMax", "Draft", "Freeboard",
            "DeadriseAmidships", "SheerHeightAft", "SheerHeightFwd",
            "TransomAngle"):
    assert hasattr(hull.body, name)
```

This is the same surface every downstream module (deck, interior, export, CLI) sees.

---

## 7. What's NOT changed by spec 006

- `Hull` dataclass shape (5 fields).
- `HullParameters` defaults (RC34 1972 dimensions).
- `HullParameterError` / `HullConstructionError` attribute shape.
- The CLI's exit-code dispatch (1 = input, 2 = system).
- The byte-determinism guarantee (constitution II) — same parameters still produce identical bytes; only the bytes themselves changed.
- The 30-second hull-construction budget (SC-002).
- The ±1% reference-fidelity tolerance for LOA / beam / draft (constitution IV).

---

## 8. What's NOT in scope for spec 006

- Bidirectional expression-engine bindings (`body.LOA = 11.0` doesn't propagate to sketches — v1.1+).
- Keel longitudinal Pad or other net-new geometric features (v1.1+).
- Adaptive station spacing for extreme parameter combinations (v1.1+).
- Multi-format CLI export (`--format all` — already deferred in spec 005).

---

## Where to next

- **Run the geometry tests**: `uv run pytest -m requires_freecad -v` — all 86 currently-failing tests should turn green.
- **Refresh hash baselines**: `uv run python tests/geometry/fixtures/refresh_hashes.py && git diff tests/geometry/fixtures/expected_hashes.toml`.
- **Visual signoff for v1.0.0**: open `/tmp/storebro_v1_signoff.FCStd` in FreeCAD GUI, eyeball against `docs/references/Alternativ3.JPG`, capture the "Visually verified in FreeCAD: 1.1.x on macOS arm64 — dragged HullStation3 handle, hull recomputed" PR description note.
- **Tag v1.0.0**: `git tag v1.0.0` (the constitution's milestone).
