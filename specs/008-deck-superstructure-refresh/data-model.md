# Data Model: Deck Superstructure Refresh

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-18

Entities, fields, validation, relationships. All units in this document are mm and degrees unless noted. Defaults are derived from `research.md` §R1 (`docs/references/Alternativ3.JPG` at LOA = 10360 mm).

## §1 Parameter dataclasses (frozen, validated at construction)

All five sub-dataclasses use `@dataclass(frozen=True)` with a `__post_init__` validator. Field types are `float` (millimeters) or `int` (counts). Field defaults match R1.

### 1.1 `CabinTrunkParameters`

| Field | Type | Default (mm) | Constraint |
|---|---|---|---|
| `length` | float | 4600.0 | `> 0` |
| `forward_width` | float | 1900.0 | `> 0`, `≤ aft_width` |
| `aft_width` | float | 2150.0 | `> 0` |
| `height` | float | 1100.0 | `> 0` |
| `forward_rake_angle` | float | 8.0 (degrees) | `0 ≤ x ≤ 45` |
| `aft_rake_angle` | float | 2.0 (degrees) | `-15 ≤ x ≤ 30` |
| `wall_inset` | float | 350.0 | `≥ 0` |

Cross-field: `forward_width ≤ aft_width` (TaperedSilhouette invariant — spec.allium §value CabinTrunkParameters).

### 1.2 `WindshieldParameters`

| Field | Type | Default (mm) | Constraint |
|---|---|---|---|
| `base_z` | float | 0.0 | (relative to cabin trunk top; can be negative for sub-cabin-top windshields, not in scope) |
| `top_z` | float | 750.0 | `> base_z` |
| `rake_angle_base` | float | 35.0 (degrees) | `-10 ≤ x ≤ 60` |
| `rake_angle_top` | float | 38.0 (degrees) | `-10 ≤ x ≤ 60` |
| `base_width` | float | 2050.0 | `> 0` |
| `top_width` | float | 1800.0 | `> 0`, `≤ base_width` |
| `thickness` | float | 25.0 | `> 0` |

Cross-field: `top_z > base_z`, `top_width ≤ base_width`.

Derived (computed for validation): `windshield_curvature_radius = (top_z - base_z) / (cos(rake_angle_base) - cos(rake_angle_top))` if rakes differ; if equal, infinite radius (straight). Computed value must be `≥ 200 mm` (RejectSubMinimumWindshieldCurvature rule).

### 1.3 `HardtopParameters`

| Field | Type | Default (mm) | Constraint |
|---|---|---|---|
| `length` | float | 3700.0 | `> 0` |
| `forward_width` | float | 2200.0 | `> 0` |
| `aft_width` | float | 2000.0 | `> 0`, `≤ forward_width` |
| `thickness` | float | 60.0 | `> 0` |
| `height_above_deck` | float | 2050.0 | `> 0` |
| `leading_edge_curl_depth` | float | 80.0 | `≥ 0`, `≤ height_above_deck` |
| `leading_edge_curl_length` | float | 250.0 | `≥ 0`, `≤ length` |

### 1.4 `PillarParameters`

| Field | Type | Default | Constraint |
|---|---|---|---|
| `count_per_side` | int | 2 | `≥ 0` |
| `diameter` | float | 35.0 mm | `> 0` |
| `forward_x` | float | 5400.0 mm | `< aft_x` |
| `aft_x` | float | 7800.0 mm | `> forward_x` |
| `inboard_offset_from_sheer` | float | 80.0 mm | `≥ 0` |

### 1.5 `RailingParameters`

| Field | Type | Default | Constraint |
|---|---|---|---|
| `post_count_per_side` | int | 6 | `≥ 0` |
| `post_diameter` | float | 25.0 mm | `> 0` |
| `top_rail_diameter` | float | 30.0 mm | `> 0` |
| `height_above_deck` | float | 720.0 mm | `> 0`, `< hardtop.height_above_deck` (cross-dataclass invariant — see §1.6) |
| `forward_x` | float | 0.0 mm | `< aft_x` |
| `aft_x` | float | 9800.0 mm | `> forward_x` |
| `inboard_offset_from_sheer` | float | 60.0 mm | `≥ 0` |

