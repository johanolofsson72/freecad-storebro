# Research: PartDesign Hull Upgrade (Phase 0)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-17

---

## R1. Why the v0.1.0-alpha fails on FreeCAD 1.1+

### Diagnosis (confirmed empirically on 2026-05-17)

```
HullConstructionError: FreeCAD failed to construct hull with parameters
  HullParameters(loa=10.35, beam_max=3.2, ...) — ValueError: Body: object is not allowed
```

The error originates from `body.addObject(loft)` at `src/storebro/hull.py:427`. The current implementation creates `Part::Loft`, `Part::Mirroring`, and `Part::MultiFuse` as document children (via `parent_doc.addObject(...)`), then attempts to add them to a `PartDesign::Body` container (via `body.addObject(...)`).

FreeCAD 1.1+ enforces that `PartDesign::Body` containers accept only feature types that derive from `PartDesign::Feature`. Legacy Part-workbench types (`Part::Loft`, `Part::Mirroring`, `Part::MultiFuse`, `Part::Feature`) do NOT inherit from `PartDesign::Feature` and are rejected at `addObject` time.

### Consequence

Every single `build_hull()` call fails before producing any output. 86 of 87 geometry tests fail because they all transitively call `build_hull()`. The CLI's `storebro build` command exits with code 2. The whole library is non-functional on a real FreeCAD host.

---

## R2. Decision: PartDesign-only feature graph

### Decision

Replace the legacy feature graph with PartDesign-only features:

| Legacy v0.1.0-alpha | PartDesign v1.0.0 |
|---|---|
| `parent_doc.addObject("Part::Feature", "Sketch_X")` with manual `Part.Shape` | `body.newObject("Sketcher::SketchObject", "HullStationN")` + `body.newObject("PartDesign::Plane", "HullDatumN")` |
| `parent_doc.addObject("Part::Loft", "HullLoft")` | `body.newObject("PartDesign::AdditiveLoft", "HullLoft")` |
| `parent_doc.addObject("Part::Mirroring", "HullMirror")` | `body.newObject("PartDesign::Mirrored", "HullMirror")` |
| `parent_doc.addObject("Part::MultiFuse", "HullFusion")` | (removed — `PartDesign::Mirrored` produces the closed full-hull directly) |
| `body.addObject(feature)` (FAILS) | `body.newObject(...)` adds the feature to the Body in one call |

The `Body.newObject(type_id, name)` API atomically creates the feature AND adds it to the Body. It is the PartDesign-idiomatic way to populate a Body; trying to create via the document and then `addObject` is exactly what triggers the legacy-feature rejection.

### Rationale

- `body.newObject` is supported on every FreeCAD version in the supported range (≥1.1, <2.0). Verified by inspecting FreeCAD's source: `PartDesign::Body.newObject` has been a documented API since FreeCAD 0.19.
- All four feature types (`Sketcher::SketchObject`, `PartDesign::Plane`, `PartDesign::AdditiveLoft`, `PartDesign::Mirrored`) are PartDesign-valid and accepted by `PartDesign::Body.newObject`.
- No legacy Part-workbench features survive; spec.allium invariant `NoLegacyPartFeaturesInsideBody` becomes trivially true.

### Alternatives considered

- **Keep PartDesign::Body but populate features at the document level via `parent_doc.addObject`**: rejected — this is exactly what v0.1.0-alpha did. The Body is then decorative; `Body.Tip` cannot point at a feature that isn't a Body child.
- **Drop the PartDesign::Body wrapper entirely; use a plain Part::Compound**: rejected — violates constitution principle III (FreeCAD-idiomatic uses PartDesign Body for parametric history). Also breaks the eight named-property contract (Bodies hold properties; Compounds don't).
- **Use PartDesign::Body but build geometry with the Sketcher + Draft workbench (no AdditiveLoft)**: rejected — Draft features (`Draft::Wire`, etc.) are not PartDesign-derived. Same rejection problem.

---

## R3. Decision: 5 separate datum planes, Body-local origin frame

### Decision

For each of the five stations, create a dedicated `PartDesign::Plane` datum that:
1. Lives as a child of the `PartDesign::Body` (created via `body.newObject("PartDesign::Plane", ...)`).
2. Attaches to the Body's local `Origin.YZ_Plane` (the YZ reference plane of the Body's coordinate system).
3. Has an `AttachmentOffset` that places it at the station's X coordinate along the hull.

