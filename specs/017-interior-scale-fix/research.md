# Phase 0 Research: Interior Scale Fix

No open `NEEDS CLARIFICATION` items — the spec is fully bounded. The only research is confirming the established convention the fix must match.

## Decision 1 — Conversion convention: reuse the hull's metre→millimetre pattern

- **Decision**: Convert metre-authored layout values to millimetres at the geometry-construction boundary via a single module-level constant `_M_TO_MM = 1000.0`, mirroring `hull._MM_PER_M = 1000.0` (`src/storebro/hull.py:569`).
- **Rationale**: The hull is the canonical correct reference — it multiplies every metre coordinate by `_MM_PER_M` before `Part`/`Sketch` construction (e.g. `profile.x_position * _MM_PER_M`, `keel_depth * _MM_PER_M`) and FreeCAD's internal length unit is millimetres. Matching the hull's convention guarantees the interior and hull share one coordinate system and satisfies constitution I (named constant, no scattered magic `1000`).
- **Alternatives considered**:
  - *Scale the whole interior with a single `Part` transform after construction* — rejected: hides the convention, complicates the per-piece envelope/manifold guards, and risks float-path divergence from the hull's per-coordinate multiply (reproducibility risk).
  - *Author fixtures in millimetres* — rejected: FR-006 forbids a fixture/schema change; metres are the human-readable authoring unit and the validators compare against hull parameters in metres.

## Decision 2 — Validators stay in metre-space

- **Decision**: `_validate_compartment_in_envelope`, `_validate_no_overlaps` (`_aabb_intersection_volume`), and `_validate_furniture_envelope` keep operating on metre-space layout values vs metre-space hull parameters.
- **Rationale**: They compare layout values against `hull.parameters` (LOA, beam_max, draft, sheer heights), all in metres. Converting validation to millimetres would require re-deriving every comparison and gains nothing — the accept/reject outcome is invariant under a uniform scale (FR-007). Keeping them in metres minimises the diff and the regression surface.
- **Consequence**: `_validate_furniture_envelope` continues to convert its mm furniture params *down* to metres for the height comparison (its own local conversion), independent of the geometry-path `_M_TO_MM`. The two conversions are deliberately separate: validation in metres, construction in millimetres.

## Decision 3 — GUI display properties are already millimetres; do not double-scale

- **Decision**: Leave `obj.Length/Width/Height = spec.dimensions.* * 1000.0` (`interior.py:836-838`) unchanged.
- **Rationale**: Those `App::PropertyLength` properties were always set in millimetres (matching the hull's `body.LOA = parameters.loa * 1000.0` pattern). Before the fix they were correct-but-inconsistent with the metre-magnitude shape; after the fix the shape is also millimetres, so the property and the geometry agree (FR-008). Adding another ×1000 would over-scale the display to 1000× the geometry.

## Decision 4 — Spec-only track, scale invariant expressed as a test

- **Decision**: No `.allium` file, no TLA+ model. The corrected-scale invariant is a pytest regression (FR-012) plus a hull-containment check (SC-003).
- **Rationale**: The fix introduces no new entities and no new state transitions — it changes the magnitude of existing geometry. Per `specs.md` triage and `allium.md`, forcing elicitation here would fabricate a `.allium` that surfaces as false drift. The test-as-invariant approach matches the precedent for fix/hardening specs.
