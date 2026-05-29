# Phase 1 Data Model: Interior Detail — Alternativ1 & 2

All dataclasses `@dataclass(frozen=True)`, lengths in **mm**, validation raises `InteriorParameterError` (the interior module's existing error type — signature `(source, compartment_name, field, reason)`). Furniture validation uses `source="FurnitureParameters"`, `compartment_name=None`. Defaults are RC34 1972 estimate-grade (research §R6).

## §1 Furniture parameter dataclasses

### §1.1 BerthParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `base_height` | float | 350.0 | `> 0` |
| `cushion_thickness` | float | 100.0 | `> 0` |
| `cushion_count` | int | 1 | `>= 0` |
| `wall_inset` | float | 50.0 | `>= 0` |

### §1.2 GalleyParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `counter_height` | float | 900.0 | `> 0` |
| `counter_thickness` | float | 40.0 | `> 0` |
| `sink_recess_depth` | float | 30.0 | `> 0`, `< counter_thickness` |
| `stove_recess_depth` | float | 20.0 | `> 0`, `< counter_thickness` |
| `cutouts_enabled` | bool | True | — |

Cross-field: `sink_recess_depth < counter_thickness` and `stove_recess_depth < counter_thickness` → `field="galley_sink_recess_depth"` / `"galley_stove_recess_depth"`, reason "must be < counter_thickness (blind recess)".

### §1.3 HeadParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `toilet_height` | float | 400.0 | `> 0` |
| `sink_height` | float | 800.0 | `> 0` |

### §1.4 SalonParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `seat_height` | float | 400.0 | `> 0` |
| `table_height` | float | 650.0 | `> 0` |

### §1.5 BulkheadParameters

| Field | Type | Default | Validation |
|---|---|---|---|
| `thickness` | float | 25.0 | `> 0` |

### §1.6 FurnitureParameters (composite)

| Field | Type | Default |
|---|---|---|
| `berth` | BerthParameters | `field(default_factory=BerthParameters)` |
| `galley` | GalleyParameters | `field(default_factory=GalleyParameters)` |
| `head` | HeadParameters | `field(default_factory=HeadParameters)` |
| `salon` | SalonParameters | `field(default_factory=SalonParameters)` |
| `bulkhead` | BulkheadParameters | `field(default_factory=BulkheadParameters)` |

## §2 Compartment wrapper extension

The existing `Compartment` wrapper (`spec`, `body`) gains:

```python
@dataclass(frozen=True)
class Compartment:
    spec: CompartmentSpec
    body: Any                       # furnished: Part::Compound of furniture; else the box
    furniture: tuple[Any, ...] = ()  # the individual furniture Part::Feature bodies
    is_furnished: bool = False
```

`body` is a `Part::Compound` of the furniture pieces (+ bulkhead) for furnished compartments; the legacy single box for unfurnished (Alt3-5) ones.

## §3 build_interior signature change

```python
def build_interior(
    hull, deck, layout="Alternativ3", *,
    parameters_furniture: FurnitureParameters | None = None,
    document=None, name=None,
) -> Interior:
```

`parameters_furniture=None` → `FurnitureParameters()`. Furniture is built when `layout_spec.layout_name in {"Alternativ1","Alternativ2"}`; otherwise the existing boxy placeholder path runs.

## §4 Build dispatch + envelope guards

Per compartment, dispatch on `spec.compartment_type`:
- `forward_cabin` → berth base + cushions
- `galley` → counter + sink/stove `Part.Cut` recesses
- `head` → toilet + sink
- `salon` → seating + table
Plus a bulkhead per compartment.

Envelope guards in `build_interior` (raise `InteriorParameterError`):
- `berth.base_height >= compartment.height` → reject (`field="berth_base_height"`)
- `galley.counter_height >= compartment.height` → reject
- any furniture piece footprint exceeding the compartment length/width → reject

## §5 FreeCAD object naming (deterministic)

| Item | Object name(s) |
|---|---|
| Berth | `{label}_Berth`, `{label}_Cushion_{i}` |
| Galley counter | `{label}_GalleyCounter` (post-Cut) |
| Head | `{label}_Toilet`, `{label}_Sink` |
| Salon | `{label}_Settee`, `{label}_Table` |
| Bulkhead | `{label}_Bulkhead` |
| Compartment compound | the existing compartment label |

(`{label}` = the existing `_compartment_label(spec, layout_name)`.)

## §6 Error taxonomy (InteriorParameterError)

| Condition | field |
|---|---|
| Per-field positivity | field name (e.g. `"berth_base_height"`) |
| `cushion_count < 0` / `wall_inset < 0` | `"berth_cushion_count"` / `"berth_wall_inset"` |
| `sink/stove_recess_depth >= counter_thickness` | `"galley_sink_recess_depth"` / `"galley_stove_recess_depth"` |
| furniture height/footprint > compartment | `"berth_base_height"` etc. (in build_interior) |
| post-cut non-manifold galley counter | `InteriorConstructionError` (FR-007) |