The station sketches each attach to their dedicated datum plane (via `sketch.AttachmentSupport = datum; sketch.MapMode = "FlatFace"` or equivalent).

### Rationale (Q1 clarify auto-pick)

- Body-local attachment keeps everything self-contained inside the Body. If a user moves the Body in the document (e.g., to position multiple hulls side-by-side), every sketch and datum moves with it.
- The Body's `Origin` object (auto-created when the Body is instantiated) provides `Origin.XY_Plane`, `Origin.XZ_Plane`, `Origin.YZ_Plane`, plus axis references. The YZ plane is the natural reference for station sketches (which lie in the YZ plane translated along X).
- This is the FreeCAD-idiomatic PartDesign convention — matches how a user building a hull manually would set up the feature tree.

### Alternatives considered

- **All five sketches on a single shared YZ datum plane**: rejected — `PartDesign::AdditiveLoft` requires each profile to be on its own sketch (and typically its own plane); FreeCAD will not loft between two sketches on the same datum without re-anchoring.
- **Document's global XZ plane as reference**: rejected per Q1 clarify — Body-local is more idiomatic and preserves the move-the-Body semantics.

---

## R4. Decision: `Body.Tip = mirror_feature` (sets the Body's output shape)

### Decision

After creating the `PartDesign::Mirrored` feature, set `body.Tip = mirror_feature`. The `Tip` property of a `PartDesign::Body` determines which feature's shape is exposed as `body.Shape` (the closed full-hull solid).

### Rationale

- `body.Shape` reads from `body.Tip.Shape`. If `Tip` is unset, FreeCAD picks the last feature added, which may or may not be the mirror. Explicit assignment is the safe, deterministic approach.
- The mirror is the only feature that produces the closed full-hull; the additive loft produces only the half-hull (port side). Setting Tip to the loft would expose a half-hull through `body.Shape`, breaking every downstream consumer (deck, interior, export).
- spec.allium invariant `BodyTipIsMirror` and FR-013 both pin this contract.

### Alternatives considered

- **Set `Body.Tip` to the additive loft (port half-hull only)**: rejected — would only export half the boat to STEP/STL/BREP and would confuse downstream modules that expect a closed solid.
- **Don't set Tip; let FreeCAD pick**: rejected — non-deterministic; could break across FreeCAD point releases.

---

## R5. Decision: Sketcher-based profile reconstruction

### Decision

Each station sketch is constructed by:
1. `body.newObject("Sketcher::SketchObject", f"HullStation{name}")`.
2. Attach to its dedicated datum plane (`sketch.AttachmentSupport = (datum_plane, "")`, `sketch.MapMode = "FlatFace"`).
3. Add construction geometry via `sketch.addGeometry(...)` calls — line segments for non-terminal stations, a single vertical line for the terminal stem.
4. Add constraints (`sketch.addConstraint(...)`) to lock the geometry's dimensions to values derived from the v0.1.0-alpha `_compute_stations` profile data.

Profile equations are NOT re-derived — they come from the existing `_StationProfile` dataclass + `_compute_stations(p: HullParameters)` function (already in `src/storebro/hull.py` lines 217-318). Only the FreeCAD construction mechanics around those profiles changes.

### Rationale

- Constitution principle III: parametric Sketcher constraints are the FreeCAD-idiomatic way to express dimensional intent. A user opening the sketch in the GUI sees the same dimensions a hand-built sketch would have.
- US2 (GUI editability) requires sketch handles draggable in the sketcher view. Locked construction geometry without dimensional constraints wouldn't satisfy this.
- Reusing `_compute_stations` preserves reference fidelity (FR-014) without re-derivation — the profile math has already been validated against the RC34 1972 reference.

### Alternatives considered

- **Use `Part.Wire` shape assignment via `sketch.Shape = ...`**: rejected — that's the v0.1.0-alpha pattern; it produces a `Part::Feature`, not a `Sketcher::SketchObject`, and breaks Body acceptance.
- **Define each station as a separate parametric extrusion direction**: rejected — over-engineered; AdditiveLoft handles the cross-station interpolation natively.

---

## R6. Decision: Stem station as a single vertex

### Decision

