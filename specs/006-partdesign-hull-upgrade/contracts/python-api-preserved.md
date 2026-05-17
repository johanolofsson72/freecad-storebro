# Contract: `storebro.hull` — public API (preserved)

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Date**: 2026-05-17

This spec is a **refactor**, not an API change. The public surface of `storebro.hull` is frozen at the v0.1.0-alpha shape and continues to satisfy spec 001's original contract verbatim.

What follows is the contract that MUST hold after spec 006 lands. Each row is enforced by an existing test in `tests/unit/` or `tests/geometry/` — no new contract surface is introduced.

---

## Public symbols re-exported from `storebro.hull`

```python
from storebro.hull import (
    HullParameters,          # frozen dataclass — hull input parameters
    Hull,                    # dataclass — build_hull return value
    HullParameterError,      # exception — invalid input parameters
    HullConstructionError,   # exception — FreeCAD construction failure
    build_hull,              # function — the entry point
)
```

`storebro.hull.__all__` is unchanged. The re-exports in `storebro/__init__.py` are unchanged.

---

## `HullParameters` — input dataclass

```python
@dataclass(frozen=True)
class HullParameters:
    loa: float = 10.35                  # RC34 1972 default
    beam_max: float = 3.20
    draft: float = 0.95
    freeboard: float = 0.95
    deadrise_amidships: float = 16.0    # degrees
    sheer_height_aft: float = 0.85
    sheer_height_fwd: float = 1.30
    transom_angle: float = 12.0         # degrees from vertical
```

- Frozen dataclass (hashable). Default values match the canonical Storebro Royal Cruiser 34 1972.
- `__post_init__` validates positive lengths, valid angle ranges. Raises `HullParameterError` on invalid input.

**Field count: 8. No additions, removals, or renames in spec 006.**

---

## `Hull` — return value dataclass

```python
@dataclass
class Hull:
    body: Any                         # FreeCAD PartDesign::Body with .Shape
    parameters: HullParameters        # the parameters used to build
    document: Any                     # FreeCAD Document hosting the Body
    label: str                        # Body.Label (e.g., "Hull" or "Hull001")
    build_duration_seconds: float     # perf_counter() delta
```

- 5 fields, frozen at spec 001's contract.
- `body.Shape` is a closed manifold solid (positive volume, watertight).
- `body` has the eight named informational properties (`Loa`, `BeamMax`, `Draft`, `Freeboard`, `DeadriseAmidships`, `SheerHeightAft`, `SheerHeightFwd`, `TransomAngle`).
- `document` is a FreeCAD `App.Document` instance — never None on success.

**What spec 006 changes (transparent to consumers):**
- `body.TypeId` is now `"PartDesign::Body"` (was already the case in v0.1.0-alpha, but the Body was empty / broken).
- `body.Tip.TypeId` is `"PartDesign::Mirrored"` (was `"Part::MultiFuse"` in the broken v0.1.0-alpha; the new value is the FreeCAD-idiomatic full-hull feature).
- `body.Group` contains 12 PartDesign-derived child features (5 datum planes + 5 sketches + 1 AdditiveLoft + 1 Mirrored) instead of zero (the legacy implementation never successfully populated the Body).

---

## `HullParameterError` — input-error exception

```python
class HullParameterError(ValueError):
    parameter_name: str
    parameter_value: float | None
    valid_range: str
```

Unchanged from spec 001. Raised pre-FreeCAD by `__post_init__` and `_validate_hull_parameters`.

---

## `HullConstructionError` — system-error exception

```python
class HullConstructionError(RuntimeError):
    parameters: HullParameters | None
    underlying: BaseException | None
    detected_version: tuple[int, int] | None
    supported_range: str | None
```

Unchanged from spec 001. Raised inside `build_hull` for:
- Unsupported FreeCAD version (detected_version + supported_range populated).
- Any FreeCAD-side construction exception (underlying populated).
- Non-manifold loft result (Q3 clarify: fail-fast; underlying = the FreeCAD error message).

The CLI's `_INPUT_ERROR_TYPES` and `_SYSTEM_ERROR_TYPES` tuples in `storebro.cli` already reference both exception types — spec 005's exit-code dispatch continues to work.

---

## `build_hull` — entry point

```python
def build_hull(
    parameters: HullParameters | None = None,
    *,
    document: Any = None,
    name: str | None = None,
) -> Hull: ...
```

- Signature unchanged from spec 001.
- `parameters=None` → defaults to `HullParameters()` (the canonical RC34 1972).
- `document=None` → uses `FreeCAD.activeDocument()` or creates a fresh document.
- `name=None` → Body labeled `"Hull"`, auto-numbered on collision.

Behavior changes (transparent):
- Internal feature graph uses PartDesign types only.
- Construction failures roll back document state (no orphan sketches, datums, or features left behind).
- Returns the same `Hull` dataclass shape.

---

## What downstream modules consume

The following four public modules each consume `Hull.body.Shape` and/or `Hull.document`. After spec 006 lands, all four MUST continue to work without source code changes.

| Module | Consumes | Notes |
|---|---|---|
| `storebro.deck` | `hull.body.Shape`, `hull.document` | Deck plate aligns with hull sheer line; reads sheer from the shape. |
| `storebro.interior` | `hull.body.Shape`, `hull.document` | Compartment envelope-fit check against hull interior. |
| `storebro.export` | `hull.body.Shape`, `hull.document` | STEP/STL/BREP read `body.Shape`; FCStd reads `body.Document`. |
| `storebro.cli` | All of the above (via composition) | `storebro build` end-to-end. |

**Verification**: spec 006's tasks list includes a CLI smoke test (`uv run storebro build --out /tmp/boat.FCStd` exits 0 on a FreeCAD 1.1.1 host) and per-downstream-module geometry test passing requirements (the 86 failing tests turn green).

---

## Versioning

- **PATCH**: implementation-internal refactor (spec 006 is a PATCH-level change to the hull module from a semver perspective, even though it ships under v1.0.0). The PUBLIC surface is frozen.
- **MINOR**: would be required if `Hull` gained a new field or `build_hull` gained a new optional argument.
- **MAJOR**: would be required if any existing field is removed/renamed, or if `build_hull`'s signature changes incompatibly.

This spec is **PATCH** per its own definition. The library-wide release is **v1.0.0** because spec 006 is the gating fix for the v1.0.0 milestone.

---

## Out of scope (per Q1/Q2/Q3 clarifications)

- Bidirectional expression-engine bindings between Body properties and sketch constraints (`deferred HullBody.expression_engine_bindings` — v1.1+).
- PartDesign::Pad for keel longitudinal or any net-new geometric features (`deferred HullModule.partdesign_pad_for_keel`).
- Adaptive station spacing for extreme parameter combinations (`deferred HullModule.adaptive_station_spacing`).
- Public re-exposure of internal feature-graph entities (datum planes, sketches, loft, mirror) — they remain private implementation details accessible only via `hull.body.Group` introspection.
