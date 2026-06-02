# Contract: Render API (public surface)

All additive. Version bump 1.1.0 → 1.2.0 (MINOR, constitution VI). No existing signature changes except new keyword-only/defaulted parameters.

## New module `storebro.render`

### `RenderAttribute` (frozen dataclass, public)

```python
@dataclass(frozen=True)
class RenderAttribute:
    color: tuple[float, float, float, float]   # RGBA, each in [0,1]
    material: str                                # FreeCAD material name
```

### `PALETTE: Mapping[str, RenderAttribute]` (public constant)

Read-only mapping `role -> RenderAttribute`. MUST contain every role in data-model.md plus `"DEFAULT"`.

### `role_for_label(label: str) -> str` (public, pure)

Returns a role key guaranteed present in `PALETTE`. Unmatched identifiers return `"DEFAULT"`. No FreeCAD import required. The applier resolves each object via its `Name` first, then `Label` (private `_role_for_object`), because the construction-time `Name` is the canonical role string.

### `apply_render_attributes(objects, *, enabled=True) -> int` (public)

- `objects`: iterable of FreeCAD document objects.
- `enabled=False`: no-op, returns `0`, leaves default appearance.
- `enabled=True`: for each object sets `App::PropertyColor` `"RenderColor"` + `App::PropertyMaterial` `"RenderMaterial"` + `App::PropertyString` `"RenderMaterialName"` (group `"Render"`) from the resolved palette entry, plus best-effort `ViewObject` color/transparency when a view object is present. Never mutates `.Shape`. Returns count applied.

## Changed build functions (additive kwarg)

Each grows a keyword parameter `apply_render_attributes: bool = True`. When `True`, the function applies palette attributes to the top-level objects it created before returning its aggregate.

```python
build_hull(..., apply_render_attributes: bool = True) -> Hull
build_deck(..., apply_render_attributes: bool = True) -> Deck
build_interior(..., apply_render_attributes: bool = True) -> Interior
build_propulsion(..., apply_render_attributes: bool = True) -> Propulsion
```

Back-compat: existing callers (no kwarg) now get a colored model by default. Geometry is unchanged.

## CLI contract

```
storebro build [...] [--no-colors]
```

- `--no-colors`: build a neutral model; threads `apply_render_attributes=False` to every `build_*`.
- Default (flag absent): colored model.
- `storebro info` / `storebro list-layouts`: unchanged.

## `storebro.__init__` exports (additive)

`RenderAttribute`, `PALETTE`, `role_for_label`, `apply_render_attributes` added to `__all__`. `__version__` → `"1.2.0"`.

## Invariants (verifiable)

1. `set(PALETTE) ⊇ {hull, superstructure, frame, glass, trim, metal, bulkhead, engine, steel, bronze, DEFAULT}`.
2. `PALETTE["glass"].color[3] < 1.0` (translucent).
3. Every `RenderAttribute.color` channel ∈ `[0,1]`; every `.material` non-empty.
4. `apply_render_attributes(objs, enabled=False)` adds zero properties.
5. Applying attributes changes no object's `Shape.Volume`, `BoundBox`, `Solids` count, or `isValid()`.
6. Two builds with identical inputs → identical `RenderColor`/`RenderMaterialName` on every object; STEP/STL/BREP exports byte-identical.
7. `role_for_label("Deck_WindshieldGlass") == "glass"` and `role_for_label("Deck_Windshield") == "frame"` (most-specific-first ordering).
8. `role_for_label("<unknown>") == "DEFAULT"`.
