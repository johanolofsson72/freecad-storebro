# Public API Contract: Interior Detail — Alternativ3, 4 & 5

**No public API change.** No new names, no signature change. `build_interior`
keeps its spec 012 signature (including `parameters_furniture`).

## Behavioral contract (the delta)

| Guarantee | Assertion |
|---|---|
| Alt3 furnished | `build_interior(h, d, "Alternativ3")` → all compartments `is_furnished` |
| Alt4 furnished | `build_interior(h, d, "Alternativ4")` → all compartments `is_furnished`; galley counter `Solids == 1` in the smaller galley |
| Alt5 furnished, no galley | `build_interior(h, d, "Alternativ5")` → forward_cabin/head/salon furnished, no galley furniture, no error |
| Custom layout boxy | a non-canonical YAML path → compartments `is_furnished == False` |
| Default fit | default furniture raises no envelope-overflow error on Alt3/4/5 |
| Inherited | reproducibility, rollback, manifold, validation — all hold (shared builders) |

## Versioning

`storebro.__version__ == "1.0.7"` == `pyproject.toml` version (guarded by the spec 010 version-consistency test).