### 1.6 `DeckSuperstructureParameters` (composite)

| Field | Type | Default |
|---|---|---|
| `cabin_trunk` | `CabinTrunkParameters` | `CabinTrunkParameters()` |
| `windshield` | `WindshieldParameters` | `WindshieldParameters()` |
| `hardtop` | `HardtopParameters` | `HardtopParameters()` |
| `pillars` | `PillarParameters` | `PillarParameters()` |
| `railings` | `RailingParameters` | `RailingParameters()` |

Cross-component invariants (checked in `__post_init__`):

- `railings.height_above_deck < hardtop.height_above_deck` — railings cannot pierce the hardtop.
- `pillars.forward_x ≥ cabin_trunk.length` — pillars cannot fall inside the cabin trunk footprint (per the X-origin convention where cabin trunk starts at X=0).
- `hardtop.forward_x_resolved + hardtop.length ≤ hull.loa_mm` — hardtop fits within hull length (checked in `build_deck`, not in `__post_init__`, because the dataclass doesn't see the hull).

### 1.7 Legacy `DeckParameters` (preserved unchanged, plus shim method)

The existing 14-field `DeckParameters` dataclass at `src/storebro/deck.py:142` is preserved verbatim. One method is added:

```python
def to_superstructure_parameters(self) -> DeckSuperstructureParameters:
    """Map legacy 14-field DeckParameters onto the 6 new dataclasses.

    See specs/008-deck-superstructure-refresh/research.md §R4 for the
    exact field-by-field translation.
    """
```

The shim is deterministic, has no I/O, no time, no env — preserves constitution II (reproducibility).

## §2 Output entities (FreeCAD Bodies)

### 2.1 `CabinTrunkBody`

```python
@dataclass(frozen=True)
class CabinTrunkBody:
    body: Any  # FreeCAD PartDesign::Body
    parameters: CabinTrunkParameters
    forward_x_mm: float  # absolute X coord of forward face, set by build_deck
    aft_x_mm: float      # absolute X coord of aft face
```

Required runtime invariants (asserted by geometry tests):

- `body.TypeId == "PartDesign::Body"`
- `body.Shape.Volume > 0`
- `body.Shape.BoundBox.XMax - body.Shape.BoundBox.XMin ≈ parameters.length` (within 1%)
- `body.Shape.BoundBox.ZMax - body.Shape.BoundBox.ZMin ≈ parameters.height` (within 1%)

### 2.2 `WindshieldBody`

```python
@dataclass(frozen=True)
class WindshieldBody:
    body: Any  # FreeCAD PartDesign::Body containing a single AdditiveLoft
    parameters: WindshieldParameters
    is_lofted_between_two_edges: bool  # always True post-construction
```

Required runtime invariants:

- `body.TypeId == "PartDesign::Body"`
- Body's Tip is a `PartDesign::AdditiveLoft`.
- The AdditiveLoft has exactly 2 cross-section sketches (port and starboard B-splines).
- `body.Shape.Volume > 0`

### 2.3 `HardtopBody`

```python
@dataclass(frozen=True)
class HardtopBody:
    body: Any
    parameters: HardtopParameters
    forward_x_mm: float
    aft_x_mm: float
    underside_z_forward_mm: float  # forward edge Z, reduced by curl depth
    underside_z_aft_mm: float      # aft edge Z (curl does not affect aft)
```

Required runtime invariants:

- `body.TypeId == "PartDesign::Body"`
- Body's Tip is a `PartDesign::AdditiveLoft` or boolean of curl-loft + main-loft.
- Aft taper: `parameters.aft_width < parameters.forward_width` reflected in body width at aft station.
- Leading-edge curl: if `parameters.leading_edge_curl_depth > 0`, the forward edge has lower underside_z than the aft edge.

### 2.4 `PillarBody`

```python
@dataclass(frozen=True)
class PillarBody:
    body: Any
    parameters: PillarParameters
    longitudinal_x_mm: float
    is_port: bool                    # True for port side (positive Y), False for starboard
    deck_top_z_at_x_mm: float        # actual deck plate top Z, sourced via _resolve_deck_top_z_at
    hardtop_underside_z_at_x_mm: float  # actual hardtop underside Z at this X
```

Required runtime invariants:

- `body.TypeId == "PartDesign::Body"`
- Body's Tip is a `PartDesign::Pad` extruding a circular sketch.
- **Seating invariant (P1 correctness)**: `body.Shape.BoundBox.ZMin ≥ deck_top_z_at_x_mm - 1.0`. No pillar geometry below the deck plate top surface.
- **Top invariant**: `body.Shape.BoundBox.ZMax ≈ hardtop_underside_z_at_x_mm` within 1 mm.
- **Vertical centerline**: pillar Pad direction is `(0, 0, 1)` (constant Z-axis).
- `body.Shape.Volume > 0`

### 2.5 `RailingBody`

```python
@dataclass(frozen=True)
class RailingBody:
    body: Any
    parameters: RailingParameters
    is_port: bool
```

Required runtime invariants:

- `body.TypeId == "PartDesign::Body"`
- Body contains a sweep (top rail) + N pads (posts) where N = `parameters.post_count_per_side`.
- `body.Shape.Volume > 0`

### 2.6 `Deck` (the existing return aggregate — extended)

The existing `Deck` dataclass at `src/storebro/deck.py:327` is preserved in name and field-name shape. Its sub-Body fields are now typed against the new entities:

```python
@dataclass(frozen=True)
class Deck:
    parameters: DeckParameters             # legacy 14-field dataclass (preserved)
    parameters_superstructure: DeckSuperstructureParameters  # NEW — the 6-dataclass composite
    hull: Hull
    document: Any
    label: str
    build_duration_seconds: float
    deck_plate: DeckPlate                  # unchanged
    cabin_trunk: CabinTrunk                # legacy wrapper, now reshaped underneath
    windshield: Windshield                 # legacy wrapper, now PartDesign-backed
    hardtop: Hardtop                       # legacy wrapper, now PartDesign-backed
    hardtop_pillars: HardtopPillars        # legacy wrapper, now a list of PillarBody
    railings: Railings                     # legacy wrapper, now PartDesign-backed
```

Field additions are *additive only*. Existing field names + types are preserved per FR-024 + R4.

## §3 Relationships

```text
Deck
├── parameters: DeckParameters (legacy, 14 fields)
├── parameters_superstructure: DeckSuperstructureParameters
│   ├── cabin_trunk: CabinTrunkParameters
│   ├── windshield: WindshieldParameters
│   ├── hardtop: HardtopParameters
│   ├── pillars: PillarParameters
│   └── railings: RailingParameters
├── hull: Hull (from spec 001/006/007)
├── document: FreeCAD document
├── deck_plate: DeckPlate (unchanged from v1.0.1)
├── cabin_trunk: CabinTrunk (legacy wrapper → CabinTrunkBody underneath)
├── windshield: Windshield (legacy wrapper → WindshieldBody underneath)
├── hardtop: Hardtop (legacy wrapper → HardtopBody underneath)
├── hardtop_pillars: HardtopPillars (legacy wrapper → list[PillarBody] underneath)
└── railings: Railings (legacy wrapper → RailingBody underneath)
```

The legacy wrappers (`CabinTrunk`, `Windshield`, `Hardtop`, `HardtopPillars`, `Railings`) preserve their existing `body` attribute (now a PartDesign Body instead of a Part Feature) and their dimension fields. New attributes are added to wrappers but no existing attributes are removed — FR-024 / R4.

## §4 State transitions

This module has no runtime state machine. Geometry is constructed once per `build_deck()` call. The dataclasses are `frozen=True`. The FreeCAD document state transitions are:

```text
[empty doc] → recompute → [hull body present] → build_deck call:
  add deck_plate Body → recompute → add cabin_trunk Body → recompute →
  add windshield Body → recompute → add hardtop Body → recompute →
  for each (side, i in count_per_side): add pillar_{side}_{i} Body → recompute →
  add railings_port Body → recompute → add railings_starboard Body → recompute →
[deck bodies present]
```

On any failure during the build sequence, `_rollback(target_doc, added)` (existing helper at `src/storebro/deck.py:474`) removes all added objects in reverse order. This pattern is preserved.

## §5 Validation rules (consolidated)

Per-dataclass `__post_init__` raises `DeckParameterError(parameter_name, parameter_value, valid_range)` per the existing error contract (`src/storebro/deck.py:58`).

| Validation | Raises (parameter_name) | Source |
|---|---|---|
| `CabinTrunkParameters.length ≤ 0` | `cabin_trunk_length` | spec FR-001/002, dataclass §1.1 |
| `CabinTrunkParameters.forward_width > aft_width` | `cabin_trunk_forward_width<>aft_width` | dataclass §1.1 cross-field |
| `WindshieldParameters.top_z ≤ base_z` | `windshield_top_z<>base_z` | dataclass §1.2 cross-field |
| `WindshieldParameters.top_width > base_width` | `windshield_top_width<>base_width` | dataclass §1.2 cross-field |
| `WindshieldCurvatureRadius < 200.0` | `windshield_curvature_radius` | RejectSubMinimumWindshieldCurvature rule, computed in `__post_init__` |
| `HardtopParameters.aft_width > forward_width` | `hardtop_aft_width<>forward_width` | dataclass §1.3 cross-field |
| `HardtopParameters.leading_edge_curl_length > length` | `hardtop_curl_length<>length` | dataclass §1.3 cross-field |
| `HardtopParameters.leading_edge_curl_depth > height_above_deck` | `hardtop_curl_depth<>height` | dataclass §1.3 cross-field |
| `PillarParameters.forward_x ≥ aft_x` | `pillar_forward_x<>aft_x` | dataclass §1.4 cross-field |
| `RailingParameters.height_above_deck ≥ hardtop.height_above_deck` | `railing_height<>hardtop_height` | composite §1.6 cross-component |
| `pillars.forward_x < cabin_trunk.length` | `pillar_forward_x<>cabin_trunk_length` | composite §1.6 cross-component |
| `hardtop.forward_width > deck_plate.width_amidships` | `hardtop_forward_width<>deck_plate_width` | `build_deck` cross-hull (not in `__post_init__`) |
| Pillar lower endpoint Z < deck plate top Z - 1.0 mm | `pillar_lower_z<>deck_plate_top_z` | runtime geometry assertion in geometry tests, not a parameter validation |

## §6 Determinism contract

For determinism (spec.allium `invariant DeterministicShapeDigest`, SC-005), the build must:

1. Iterate sub-bodies in a fixed order (deck plate → cabin trunk → windshield → hardtop → pillars (port→starboard, fwd→aft) → railings (port→starboard)).
2. Generate Body labels in a deterministic pattern: `Deck_CabinTrunk`, `Deck_Windshield`, `Deck_Hardtop`, `Deck_Pillar_Port_1`, `Deck_Pillar_Port_2`, …, `Deck_Railings_Port`, `Deck_Railings_Starboard`. No timestamps, no UUIDs, no counters that depend on what else is in the document.
3. Pass all geometry through spec 002's `Fcstd.scrub` before write — already handled by the existing `export.py`. No new determinism mechanism needed.

---

**Data model complete. Ready for Phase 1 contracts.**
