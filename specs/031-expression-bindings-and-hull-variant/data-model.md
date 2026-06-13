# Phase 1 Data Model — hull variant

Item 1 only (item 2 ships no code). No new dataclass, no new state machine.

## `build_hull` (function signature, `src/storebro/hull.py`)

| Param | Type | Default | New? | Notes |
|---|---|---|---|---|
| `parameters` | `HullParameters \| None` | `None` | existing | — |
| `parameters_glazing` | `HullGlazingParameters \| None` | `None` | existing | — |
| **`hull_variant`** | **`Literal["standard","hard_chine"]`** | **`"standard"`** | **NEW (keyword)** | mirrors `build_deck.superstructure_variant`; validated before any FreeCAD call |
| `document` / `name` / `apply_render_attributes` | … | … | existing | — |

Validation (before FreeCAD, alongside the existing param checks):
`if hull_variant not in ("standard", "hard_chine"): raise HullParameterError("hull_variant",
hull_variant, "standard|hard_chine")`.

## `_StationProfile` (existing frozen dataclass)

| Field | Type | Default | New? | Notes |
|---|---|---|---|---|
| `chine_z_factor` | float | `0.6` | **NEW (additive)** | replaces the literal `0.6` chine-depth multiplier in `_create_pentagon_legacy_station_sketch`. Default 0.6 → standard byte-identical. Hard-chine sets `_HARD_CHINE_CHINE_Z_FACTOR` (0.35). |

(All existing fields unchanged.)

## Module constants (new, named — constitution I)

| Constant | Value | Meaning |
|---|---|---|
| `_HARD_CHINE_BEAM_BLEND` | `0.5` | fraction the chine half-beam moves from `half_beam_bottom` toward `half_beam_top` |
| `_HARD_CHINE_CHINE_Z_FACTOR` | `0.35` | chine-depth factor for hard-chine stations (vs 0.6 standard) |

## `_compute_stations` (existing)

Signature gains `hull_variant: str = "standard"`. For `hull_variant == "hard_chine"`, each
**non-stem** `PENTAGON_LEGACY` station is built with:
`half_beam_at_bottom' = half_beam_bottom + (half_beam_top - half_beam_bottom) * _HARD_CHINE_BEAM_BLEND`
and `chine_z_factor = _HARD_CHINE_CHINE_Z_FACTOR`. Stem + thin-stem profiles unchanged. `"standard"`
path unchanged (chine_z_factor defaults to 0.6).

## `Hull` (existing dataclass wrapper)

| Field | Type | Default | New? | Notes |
|---|---|---|---|---|
| `hull_variant` | str | `"standard"` | **NEW (additive)** | the requested variant |
| `variant_applied` | bool | `True` | **NEW (additive)** | `False` iff hard-chine fell back to standard (FR-006/FR-010) |

Additive defaulted fields — `Hull` is only constructed inside `build_hull`, so this is non-breaking
(same pattern as the spec 011 `portholes`/`parameters_glazing` additions).

## CLI (`src/storebro/cli.py`)

`storebro build` gains `--hull-variant {standard,hard_chine}` (default `standard`), passed to
`build_hull(hull_variant=...)`, mirroring `--superstructure`. Reflected in `info`/JSON output.

## Derived build-time properties (asserted by `requires_freecad` tests, not stored)

| Property | Meaning |
|---|---|
| `Shape.Solids == 1` and `Shape.isValid()` | single manifold solid (or standard fallback) |
| amidships `half_beam_bottom/half_beam_top` (hard_chine) > standard's | chine pushed outboard (SC-002) |
| `hull.hull_variant`, `hull.variant_applied` | variant bookkeeping (FR-010) |
| standard build == pre-031 hull (byte/volume) | default preserved (SC-001) |
