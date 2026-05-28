# Data Model: Hull surface smoothness (spec 009)

Phase 1 output for `/plan`. Captures entities, fields, and relationships for spec 009 in implementation-ready form. Authoritative source for `tasks.md` to derive concrete TaskN entries.

## Entities

### 1. `HullParameters` (extended)

Existing frozen dataclass at `src/storebro/hull.py:126`. Spec 009 adds two additive fields and four computed flags.

| Field | Type | Default | Validation | Source |
|---|---|---|---|---|
| `loa` | `float` (m) | 10.34 | > 0 | spec 001 (unchanged) |
| `beam` | `float` (m) | 3.13 | > 0 | spec 001 (unchanged) |
| `draft` | `float` (m) | 1.10 | > 0 | spec 007 (unchanged) |
| `deadrise` | `float` (deg) | 8.0 | [0, 30] | spec 007 (unchanged) |
| `sheer_aft` | `float` (m) | 0.95 | > 0 | spec 007 (unchanged) |
| `sheer_fwd` | `float` (m) | 1.16 | > 0 | spec 007 (unchanged) |
| `transom_angle` | `float` (deg) | 5.0 | [0, 30] | spec 007 (unchanged) |
| `stem_rake_angle` | `float` (deg) | 6.0 | [0, 30] | spec 007 (unchanged) |
| **`station_count`** | **`int`** | **9** | **[3, 21]** | **spec 009 NEW (FR-001, FR-003)** |
| **`bilge_radius`** | **`float` (m)** | **0.20** | **[0, min(beam/2, draft)]** | **spec 009 NEW (FR-002, FR-004)** |

> **Naming note**: `spec.allium` and some `data-model.md` headings use the suffix `bilge_radius_m` (the `_m` denotes "meters") for formal-spec clarity. The Python field name on `HullParameters` is `bilge_radius` (no suffix), matching the existing `hull.py` convention (`loa`, `beam`, `draft` etc.). Both names refer to the same value. Documentation alignment per `/speckit.analyze` finding L1.

**Computed properties (read-only, derived from fields)**:

| Property | Type | Formula | Used by |
|---|---|---|---|
| `uses_b_spline_loft` | `bool` | `station_count >= B_SPLINE_STATION_COUNT_THRESHOLD` | `_apply_loft_and_mirror`, `_detect_b_spline_overshoot` |
| `uses_zero_forefoot_stem` | `bool` | `station_count >= B_SPLINE_STATION_COUNT_THRESHOLD` | `_compute_stations` (stem branch) |
| `uses_bilge_arc` | `bool` | `bilge_radius > 0` | `_compute_stations` (non-stem branch), `_create_station_sketch` |
| `max_bilge_radius` | `float` (m) | `min(beam / 2, draft)` | `__post_init__` validation |

**Module-level constants** (Constitution I — named, exported):

```python
DEFAULT_STATION_COUNT = 9
DEFAULT_BILGE_RADIUS_M = 0.20
STATION_COUNT_MIN = 3
STATION_COUNT_MAX = 21
B_SPLINE_STATION_COUNT_THRESHOLD = 8
OVERSHOOT_TOLERANCE_MM = 1.0
PILLAR_SEATING_TOLERANCE_MM = 1.0      # already exists (spec 008); referenced here for cross-spec clarity
REFERENCE_FIDELITY_TOLERANCE_PCT = 1.0
```

### 2. `_StationProfile` (extended)

Existing internal dataclass at `src/storebro/hull.py:218`. Spec 009 extends with bilge-arc context and topology enum.

| Field | Type | Default | Source |
|---|---|---|---|
| `name` | `str` | (per-station: "Transom", "Station2", ..., "Stem") | unchanged |
| `x_position` | `float` (m) | (derived) | unchanged |
| `half_beam_at_top` | `float` (m) | (derived) | unchanged |
| `half_beam_at_bottom` | `float` (m) | (derived) | unchanged |
| `keel_depth` | `float` (m) | (derived) | unchanged |
| `is_terminal` | `bool` | `False` | unchanged (legacy field kept for migration; new code uses `topology`) |
| `stem_rake_angle_deg` | `float` | `0.0` | unchanged |
| **`topology`** | **`StationTopology` enum** | **(derived)** | **spec 009 NEW** |
| **`bilge_radius_m`** | **`float` (m)** | **`0.0`** | **spec 009 NEW — copied from `HullParameters.bilge_radius * 1000` when `topology == PENTAGON_WITH_ARC`** |
| **`vertex_count`** | **`int`** | **(derived from topology)** | **spec 009 NEW** |

**`StationTopology` enum** (NEW):

```python
class StationTopology(enum.Enum):
    DEGENERATE_VERTEX = "degenerate_vertex"             # single point (stem with zero forefoot)
    SHARP_CHINE_QUADRILATERAL = "sharp_chine"           # 4-vertex (non-stem, no bilge arc)
    PENTAGON_WITH_ARC = "pentagon_with_arc"             # 5-vertex with quarter-circle bilge
    PENTAGON_80MM_FOREFOOT = "pentagon_80mm_forefoot"   # legacy 5-vertex stem (station_count < 8)
```