The stem station (X = LOA, where the bow centerline meets the deck-keel) collapses to a single point — `half_beam = 0`, `keel_depth = 0`. Represent this in the sketch as a single zero-dimension geometric primitive (point or zero-length line) that `PartDesign::AdditiveLoft` can interpret as a degenerate end profile.

### Rationale

- FreeCAD's `PartDesign::AdditiveLoft` accepts degenerate end profiles (a single point or a sketch with no closed wire) as the loft's start or end shape. The result is a pointed end on the loft — exactly the shape of a hull's bow.
- Matches the v0.1.0-alpha `_StationProfile(is_terminal=True)` semantic — same data, different construction mechanics.

### Alternatives considered

- **Use a tiny non-zero half-beam at the stem (e.g., 1 mm) to avoid degeneracy**: rejected — produces a blunt bow instead of a pointed one; violates reference fidelity.
- **Skip the stem profile and let AdditiveLoft interpolate to infinity**: rejected — produces an open loft, not a closed solid.

---

## R7. Decision: Rollback discipline mirrors spec 003 deck pattern

### Decision

`build_hull()` tracks every document object created during construction in a local `added: list[Any]` list. If any FreeCAD call (sketch creation, geometry add, constraint add, datum plane create, additive loft, mirror, recompute) raises, the existing `except BaseException` handler in `build_hull` (lines 591-597) is augmented to remove each object in reversed order before re-raising as `HullConstructionError`.

### Rationale

- Mirror spec 003's deck rollback discipline (which is already proven to leave the document clean on failure).
- FR-012 + spec.allium `RollbackOnConstructionFailure` rule mandate clean document state on failure.
- The reversed-order removal ensures FreeCAD's `Group` and `Tip` references are unwound in the same order they were established — avoids dangling references.

### Alternatives considered

- **Build hull in a separate scratch document and only copy on success**: rejected — adds significant complexity for a corner case; FreeCAD's `Document.copyObject` cross-document semantics are non-trivial.
- **Roll forward on partial failure**: rejected — violates the no-half-built-Body requirement; the user would see corrupted parametric history.

---

## R8. Decision: Hash baselines refreshed in this spec's polish phase

### Decision

The PartDesign feature graph is structurally different from the legacy Part-workbench graph. The resulting `.FCStd` archive contents differ byte-for-byte (different feature types, different XML serialization, different recompute order). Hash baselines in `tests/geometry/fixtures/expected_hashes.toml` MUST be refreshed via the existing `tests/geometry/fixtures/refresh_hashes.py` script as part of this spec's polish phase, then the new baselines committed.

The byte-determinism guarantee (constitution II) is preserved at the new baselines: two consecutive builds with identical parameters produce identical bytes; only the cross-spec-version comparison changes.

### Rationale

- The legacy baselines are invalid the moment the implementation changes; running tests against them would be a false negative.
- Refresh on a FreeCAD-equipped host (developer laptop / CI runner with FreeCAD installed) using `uv run python tests/geometry/fixtures/refresh_hashes.py`.
- Eyeball the diff (visual diff of the TOML file) to confirm hashes are plausible (64-char hex strings, no obvious corruption) before committing.

### Alternatives considered

- **Skip the hash regression test in v1.0.0 and add it back in v1.1+**: rejected — the byte-determinism guarantee is constitution II (NON-NEGOTIABLE); regression test must remain.
- **Leave baselines blank and have tests auto-generate-and-compare in a single run**: rejected — would mask future drift by making the first run always pass.

---

## Summary of decisions

| ID | Decision | Resolves |
|---|---|---|
| R1 | Root cause: legacy Part features rejected by PartDesign Body | Diagnostic |
| R2 | PartDesign-only feature graph via `body.newObject` | FR-001 / FR-002 / FR-010 |
| R3 | 5 separate datum planes, attached to Body-local Origin.YZ_Plane | FR-002 / Q1 clarify |
| R4 | `Body.Tip = mirror_feature` for full-hull shape exposure | FR-013 |
| R5 | Sketcher-based profile reconstruction, reusing `_compute_stations` | FR-003 / FR-004 / FR-014 |
| R6 | Stem station as degenerate single-point profile | FR-007 / reference fidelity |
| R7 | Rollback discipline mirrors spec 003 deck pattern | FR-012 |
| R8 | Hash baselines refreshed in polish phase | FR-008 / SC-004 |

All NEEDS CLARIFICATION resolved.
