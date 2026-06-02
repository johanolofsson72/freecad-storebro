# Data Model: Render Attributes

This is a spec-only cosmetic feature — **no new geometric entities, no state transitions**. The "data model" is the cosmetic value objects and the palette mapping.

## Value object: `RenderAttribute`

Frozen dataclass — the appearance of one body role.

| Field | Type | Notes |
|-------|------|-------|
| `color` | `tuple[float, float, float, float]` | RGBA, each in `[0.0, 1.0]`. Alpha < 1.0 marks translucency (glass). |
| `material` | `str` | FreeCAD material name (e.g. `"gelcoat_white"`, `"teak"`, `"chrome"`, `"glass"`, `"bronze"`, `"steel"`, `"engine_enamel"`, `"default"`). |

Validation (constructed only from the palette, so values are fixed constants):
- each color channel ∈ `[0.0, 1.0]`
- `material` non-empty

## Mapping: `PALETTE: dict[str, RenderAttribute]`

Single source of truth. Keys are **roles**, not labels. Intent (exact RGBA is an implementation detail tuned to `docs/references/`):

| Role | Color intent | Material | Applies to (labels) |
|------|-------------|----------|---------------------|
| `hull` | gelcoat off-white | `gelcoat_white` | `HullBody` |
| `superstructure` | gelcoat off-white | `gelcoat_white` | `Deck_DeckPlate`, `Deck_CabinTrunk`, `Deck_Hardtop`, `Deck_AnchorLocker` |
| `frame` | metallic/dark frame | `frame_alloy` | `Deck_Windshield` |
| `glass` | translucent blue-grey, alpha ≈ 0.35 | `glass` | `Deck_WindshieldGlass` |
| `trim` | warm teak/mahogany brown | `teak` | `Deck_Rubrail*`, interior furniture/compartment bodies |
| `metal` | light-grey metallic (chrome/stainless) | `chrome` | `Deck_Railings*`, `Deck_BowPulpit`, `Deck_Cleat*`/`Deck_Cleats`, `Deck_Lifelines`, `Deck_HardtopPillars`/`Deck_Pillar*` |
| `bulkhead` | light neutral | `paint_white` | interior bulkhead bodies |
| `engine` | dark grey-green | `engine_enamel` | `Propulsion_Engine`, `Propulsion_EngineBed` |
| `steel` | steel metallic | `steel` | `Propulsion_Shaft` |
| `bronze` | bronze | `bronze` | `Propulsion_Propeller`, `Propulsion_Rudder` |
| `DEFAULT` | neutral grey | `default` | any unmatched label (FR-010) |

## Role resolution: `role_for_label(label: str) -> str`

Pure function. Ordered match (most-specific first so `Deck_WindshieldGlass` wins over `Deck_Windshield`, and `Deck_Rubrail` is `trim` not `metal`). Returns a role key always present in `PALETTE`; unmatched → `"DEFAULT"`. No FreeCAD dependency → unit-testable. The applier feeds it the object's `Name` first, then `Label`, via the private `_role_for_object`.

## Operation: `apply_render_attributes(objects, *, enabled=True) -> int`

| Aspect | Behavior |
|--------|----------|
| Input | iterable of FreeCAD document objects (top-level shape-bearing bodies) |
| `enabled=False` | no-op; returns 0; objects keep FreeCAD default appearance (FR-009) |
| Per object | resolve role from `.Name` first then `.Label` (the construction-time `Name` is the canonical role string; `build_hull(name=...)` leaves `Name="HullBody"` but `Label="Hull"`) → `PALETTE[role]`; add/set `App::PropertyColor` (`"RenderColor"`, group `"Render"`) to `color`; add/set `App::PropertyMaterial` (`"RenderMaterial"`, group `"Render"`) with `DiffuseColor = color` and `Transparency = 1 - alpha`; add/set `App::PropertyString` (`"RenderMaterialName"`) to `material`; if `obj.ViewObject` is not `None`, set `ShapeColor` and `Transparency = round((1-alpha)*100)` |
| Idempotent | re-applying with same palette yields identical stored values (adds property only if absent) |
| Geometry | never touches `.Shape` — volume/bbox/solids/validity unchanged (FR-011) |
| Returns | count of objects to which attributes were applied |

## Determinism notes

- `PALETTE` is a module-level constant dict of constant `RenderAttribute`s — no runtime computation, no randomness, no env/time input (FR-004).
- RGBA is stored quantized to 8-bit per channel by FreeCAD; quantization is a pure function of the input → reproducible.
- Objects are processed in caller-supplied order (each `build_*` supplies a fixed order) → deterministic.
- STEP/STL/BREP exports carry no appearance → byte-identical regardless of coloring (FR-012).
