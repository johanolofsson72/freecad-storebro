# Contract: `storebro.hull.HullParameters` (v1.0.3)

Public API contract for the hull-parameters extension introduced by spec 009. This is the only external interface affected; CLI, fixtures, and the downstream deck/interior/export modules are unchanged.

## Module: `storebro.hull`

### Class `HullParameters` — frozen dataclass

**Construction signature (v1.0.3)**:

```python
@dataclass(frozen=True)
class HullParameters:
    loa: float = 10.34
    beam: float = 3.13
    draft: float = 1.10
    deadrise: float = 8.0
    sheer_aft: float = 0.95
    sheer_fwd: float = 1.16
    transom_angle: float = 5.0
    stem_rake_angle: float = 6.0
    # spec 009 additive fields:
    station_count: int = 9
    bilge_radius: float = 0.20
```

**Backward compatibility**: existing callers passing only v1.0.2 fields (without `station_count` or `bilge_radius`) continue to compile and run. The new defaults take effect silently.

**New computed properties**:

```python
@property
def uses_b_spline_loft(self) -> bool: ...
@property
def uses_zero_forefoot_stem(self) -> bool: ...
@property
def uses_bilge_arc(self) -> bool: ...
@property
def max_bilge_radius(self) -> float: ...
```

**Construction errors (v1.0.3 additions)**:

| Input | Raises | Message format |
|---|---|---|
| `station_count < 3 or > 21` | `HullParameterError` | `"station_count out of range: got {n}, valid [3, 21]"` |
| `bilge_radius < 0` | `HullParameterError` | `"bilge_radius out of range: got {r}, valid [0, {max}]"` |
| `bilge_radius > min(beam/2, draft)` | `HullParameterError` | `"bilge_radius out of range: got {r}, valid [0, {max}]"` |

**Pre-existing construction errors (unchanged)**:

| Input | Raises | Message |
|---|---|---|
| `loa <= 0` | `HullParameterError` | `"loa must be positive"` |
| `beam <= 0` | `HullParameterError` | `"beam must be positive"` |
| `draft <= 0` | `HullParameterError` | `"draft must be positive"` |
| `deadrise outside [0, 30]` | `HullParameterError` | `"deadrise out of range"` |
| `transom_angle outside [0, 30]` | `HullParameterError` | `"transom_angle out of range"` |
| `stem_rake_angle outside [0, 30]` | `HullParameterError` | `"stem_rake_angle out of range"` |

### Function `build_hull(parameters: HullParameters, document: Optional[App.Document] = None) -> Any`

**Signature**: unchanged.

**Behavior changes** (v1.0.3):

1. Constructs `parameters.station_count` station sketches on the half-hull (was hardcoded 5).
2. The `PartDesign::AdditiveLoft` is built with `Ruled=False` when `parameters.uses_b_spline_loft`, otherwise `Ruled=True`.
3. The stem station is a degenerate vertex when `parameters.uses_zero_forefoot_stem`, otherwise the spec 007 pentagon-with-80mm-forefoot.
4. Non-stem stations carry a quarter-circle bilge arc when `parameters.uses_bilge_arc`, otherwise sharp-chine.

**New build-time error**:

| Condition | Raises | Message |
|---|---|---|
| `uses_b_spline_loft AND bbox_z_overshoot > 1 mm at any X-station` | `HullConstructionError` | `"B-spline loft overshoots hull height envelope at X={x}mm by {overshoot}mm — increase station_count, reduce bilge_radius, or set station_count < 8 for legacy piecewise-linear behavior"` |

**Output contract (unchanged invariants)**:

- Returns a `PartDesign::Body` instance.
- `body.Shape.isClosed()` returns `True`.
- `body.Shape.Volume > 0`.
- `body.Tip` is the `PartDesign::Mirrored` feature (port mirror of the starboard half-hull).
- Body name is `"HullBody"`.
- The body owns N datum planes + N sketches + 1 AdditiveLoft + 1 Mirrored feature.

### Module-level constants (NEW)

```python
DEFAULT_STATION_COUNT: int = 9
DEFAULT_BILGE_RADIUS_M: float = 0.20
STATION_COUNT_MIN: int = 3
STATION_COUNT_MAX: int = 21
B_SPLINE_STATION_COUNT_THRESHOLD: int = 8
OVERSHOOT_TOLERANCE_MM: float = 1.0
REFERENCE_FIDELITY_TOLERANCE_PCT: float = 1.0
```

These are exported from `storebro.hull` and may be referenced by downstream callers.

## CLI: `storebro build`

**Contract**: UNCHANGED from v1.0.2.

```
storebro build --layout <N> --out <path>
```

No new flags, no new required arguments, no flag renames. Per spec 009 clarification 3 and FR-017, `station_count` and `bilge_radius` are NOT exposed via CLI in v1.0.3.

## Downstream modules

- `storebro.deck` — UNCHANGED. The `_resolve_deck_top_z_at(deck_plate, x)` helper is consumed as-is by spec 009; spec 009 must not regress it.
- `storebro.export` — UNCHANGED. The spec 002 deterministic writers handle the new geometry through the same code paths.
- `storebro.interior` — UNCHANGED.
- `storebro.cli` — UNCHANGED.

## Semver impact

PATCH bump: **v1.0.2 → v1.0.3**.

Justification: all changes are additive (new optional fields, new optional CLI flags would be MINOR but are not added). No removal, no rename, no signature break, no behavior change in code paths that do not use the new fields. The geometric output of the default-parameter call changes (smoother hull), but that is a behavior refinement under fixed public surface — same convention as spec 007 (v1.0.0 → v1.0.1).
