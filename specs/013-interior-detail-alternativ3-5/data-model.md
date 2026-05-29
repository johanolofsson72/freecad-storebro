# Phase 1 Data Model: Interior Detail — Alternativ3, 4 & 5

**No new entities or dataclasses.** This spec reuses the spec 012 furniture
model (`BerthParameters`, `GalleyParameters`, `HeadParameters`,
`SalonParameters`, `BulkheadParameters`, `FurnitureParameters`) and the
`Compartment` wrapper unchanged.

## §1 The single production change

```python
# interior.py — before (spec 012)
_FURNISHED_LAYOUTS: frozenset[str] = frozenset({"Alternativ1", "Alternativ2"})

# after (spec 013)
_FURNISHED_LAYOUTS: frozenset[str] = frozenset(
    {"Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"}
)
```

Equivalently, reuse the existing `_CANONICAL_LAYOUT_NAMES` constant so the two
cannot drift: `_FURNISHED_LAYOUTS = _CANONICAL_LAYOUT_NAMES`.

## §2 Behavior

- `build_interior(layout=<any canonical name>)` → furnished (per-type dispatch).
- `build_interior(layout=<custom YAML path>)` → boxy placeholders (unchanged).
- A canonical layout missing a compartment type (Alt5: no galley) → that type's
  furniture is simply not built; no error (existing dispatch behavior).

## §3 No signature / contract change

`build_interior` keeps its spec 012 signature (`parameters_furniture` already
present). No `__all__` change. Only `__version__` bumps to 1.0.7.
