# Data Model: Hull Module (Phase 1)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Date**: 2026-05-17

This document defines the data structures of the hull module: the public dataclass for inputs, the conceptual `Hull` aggregate, and the two public exception types.

---

## Entity overview

```text
HullParameters (value object, frozen dataclass)
        │
        ▼
   build_hull(parameters, document, name)
        │
        ├── validates HullParameters  ──▶ HullParameterError (raises)
        │
        ├── version-checks FreeCAD    ──▶ HullConstructionError (raises)
        │
        ├── constructs station sketches + loft + mirror
        │       │
        │       └── on FreeCAD failure ──▶ HullConstructionError (raises, wraps)
        │
        ▼
   Hull (returned to caller — a wrapper around a FreeCAD::Part::Body)
```

---

## 1. `HullParameters` (frozen dataclass — value object)

Public, frozen `dataclasses.dataclass` exported from `storebro.hull`. Hashable. Used as the single input contract for `build_hull`. All fields are SI: meters for lengths, degrees for angles.

### Fields

| Field | Type | Default | Unit | Valid range | Description |
|---|---|---|---|---|---|
| `loa` | `float` | `10.35` | m | `> 0` and `> beam_max` | Length overall — bow to transom at sheer line. **Citation**: Royal Cruiser 34 (1972). |
| `beam_max` | `float` | `3.20` | m | `> 0` and `< loa` | Maximum beam at amidships. **Citation**: Royal Cruiser 34 (1972). |
| `draft` | `float` | `0.95` | m | `> 0` | Draft at amidships. Estimate scaled from era-typical semi-displacement. |
| `freeboard` | `float` | `0.95` | m | `> 0` | Freeboard at amidships. Estimate ≈ 30% of beam. |
| `deadrise_amidships` | `float` | `16.0` | ° | `[0, 30]` | Deadrise angle at amidships (0 = flat bottom). Estimate. |
| `sheer_height_aft` | `float` | `0.85` | m | `> 0` and `<= sheer_height_fwd` | Sheer line height at transom. Estimate. |
| `sheer_height_fwd` | `float` | `1.30` | m | `> 0` and `>= sheer_height_aft` | Sheer line height at stem. Estimate. |
| `transom_angle` | `float` | `12.0` | ° | `[0, 45]` | Transom rake from vertical, aft direction positive. Estimate. |

### Class-level constants

```python
REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972: ClassVar[dict[str, float]] = {
    "loa": 10.35, "beam_max": 3.20, "draft": 0.95, "freeboard": 0.95,
    "deadrise_amidships": 16.0,
    "sheer_height_aft": 0.85, "sheer_height_fwd": 1.30,
    "transom_angle": 12.0,
}
```

This constant is read by the `DefaultHullMatchesReferenceFidelity` test in `test_hull_default_dimensions.py` so the ±1% comparison cites a single source of truth. The `loa` and `beam_max` entries are citation-grade; the remaining six are estimate-grade — see [research.md §R1](./research.md) for sourcing details.

### Validation (`__post_init__`)

Implemented as a single private `_validate` helper invoked from `__post_init__`. Validation order is:

1. **Per-field positivity / range** — raises `HullParameterError` on the first field that fails. Range messages cite the field name, the supplied value, and the documented valid range.
2. **Cross-field geometric impossibility checks**:
   - `loa > beam_max` (else `HullParameterError`, "LOA must exceed beam_max")
   - `sheer_height_fwd >= sheer_height_aft` (else `HullParameterError`, "sheer_height_fwd must not be below sheer_height_aft (inverted sheer)")

The cross-field checks are deliberately ordered after the per-field ones — bad single-field values produce more actionable error messages than the cross-field message would.

### Properties (derived, not stored)

- `aspect_ratio: float` — `loa / beam_max`. Useful for tests and assertions.
- `is_planing_hull: bool` — `aspect_ratio > 3.2`. Informational only; does not affect geometry.

### Identity & lifecycle

`HullParameters` is frozen (immutable), hashable, and value-equal: two instances with the same field values compare equal and hash the same. No identity beyond field values. Lifecycle: built by the caller, passed to `build_hull`, discarded.

---

## 2. `Hull` (returned wrapper — see note on identity)

`build_hull` returns a `Hull` dataclass that wraps the FreeCAD Body and carries the inputs alongside it, so callers can introspect the build without re-reading FreeCAD properties.

### Fields

| Field | Type | Description |
|---|---|---|
| `body` | `FreeCAD.DocumentObject` (a `Part::Body`) | The parametric Body added to the FreeCAD document |
| `parameters` | `HullParameters` | The exact inputs that built this hull |
| `document` | `FreeCAD.Document` | The document holding the Body |
| `label` | `str` | The Body's `Label` after FreeCAD auto-numbering (e.g. `Hull001`) |
| `build_duration_seconds` | `float` | Wall-clock seconds the build took, for the SC-002 budget check |

### Behavior

- `Hull` is a regular (non-frozen) dataclass; `__eq__` is by identity, not value (because two builds with identical parameters produce structurally identical but distinct FreeCAD Bodies).
- `Hull.bbox: tuple[float, float, float]` — convenience property returning `(length, width, height)` of the Body's bounding box. Used by the determinism and parametricity tests.
- `Hull.volume: float` — convenience property returning the Body's volume. Used by the determinism test.

