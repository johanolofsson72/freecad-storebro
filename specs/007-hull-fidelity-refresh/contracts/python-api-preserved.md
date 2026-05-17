# Contract: `storebro.hull` — public API (preserved, additive only)

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Date**: 2026-05-17

This spec is a **shape refresh** with a single additive parameter. The public surface of `storebro.hull` follows PATCH-level semver: existing fields/methods/exceptions unchanged, one new field added with a default value.

---

## Public symbols (unchanged re-exports)

```python
from storebro.hull import (
    HullParameters,          # frozen dataclass — gains 1 new field with default
    Hull,                    # dataclass — unchanged
    HullParameterError,      # exception — unchanged
    HullConstructionError,   # exception — unchanged
    build_hull,              # function — signature unchanged
)
```

`storebro.hull.__all__` and `storebro/__init__.py` re-exports stay identical.

---

## `HullParameters` — input dataclass

```python
@dataclass(frozen=True)
class HullParameters:
    loa: float = 10.35
    beam_max: float = 3.20
    draft: float = 1.10                      # default changed (PATCH-permitted)
    freeboard: float = 0.95
    deadrise_amidships: float = 8.0          # default changed
    sheer_height_aft: float = 0.95           # default changed
    sheer_height_fwd: float = 1.16           # default changed
    transom_angle: float = 5.0               # default changed
    stem_rake_angle: float = 6.0             # NEW field (additive)
```

**Field count: 9 (was 8).** New field is **additive** with a default value — existing call-sites passing 8 positional args or 8 named kwargs continue to work without modification.

Validation rules:
- `loa, beam_max, draft, freeboard, sheer_height_aft, sheer_height_fwd` MUST be > 0 (unchanged).
- `deadrise_amidships` MUST be in `[0, 30]` degrees (unchanged range).
- `transom_angle` MUST be in `[0, 45]` degrees (unchanged range).
- `stem_rake_angle` MUST be in `[0, 30]` degrees (NEW range).
- Cross-field constraints: `loa > beam_max`, `sheer_height_fwd >= sheer_height_aft` (unchanged).

---

## `Hull` — return value (UNCHANGED)

```python
@dataclass
class Hull:
    body: Any
    parameters: HullParameters
    document: Any
    label: str
    build_duration_seconds: float
```

5 fields, identical to v1.0.0. No public field added or removed.

`body.Shape` continues to be a closed manifold solid with positive volume.

**What changes (transparent to consumers):**
- `body.Shape.Volume` will differ from v1.0.0 because the hull shape changed.
- `body.Shape.BoundBox.ZLength` will be lower (sheer rise dropped 450→210mm, freeboards aligned to reference).
- A new 9th named property `StemRakeAngle` (App::PropertyAngle) is on `body`.

---

## `HullParameterError` / `HullConstructionError` (UNCHANGED)

Both exception classes' `__init__` signatures and attribute sets unchanged. Existing `except HullConstructionError as exc: exc.parameters / exc.underlying / ...` patterns work without modification.

The CLI's `_INPUT_ERROR_TYPES` / `_SYSTEM_ERROR_TYPES` tuples in `storebro.cli` are unchanged.

---

## `build_hull` — entry point (UNCHANGED signature)

```python
def build_hull(
    parameters: HullParameters | None = None,
    *,
    document: Any = None,
    name: str | None = None,
) -> Hull: ...
```

Signature identical to v1.0.0. Default `parameters=None` uses the new RC34 defaults (5 changed values + 1 new value).

---

## Body properties (9 total — was 8)

| Property name | Type | Group | Status |
|---|---|---|---|
| `LOA` | `App::PropertyLength` | `Hull` | unchanged |
| `BeamMax` | `App::PropertyLength` | `Hull` | unchanged |
| `Draft` | `App::PropertyLength` | `Hull` | unchanged (value: 1.10 vs 0.95) |
| `Freeboard` | `App::PropertyLength` | `Hull` | unchanged |
| `SheerHeightAft` | `App::PropertyLength` | `Hull` | unchanged (value: 0.95 vs 0.85) |
| `SheerHeightFwd` | `App::PropertyLength` | `Hull` | unchanged (value: 1.16 vs 1.30) |
| `DeadriseAmidships` | `App::PropertyAngle` | `Hull` | unchanged (value: 8.0 vs 16.0) |
| `TransomAngle` | `App::PropertyAngle` | `Hull` | unchanged (value: 5.0 vs 12.0) |
| `StemRakeAngle` | `App::PropertyAngle` | `Hull` | **NEW (value: 6.0)** |

Existing code that reads `body.LOA` etc. continues to work.

---

## Downstream consumers (UNCHANGED contracts)

| Module | Consumes | Notes |
|---|---|---|
| `storebro.deck` | `hull.body.Shape`, `hull.document`, `hull.parameters.sheer_height_aft/fwd` | Reads the sheer parameters via `_sample_hull_sheer`. New sheer values flow through automatically. |
| `storebro.interior` | `hull.body.Shape`, `hull.document` | Compartment envelope-fit against the new (different) hull interior. The Alternativ1-5 YAML positions stay valid as long as the hull volume contains them — which the new larger draft + same beam ensures. |
| `storebro.export` | `hull.body.Shape`, `hull.document` | Exports the new-shape body. Hash baselines re-seed in polish phase. |
| `storebro.cli` | All of the above (via composition) | `storebro build` produces v1.0.1-style FCStd. |

**Verification**: spec 007's tasks list includes a CLI smoke test and all-downstream-module re-runs.

---

## Semver

- **PATCH (v1.0.0 → v1.0.1)**: shape change with additive parameter. Default values of existing parameters change, but the *names and types* don't.
- **MINOR**: would be required if any existing parameter changed type (e.g., float → int) or was removed.
- **MAJOR**: would be required if the `Hull` dataclass shape changed or `build_hull` signature changed.

This spec is **PATCH**. The library-wide release becomes **v1.0.1** once shipped.

---

## Out of scope (deferred markers in spec.allium)

- `HullModule.hard_chine_variant` — true hard chine instead of rounded bilge; v1.1+.
- `HullModule.compound_curved_sections` — cubic-spline bilge curves with per-station variation; v1.1+.
- `HullModule.body_plan_from_primary_source` — full naval-architecture fidelity from a primary lines drawing; v1.1+.

All three confirmed `Defer to v1.1+` by the user during clarify phase.