**Topology → vertex_count mapping** (enforced by Allium invariant `VertexCountMatchesTopology`):

| Topology | vertex_count |
|---|---|
| `DEGENERATE_VERTEX` | 1 |
| `SHARP_CHINE_QUADRILATERAL` | 4 |
| `PENTAGON_WITH_ARC` | 5 |
| `PENTAGON_80MM_FOREFOOT` | 5 |

### 3. `HullBody` (output)

The `PartDesign::Body` produced by `build_hull()`. No new entity fields; behavior changes:

| Property | Type | v1.0.2 value | v1.0.3 value | Note |
|---|---|---|---|---|
| `stations.count` | `int` | 5 | `parameters.station_count` (default 9) | (FR-005) |
| `loft.Ruled` | `bool` | `True` always | `True` when `< 8`, `False` when `>= 8` | (FR-006, FR-007) |
| Stem topology | (implicit) | pentagon w/ 80 mm forefoot | degenerate vertex when `>= 8` | (FR-009) |
| Non-stem topology | (implicit) | sharp-chine 4-vertex | pentagon-with-arc when `bilge_radius > 0` | (FR-008) |
| `Shape.isClosed()` | `bool` | `True` | `True` (invariant preserved) | Constitution III |
| `Shape.Volume` | `float` | > 0 | > 0 (invariant preserved) | Constitution III |
| `Tip` | `PartDesign::Mirrored` | yes | yes (invariant preserved) | Constitution III |

### 4. `BilgeArc` (conceptual)

Embedded in each `PENTAGON_WITH_ARC` station sketch. No standalone Python dataclass — represented by Sketcher elements in the SketchObject. Conceptual model:

| Property | Type | Value | Note |
|---|---|---|---|
| `radius_mm` | `float` | `parameters.bilge_radius * 1000` | (FR-008) |
| `tangent_continuous_at_bottom` | `bool` | `True` (enforced by `Sketcher.Constraint("Tangent", arc_idx, bottom_line_idx)`) | research R5 |
| `tangent_continuous_at_topside` | `bool` | `True` (enforced by `Sketcher.Constraint("Tangent", arc_idx, topside_line_idx)`) | research R5 |
| Start vertex Z | `float` | (derived) | Replaces the v1.0.2 sharp-chine bottom-to-topside corner vertex |
| End vertex Z | `float` | (derived) | |

## Relationships

```
HullParameters (1) ──→ (1) HullBody                        [build_hull(params) creates HullBody]
HullBody (1) ──→ (N) StationSketch                         [N = parameters.station_count]
StationSketch (1) ──→ (0..1) BilgeArc                      [present when topology == PENTAGON_WITH_ARC]
HullBody (1) ──→ (1) PartDesign::AdditiveLoft              [loft.Ruled = (NOT uses_b_spline_loft)]
HullBody (1) ──→ (1) PartDesign::Mirrored                  [HullBody.Tip]
HullBody (1) ──── (0..1) DeckPlate                         [via deck module; spec 009 read-only]
```

## State transitions

No state machines in spec 009. Hull construction is a single-shot transformation `(params → body)`; there is no intermediate state where a hull is "partially built" exposed to library consumers.

## Validation rules

Enforced in `HullParameters.__post_init__`. Each violation raises `HullParameterError(field, value, valid_range)` with a message identifying the offending field, the offending value, and the valid range (existing exception class from spec 001; reused unchanged).

| Field | Validation | Message format |
|---|---|---|
| `station_count` | `STATION_COUNT_MIN <= n <= STATION_COUNT_MAX` | `"station_count out of range: got {n}, valid [{min}, {max}]"` |
| `bilge_radius` | `0 <= r <= max_bilge_radius` | `"bilge_radius out of range: got {r}, valid [0, {max}]"` |

Build-time validation (in `_detect_b_spline_overshoot`):

| Condition | Action |
|---|---|
| `parameters.uses_b_spline_loft AND any_station_bbox_z_overshoot > OVERSHOOT_TOLERANCE_MM` | Raise `HullConstructionError(message, x_station_mm, overshoot_mm, remediation_hint)` |

## Compatibility map

Per spec 009 FR-016 (frozen dataclass preserved):

- `HullParameters(loa=10.34, beam=3.13, draft=1.10)` — succeeds; gets new defaults.
- `HullParameters(loa=10.34, beam=3.13, draft=1.10, station_count=5)` — succeeds; opts into legacy 5-station + Ruled=True + pentagon-stem behavior.
- `HullParameters(loa=10.34, beam=3.13, draft=1.10, bilge_radius=0)` — succeeds; opts into sharp-chine cross-section.
- `HullParameters(loa=10.34, beam=3.13, draft=1.10, station_count=50)` — raises `HullParameterError("station_count", 50, "[3, 21]")`.
- `HullParameters(loa=10.34, beam=3.13, draft=1.10, bilge_radius=5.0)` — raises `HullParameterError("bilge_radius", 5.0, "[0, 1.10]")` (1.10 = min(beam/2, draft) = min(1.565, 1.10) = 1.10).

All v1.0.2 call sites that did not pass `station_count` or `bilge_radius` continue to work with no source-level changes — they now use the v1.0.3 defaults and observe the smoother hull as the headline deliverable.
