# Quickstart — hard-chine hull variant

## Build a hard-chine hull

```bash
uv run storebro build --hull-variant hard_chine --out boat.FCStd
# default stays the round-ish standard hull:
uv run storebro build --out boat_standard.FCStd
```

## Library

```python
from storebro.hull import build_hull

standard = build_hull()                            # hull_variant="standard" (default)
hard     = build_hull(hull_variant="hard_chine")   # pronounced hard chine
hard.hull_variant      # "hard_chine"
hard.variant_applied   # True (False only if it fell back to standard)
```

Invalid variant fails fast:

```python
build_hull(hull_variant="deep_vee")   # HullParameterError: standard|hard_chine
```

## Verify

```bash
# Unit (no FreeCAD) — variant validation + default preservation + CLI wiring:
uv run pytest tests/unit/test_hull_variant.py -q

# Geometry (maintainer, needs FreeCAD) — manifold, variant-differs, reproducible:
uv run pytest -m requires_freecad -k hull_variant -q

# Full gates:
uv run pytest -m "not requires_freecad" -q && uv run ruff check src/ tests/ && uv run mypy src/
```

Then GUI-eyeball both variants in FreeCAD (constitution V) and record the hard-chine signoff
`.FCStd` size + SHA-256 in the register entry.

## Deferred

Expression-engine bindings (GUI edits propagating through the parametric history) are **not** in this
build — deferred per the 2026-06-13 decision, revisited in a FreeCAD-equipped session. See
`research.md` §D6.
