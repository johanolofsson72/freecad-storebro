# Phase 1 Data Model: Basic Deck Hardware

All dataclasses are `@dataclass(frozen=True)`, lengths in **millimeters**, angles in **degrees**, mirroring the spec 008 per-component dataclasses. Each `__post_init__` raises `DeckParameterError(name, value, valid_range)` on violation. Defaults are the RC34 1972 estimate-grade values from research.md §R7.

## §1 Parameter dataclasses

### §1.1 RubrailParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `height` | float | 60.0 | `> 0` |
| `thickness` | float | 40.0 | `> 0` |
| `forward_x` | float | 300.0 | `>= 0` |
| `aft_x` | float | 10000.0 | `> forward_x` |

Cross-field: `forward_x < aft_x` → `"rubrail_forward_x<>aft_x"`.

### §1.2 BowPulpitParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `tube_diameter` | float | 25.0 | `> 0` |
| `height` | float | 600.0 | `> 0` |
| `forward_extent` | float | 400.0 | `>= 0` |
| `stanchion_count` | int | 2 | `>= 0` |

### §1.3 LifelineParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `line_count` | int | 1 | `>= 0` |
| `tube_diameter` | float | 12.0 | `> 0` |
| `height_fraction` | float | 1.0 | `0 < x <= 1.0` → `"lifeline_height_fraction"` `(0, 1]` |

### §1.4 AnchorLockerParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `length` | float | 500.0 | `> 0` |
| `width` | float | 400.0 | `> 0` |
| `height` | float | 150.0 | `> 0` |
| `center_x` | float | 8500.0 | `>= 0` |

> Coordinate note: the hull places the **transom (stern) at X=XMin (0)** and the **stem (bow) at X=XMax (≈ LOA)**. The foredeck — "forward of the cabin trunk" — is therefore the high-X region. The default `center_x=8500` lands on the foredeck near the bow (cabin trunk occupies X≈350–4950 by default).

### §1.5 CleatParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `count_per_station` | int | 1 | `>= 0` |
| `station_count` | int | 2 | `>= 0` |
| `length` | float | 200.0 | `> 0` |
| `height` | float | 80.0 | `> 0` |

**Count interpretation (per-side semantics — matches spec.allium `expected_cleat_total`)**: the cleat builder places cleats at `station_count` evenly-spaced longitudinal stations between a forward and aft X bound. `count_per_station` is the number of cleats placed *per side* at each station, and every cleat is mirrored port↔starboard, so symmetry is automatic (no even-count rule needed). Therefore:

```
total_cleats = count_per_station * station_count * 2     (default 1 * 2 * 2 = 4)
port_cleats  = starboard_cleats = count_per_station * station_count   (default 2 each)
```

### §1.6 DeckHardwareParameters (composite)

| Field | Type | Default |
|---|---|---|
| `rubrail` | RubrailParameters | `field(default_factory=RubrailParameters)` |
| `bow_pulpit` | BowPulpitParameters | `field(default_factory=BowPulpitParameters)` |
| `lifelines` | LifelineParameters | `field(default_factory=LifelineParameters)` |
| `anchor_locker` | AnchorLockerParameters | `field(default_factory=AnchorLockerParameters)` |
| `cleats` | CleatParameters | `field(default_factory=CleatParameters)` |

No cross-component `__post_init__` invariants at the composite level (unlike `DeckSuperstructureParameters`, the hardware items are mutually independent at the parameter layer). Cross-hull / cross-deck collision checks (anchor locker vs. cabin trunk, rubrail vs. deck extent) are enforced inside `build_deck` where the deck plate + cabin trunk geometry is available — mirroring `_validate_cross_hull_constraints`.

## §2 Wrapper dataclasses (returned on the Deck aggregate)

All `@dataclass(frozen=True)`, holding the FreeCAD object + key derived dims (mirrors `DeckPlate`, `CabinTrunk`, etc.).

```python
@dataclass(frozen=True)
class Rubrail:        body: Any; height: float; thickness: float       # body = Part::Compound (port+starboard)
@dataclass(frozen=True)
class BowPulpit:      body: Any; tube_diameter: float; height: float    # body = PartDesign::Body
@dataclass(frozen=True)
class Lifelines:      body: Any; line_count: int                        # body = Part::Compound (sides×lines); empty compound if no posts
@dataclass(frozen=True)
class AnchorLocker:   body: Any; length: float; width: float; height: float  # body = PartDesign::Body
@dataclass(frozen=True)
class Cleats:         body: Any; count: int                             # body = Part::Compound (all cleats)
```

(`height`/`length`/`width` on wrappers are stored in **meters**, matching how the existing `DeckPlate.thickness`, `CabinTrunk.length`, etc. expose meters — `_MM_PER_M` scaling at the wrapper boundary.)

## §3 Deck aggregate extension

`Deck` (frozen) gains five additive fields after the existing six sub-bodies:

```python
@dataclass(frozen=True)
class Deck:
    # ... existing fields unchanged (parameters, hull, document, label,
    #     build_duration_seconds, deck_plate, cabin_trunk, windshield,
    #     hardtop, hardtop_pillars, railings) ...
    rubrail: Rubrail
    bow_pulpit: BowPulpit
    lifelines: Lifelines
    anchor_locker: AnchorLocker
    cleats: Cleats
    parameters_hardware: DeckHardwareParameters
```

Fields are appended at the end so the dataclass field order for the existing six is unchanged. `Deck` is constructed only inside `build_deck` (keyword args), so adding fields is non-breaking for all external callers (they never construct `Deck` themselves).

## §4 build_deck signature change

```python
def build_deck(
    hull: Hull,
    parameters: DeckParameters | None = None,
    *,
    parameters_superstructure: DeckSuperstructureParameters | None = None,
    parameters_hardware: DeckHardwareParameters | None = None,   # NEW
    document: Any = None,
    name: str = "Deck",
) -> Deck:
```

`parameters_hardware=None` → `DeckHardwareParameters()` (defaults). Independent of the `parameters` ⊕ `parameters_superstructure` mutual-exclusivity guard.

## §5 FreeCAD object naming (deterministic, for reproducibility)

| Item | Object name(s) |
|---|---|
| Rubrail | `Deck_Rubrail_Port`, `Deck_Rubrail_Starboard` (PartDesign bodies) → `Deck_Rubrail` (compound) |
| Bow pulpit | `Deck_BowPulpit` (PartDesign body) |
| Lifelines | `Deck_Lifeline_{Port,Starboard}_{i}` → `Deck_Lifelines` (compound) |
| Anchor locker | `Deck_AnchorLocker` (PartDesign body) |
| Cleats | `Deck_Cleat_{Port,Starboard}_{i}` → `Deck_Cleats` (compound) |

Names are static (no timestamps/counters beyond station index), so FreeCAD auto-numbering on collision is deterministic per document — satisfies constitution II.

## §6 Error taxonomy (all `DeckParameterError`, raised pre-FreeCAD)

| Condition | parameter_name |
|---|---|
| Any per-field positivity violation | field name (e.g. `"rubrail_height"`) |
| `rubrail.forward_x >= rubrail.aft_x` | `"rubrail_forward_x<>aft_x"` |
| `lifeline.height_fraction` out of (0, 1] | `"lifeline_height_fraction"` |
| Anchor locker overlaps cabin trunk | `"anchor_locker_center_x<>cabin_trunk"` (in build_deck) |
| Anchor locker past deck bow edge | `"anchor_locker_center_x<>deck_forward_edge"` (in build_deck) |
| Rubrail extent outside deck X-extent | `"rubrail_extent<>deck_extent"` (in build_deck) |
