# Public API Contract: Propulsion Module

New public surface added by spec 014. All names are importable from `storebro` (re-exported in `__init__.py`) and from `storebro.propulsion`. Additive only — no existing symbol changes.

## Function

```python
def build_propulsion(
    hull: Hull,
    deck: Deck | None = None,
    parameters: PropulsionParameters | None = None,
    *,
    document: Any | None = None,
    name: str = "Propulsion",
) -> Propulsion: ...
```

- **`hull`** (required): a built `Hull` (from `build_hull`); its `body.Shape` is sampled for keel depth and half-beam. Components are added to `hull.document` unless `document` is given.
- **`deck`** (optional): a built `Deck`; supplies the engine-height ceiling (deck-plate top Z). When `None`, the ceiling falls back to the hull sheer at the engine station.
- **`parameters`** (optional): a `PropulsionParameters`; when `None`, defaults are used (twin-screw RC34 layout).
- **`document`** (optional, keyword-only): target FreeCAD document; defaults to `hull.document`.
- **`name`** (optional, keyword-only): label prefix for the produced bodies.
- **Returns**: a `Propulsion` aggregate (see data-model.md).
- **Raises**: `PropulsionParameterError` for invalid parameters or build-context violations (offset past topsides, exit not aft of engine, exit above waterline); `PropulsionConstructionError` wrapping any unexpected FreeCAD-side failure (after rolling back).

## Parameter dataclasses (frozen)

```python
@dataclass(frozen=True)
class EngineBedParameters: length_mm: float = 1400.0; width_mm: float = 120.0; height_mm: float = 200.0

@dataclass(frozen=True)
class EngineParameters: length_mm: float = 1100.0; width_mm: float = 600.0; height_mm: float = 700.0; station_x_mm: float = 3500.0

@dataclass(frozen=True)
class ShaftParameters: diameter_mm: float = 45.0; angle_deg: float = 10.0; exit_x_mm: float = 1800.0

@dataclass(frozen=True)
class PropellerParameters: diameter_mm: float = 450.0; hub_diameter_mm: float = 90.0; blade_count: int = 3

@dataclass(frozen=True)
class RudderParameters: chord_mm: float = 300.0; span_mm: float = 500.0; thickness_mm: float = 40.0; stock_diameter_mm: float = 50.0

@dataclass(frozen=True)
class PropulsionParameters:
    engine_count: int = 2
    engine_offset_y_mm: float = 400.0
    rudder_count: int | None = None      # None → resolved to engine_count
    engine_bed: EngineBedParameters = field(default_factory=EngineBedParameters)
    engine: EngineParameters = field(default_factory=EngineParameters)
    shaft: ShaftParameters = field(default_factory=ShaftParameters)
    propeller: PropellerParameters = field(default_factory=PropellerParameters)
    rudder: RudderParameters = field(default_factory=RudderParameters)
```

(Each `__post_init__` validates its own fields; `PropulsionParameters.__post_init__` enforces the cross-invariants in data-model.md. `rudder_count is None` resolves to `engine_count` at build time.)

## Wrapper + aggregate dataclasses (read-only result)

`EngineBed`, `EngineBlock`, `Shaft`, `Propeller`, `Rudder` (fields per data-model.md) and:

```python
@dataclass
class Propulsion:
    document: Any
    parameters: PropulsionParameters
    engine_beds: list[EngineBed]
    engines: list[EngineBlock]
    shafts: list[Shaft]
    propellers: list[Propeller]
    rudders: list[Rudder]
    hull_modified: bool          # always False
    build_duration_seconds: float
```

## Exceptions

```python
class PropulsionParameterError(ValueError): ...      # invalid params / context; names value + valid range
class PropulsionConstructionError(RuntimeError): ... # wraps unexpected FreeCAD failures; rollback already done
```

## CLI contract (cli.py `build` command)

- New flag `--engine-count {1,2}` (default 2): selects single- or twin-screw.
- New flag `--no-propulsion`: skip the propulsion step entirely.
- Behaviour: `_run_build` calls `build_propulsion(hull, deck, parameters=PropulsionParameters(engine_count=<flag>))` after `build_interior`, on the same document, unless `--no-propulsion` is given. The propulsion bodies are then included in every export format (`fcstd`/`step`/`stl`/`brep`) without further registration.

## Back-compatibility guarantees

- No existing function signature, dataclass, or CLI flag changes.
- Existing `storebro build ...` invocations gain propulsion by default (additive geometry); `--no-propulsion` restores the pre-1.1.0 output set.
- `storebro.__version__ == "1.1.0"` and equals `pyproject.toml` `version` (guarded by `test_version_consistency`).
