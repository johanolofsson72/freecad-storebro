# Phase 1 Data Model: Window & Porthole Cutouts

All dataclasses `@dataclass(frozen=True)`, lengths in **mm**. Porthole dataclasses raise `HullParameterError`; window/windshield dataclasses raise `DeckParameterError`. Defaults are RC34 1972 estimate-grade (research §R7).

## §1 Hull-side parameters (hull.py)

### §1.1 PortholeParameters → raises `HullParameterError`

| Field | Type | Default | Validation |
|---|---|---|---|
| `count_per_side` | int | 3 | `>= 0` |
| `diameter` | float | 220.0 | `> 0` |
| `recess_depth` | float | 20.0 | `> 0` |
| `forward_x` | float | 0.0 (0 → derive from cabin extent) | `>= 0` |
| `aft_x` | float | 0.0 (0 → derive) | `forward_x <= aft_x` |
| `height_above_waterline` | float | 0.0 (0 → mid-freeboard) | `>= 0` |

Sentinel `0.0` on `forward_x`/`aft_x`/`height_above_waterline` means "derive from the actual hull/cabin geometry in `build_hull`" (so the dataclass needs no hull reference). When both `forward_x` and `aft_x` are non-zero, require `forward_x < aft_x`.

### §1.2 HullGlazingParameters (composite) → `field(default_factory=...)`

| Field | Type | Default |
|---|---|---|
| `portholes` | PortholeParameters | `field(default_factory=PortholeParameters)` |

## §2 Deck-side parameters (deck.py)

### §2.1 CabinWindowParameters → raises `DeckParameterError`

| Field | Type | Default | Validation |
|---|---|---|---|
| `count_per_side` | int | 1 | `>= 0` |
| `length` | float | 900.0 | `> 0` |
| `height` | float | 350.0 | `> 0` |
| `corner_radius` | float | 80.0 | `>= 0`, `2*r <= height`, `2*r <= length` |
| `recess_depth` | float | 15.0 | `> 0` |
| `sill_height` | float | 0.0 (0 → centered on wall) | `>= 0` |

### §2.2 WindshieldGlazingParameters → raises `DeckParameterError`

| Field | Type | Default | Validation |
|---|---|---|---|
| `enabled` | bool | True | — |
| `frame_border` | float | 60.0 | `> 0` |
| `glass_thickness` | float | 6.0 | `> 0` |

### §2.3 DeckGlazingParameters (composite)

| Field | Type | Default |
|---|---|---|
| `cabin_windows` | CabinWindowParameters | `field(default_factory=...)` |
| `windshield` | WindshieldGlazingParameters | `field(default_factory=...)` |

## §3 Wrappers / aggregate extensions

### §3.1 hull.py

```python
@dataclass(frozen=True)
class Porthole:
    body: Any          # the HullBody (pockets are features on it)
    count: int         # total portholes cut (both sides)
    diameter: float    # meters
```

`Hull` aggregate gains: `portholes: Porthole` and `parameters_glazing: HullGlazingParameters` (appended after existing fields; `Hull` is only constructed inside `build_hull`).

### §3.2 deck.py

```python
@dataclass(frozen=True)
class CabinWindows:
    body: Any          # the cabin-trunk body (pockets are features on it)
    count: int         # total windows cut (both sides)

@dataclass(frozen=True)
class WindshieldGlass:
    body: Any          # the glass-pane PartDesign::Body
    thickness: float   # meters
```

The existing `Windshield` wrapper gains a `glass_pane: WindshieldGlass | None` field (None when glazing disabled). `Deck` aggregate gains `cabin_windows: CabinWindows` and `parameters_glazing: DeckGlazingParameters`.

## §4 Signature changes

```python
def build_hull(parameters=None, *, parameters_glazing: HullGlazingParameters | None = None,
               document=None, name="Hull") -> Hull: ...

def build_deck(hull, parameters=None, *, parameters_superstructure=None,
               parameters_hardware=None, parameters_glazing: DeckGlazingParameters | None = None,
               document=None, name="Deck") -> Deck: ...
```

`parameters_glazing=None` → defaults (glazing on). Independent of the existing mutual-exclusivity guards.

## §5 FreeCAD object naming (deterministic)

| Item | Object name(s) |
|---|---|
| Porthole | `Hull_Porthole_{Port,Starboard}_{i}` Pocket features on HullBody |
| Cabin window | `Deck_CabinWindow_{Port,Starboard}_{i}` Pocket features on the trunk body |
| Windshield frame opening | `Deck_WindshieldFrameOpening` Pocket on the windshield body |
| Windshield glass | `Deck_WindshieldGlass` (PartDesign::Body) |

## §6 Error taxonomy (raised pre-/early-build)

| Condition | error / parameter_name |
|---|---|
| Per-field positivity | field name (e.g. `"porthole_diameter"`, `"cabin_window_height"`) |
| `corner_radius*2 > height/length` | `"cabin_window_corner_radius"` |
| `forward_x >= aft_x` (both set) | `"porthole_forward_x<>aft_x"` |
| recess_depth >= local half-beam (hull) | `"porthole_recess_depth<>half_beam"` (in build_hull) |
| recess_depth >= trunk half-width | `"cabin_window_recess_depth<>wall"` (in build_deck) |
| porthole at/below waterline | `"porthole_height_above_waterline"` (in build_hull) |
| porthole diameter > freeboard | `"porthole_diameter<>freeboard"` (in build_hull) |
| `2*frame_border >= slab width/height` | `"windshield_frame_border<>opening"` (in build_deck) |
| post-cut non-manifold | `HullConstructionError` / `DeckConstructionError` (FR-008) |
