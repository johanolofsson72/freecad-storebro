# Phase 1 Data Model: Interior Scale Fix

**No new entities, no field changes, no schema changes.** This is a spec-only-track scale correction.

## Existing entities (unchanged in shape, corrected in emitted scale)

| Entity | Authoring unit (YAML / params) | Emitted geometry before fix | Emitted geometry after fix |
|---|---|---|---|
| `Position3D` (x, y, z) | metres | used raw → metre-magnitude | × `_M_TO_MM` → millimetre-magnitude |
| `Dimensions3D` (length, width, height) | metres | used raw → metre-magnitude | × `_M_TO_MM` → millimetre-magnitude |
| `CompartmentSpec` / `LayoutSpec` | metres | n/a (parsed values) | unchanged — parsed in metres, converted only at construction |
| `BerthParameters`, `GalleyParameters`, `HeadParameters`, `SalonParameters`, `BulkheadParameters` | millimetres | × `1/1000` → metre-magnitude (to match broken boxes) | used at face value → millimetre-magnitude |
| `Compartment` / `Interior` aggregates | n/a | wraps metre-magnitude `Shape` | wraps millimetre-magnitude `Shape` |

## Invariants preserved (metre-space, unchanged)

- **Envelope containment**: `position.x ≥ 0`, `position.x + length ≤ loa`, `width ≤ beam_max`, `position.z ≥ -draft`, `position.z + height ≤ sheer_height_fwd + 1.5` — all compared in metres.
- **No overlap**: pairwise AABB intersection volume `≤ 1e-6 m³` — computed in metres.
- **Furniture fit**: berth/galley heights `<` compartment height — compared in metres (furniture mm converted down for the check).
- **Galley manifold**: cut worktop is a single valid solid — scale-invariant (`Solids == 1`, `isValid()`).
- **Rollback**: failed build removes all added objects — unaffected by scale.

## New invariant (post-fix, expressed as a test — FR-012 / SC-001)

- **Corrected scale**: a compartment authored as `length = L` metres yields `Shape.BoundBox.XLength ≈ L × 1000` millimetres (±1%). Regression-tested against the Alternativ1 forward cabin (2.4 m → ~2400 mm).
- **Hull containment** (SC-003): the interior's combined X-Y footprint is contained within the hull's bounding box and its floor sits above the keel (Z is bounded below by the keel, not above by the hull sheer — the cabin interior rises into the superstructure headroom the envelope validator allows).
