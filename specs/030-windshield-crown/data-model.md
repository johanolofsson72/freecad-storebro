# Phase 1 Data Model — windshield crown

One additive field on an existing frozen dataclass. No new entity, no new state machine.

## `WindshieldParameters` (existing, `src/storebro/deck.py`)

| Field | Type | Default | New? | Constraint |
|---|---|---|---|---|
| `base_z` | float | 0.0 | existing | — |
| `top_z` | float | 750.0 | existing | `top_z > base_z` |
| `rake_angle_base` | float | 35.0 | existing | `[-10, 60]°` |
| `rake_angle_top` | float | 38.0 | existing | `[-10, 60]°` |
| `base_width` | float | 2050.0 | existing | `> 0` |
| `top_width` | float | 1800.0 | existing | `> 0`, `≤ base_width` |
| `thickness` | float | 25.0 | existing | `> 0` |
| **`crown_height`** | **float** | **60.0** | **NEW** | **`0.0 ≤ crown_height < top_width / 2`; finite (NaN/±inf rejected via spec 029 guard)** |

### Validation (`__post_init__`)

Order (new check appended after the existing blocks):

1. `_reject_nonfinite_floats(self)` — already present (spec 029); now also covers `crown_height`
   (it iterates every float field) → NaN/±inf rejected automatically.
2. existing positivity / rake / curvature-radius checks — unchanged.
3. **NEW**: `if not (0.0 <= self.crown_height < self.top_width / 2): raise
   DeckParameterError("windshield_crown_height", self.crown_height, "[0, top_width/2) mm")`.

`crown_height = 0.0` is accepted (OFF sentinel). Negative → rejected (fails `>= 0.0`). NaN/±inf →
rejected by step 1.

### `to_superstructure_parameters()` legacy bridge

The legacy `DeckParameters` → `WindshieldParameters` bridge (deck.py ~283) constructs a
`WindshieldParameters` from legacy fields. `crown_height` is **not** a legacy field, so it takes the
dataclass default (60.0) — the legacy path also gets the crown by default, consistent with the new
default. (If byte-identical legacy output is later required, the bridge can pass `crown_height=0.0`;
the spec defaults to crowned, so we keep 60.0 — confirmed acceptable: legacy geometry already
changed across specs 007/008/020.)

## Derived build-time entity (not persisted) — the windshield body

These are observable properties asserted by `requires_freecad` tests, not stored fields:

| Property | Meaning |
|---|---|
| `Shape.Solids == 1` and `Shape.isValid()` | single manifold solid (or fallback) |
| top-edge Z at Y=0 − top-edge Z at corner ≈ `crown_height` | crown applied (when crowned) |
| `Deck_Windshield` + `WindshieldFrameOpening` + `Deck_WindshieldGlass` present | frame/glass preserved |
| `Windshield(body, rake_degrees, glass_pane)` wrapper shape | unchanged public surface (FR-011) |