### Identity & lifecycle

The `body` field carries identity (FreeCAD `Name`, `Label`, and document membership). Two `Hull` objects are equal iff they wrap the same underlying `Part::Body`. Lifecycle: returned from `build_hull`, lives as long as the FreeCAD document does; releasing the Python reference does not delete the Body — the document owns it.

---

## 3. `HullParameterError(ValueError)` — exception class

Public exception raised when `HullParameters` validation fails — strictly before any FreeCAD call.

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `parameter_name` | `str` | Field name that failed (e.g. `"loa"`, `"sheer_height_fwd"`, `"loa<>beam_max"` for cross-field) |
| `parameter_value` | `float \| None` | The offending value. `None` for cross-field violations where no single value is "the" offender. |
| `valid_range` | `str` | Human-readable range (e.g. `"> 0"`, `"[0, 30] degrees"`, `"loa > beam_max"`) |

### Message format

```
HullParameterError: <field_name> = <value> is outside the valid range <range>
```

For cross-field violations:

```
HullParameterError: invalid parameter combination — <constraint>
```

### Usage

Always raised by `HullParameters.__post_init__` or by `_validate(...)` inside `build_hull`. Never raised after FreeCAD calls — those go through `HullConstructionError`.

---

## 4. `HullConstructionError(RuntimeError)` — exception class

Public exception raised when (a) the FreeCAD version is outside the supported range, OR (b) FreeCAD fails to construct the hull despite valid parameters. Wraps the underlying FreeCAD exception when one is present.

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `parameters` | `HullParameters \| None` | The parameter set that triggered the failure. `None` for version-check failures (no build attempt). |
| `underlying` | `BaseException \| None` | The FreeCAD-side exception, if any. `None` for version-check failures. |
| `detected_version` | `tuple[int, int] \| None` | The `(major, minor)` of the FreeCAD runtime, populated for version-check failures only. |
| `supported_range` | `str \| None` | Human-readable supported range (e.g. `"1.1 to <2.0"`), populated for version-check failures only. |

### Message format

```
HullConstructionError: unsupported FreeCAD version 0.20 — supported range is 1.1 to <2.0
```

```
HullConstructionError: FreeCAD failed to construct hull with parameters <repr(parameters)> — <type(underlying).__name__>: <str(underlying)>
```

### Usage

Raised in three code paths:

1. Lazy first-call version check (R6 in research.md): version is out of range → raised with `detected_version` + `supported_range` set.
2. FreeCAD raises while building station sketches → wrapped, raised with `parameters` + `underlying` set.
3. FreeCAD raises while running the additive loft or mirror → same as (2).

---

## 5. Module-private types

These are *not* part of the public API. Documented here for plan completeness; not exported.

### `_StationProfile`

Internal value object representing one of the five station sketches before it becomes a FreeCAD `Sketch`. Fields: `x_position: float`, `half_beam_at_top: float`, `half_beam_at_bottom: float`, `keel_depth: float`, `is_terminal: bool` (True for the stem station). Built by `_compute_stations(parameters)` and consumed by `_create_station_sketch(profile, body)`.

### `_HullDimensions`

Internal NamedTuple holding the measured dimensions of a built Body (length, beam, draft, freeboard, plus topology counts). Built by `_measure_hull(body)` and used by the geometry tests. Not exported because it duplicates information the caller already has (parameters) plus internal data (topology counts) the public API doesn't promise to keep stable.

---

## State transitions

The hull module is stateless from the caller's perspective: `build_hull` is a pure function over `(HullParameters, document, name)` with the side effect of adding a Body to a FreeCAD document.

Internal state machine of one `build_hull` invocation:

```
START
  │
  ├── version_check_status: unknown ──┐
  │                                   ▼
  │                            ┌─ in_range ──┐
  │                            │             │
  │                            └─ out_of_range ──▶ raise HullConstructionError (END)
  │                                   │
  │                                   ▼
  ├── parameter_validation: not_started
  │                            │
  │                            ├─ valid ──┐
  │                            │          │
  │                            └─ invalid ──▶ raise HullParameterError (END)
  │                                   │
  │                                   ▼
  ├── document_resolution: not_started
  │                            │
  │                            ▼
  │                          resolved (document selected per R4 / FR-016)
  │                                   │
  │                                   ▼
  ├── geometry_construction: not_started
  │                            │
  │                            ├─ success ──┐
  │                            │            │
  │                            └─ freecad_failed ──▶ wrap and raise HullConstructionError (END)
  │                                   │
  │                                   ▼
  └── RETURN Hull(body, parameters, document, label, build_duration_seconds)
```

This state machine is the model for the TLA+ verification in `/tla` (post-implementation phase).

---

## Cross-references

- Public API exports → [contracts/python-api.md](./contracts/python-api.md)
- Usage example → [quickstart.md](./quickstart.md)
- Formal invariants → [spec.allium](./spec.allium)
- Acceptance criteria → [spec.md](./spec.md) §Success Criteria
