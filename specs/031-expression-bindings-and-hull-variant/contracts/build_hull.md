# Public API Contract Delta — hull variant

Single additive, backward-compatible change to `build_hull` + the `Hull` wrapper. Item 2 (expression
bindings) adds **no** public surface this spec.

## Added

```python
def build_hull(
    parameters: HullParameters | None = None,
    *,
    parameters_glazing: HullGlazingParameters | None = None,
    hull_variant: Literal["standard", "hard_chine"] = "standard",   # NEW
    document: Any = None,
    name: str = "Hull",
    apply_render_attributes: bool = True,
) -> Hull: ...
```

`Hull` gains two readable attributes:

```python
hull.hull_variant     # "standard" | "hard_chine" (requested)
hull.variant_applied  # bool — False iff hard-chine fell back to the standard hull
```

CLI: `storebro build --hull-variant {standard,hard_chine}` (default `standard`).

## Unchanged (no breaking change)

- `HullParameters` (frozen dataclass) — no new field; fixtures byte-identical.
- `build_hull` default behaviour: `hull_variant="standard"` reproduces the pre-031 hull byte-for-byte.
- The `Hull.bbox` / `Hull.volume` properties, the loft/mirror/porthole pipeline, render attributes.
- Every existing caller (deck/interior/propulsion/export/CLI) is unaffected — the default is unchanged.

## Versioning

MINOR bump (additive keyword + additive `Hull` fields + back-compat default): `1.14.0 → 1.15.0`.

## Construction errors (fail-fast)

`build_hull(hull_variant=<unknown>)` raises `HullParameterError("hull_variant", value,
"standard|hard_chine")` before any FreeCAD call.

## Deferred (no contract this spec)

Expression-engine bindings (`obj.setExpression(...)`) — designed in research.md, deferred per the
2026-06-13 user decision; no public surface added.
