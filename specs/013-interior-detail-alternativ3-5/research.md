# Phase 0 Research: Interior Detail — Alternativ3, 4 & 5

All "NEEDS CLARIFICATION" resolved in `/clarify`. This spec reuses spec 012's
furniture builders; the research is a fixture-fit check.

## R1 — The change: widen the gate

`interior.py` has `_FURNISHED_LAYOUTS = frozenset({"Alternativ1", "Alternativ2"})`.
Spec 013 widens it to all five canonical names
(`{"Alternativ1", ..., "Alternativ5"}`). Everything else — the per-type
dispatch in `_build_furnished_compartment`, the parameter dataclasses, the
galley manifold guard, rollback — is reused unchanged.

## R2 — Default furniture fits every Alt3/4/5 compartment (verified vs fixtures)

| Layout | Compartment | dims (L×W×H, m) | fit check |
|---|---|---|---|
| Alt3 | forward_cabin | 2.5×2.1×1.2 | berth base 0.35 < 1.2 ✓; insets fit |
| Alt3 | head | 1.2×1.0×1.4 | toilet 0.5×0.4 + sink 0.4×0.3 fit in 1.2×1.0 ✓ |
| Alt3 | galley | 1.2×1.0×1.4 | counter 0.9 < 1.4; recess cuts (0.25L×0.4W) fit ✓ |
| Alt3 | salon | 4.0×2.6×1.8 | settee + table fit ✓ |
| Alt4 | galley | 0.9×1.6×1.4 | counter 0.9<1.4; cuts fit the 0.8×1.5 worktop ✓ |
| Alt4 | others | — | fit ✓ |
| Alt5 | forward_cabin/head/salon | — | fit ✓; **no galley compartment** |

The furniture builders inset/size relative to compartment dimensions, so a
smaller compartment yields proportionally smaller furniture — no default
overflow. The height guards (`base_height`, `counter_height` < compartment
height) pass for all.

## R3 — Alt5 has no galley

Alt5's fixture has 3 compartments (forward_cabin, head, salon); the salon
description notes an integrated galley. The per-compartment dispatch builds
furniture only for the types present, so Alt5 yields berth + head + salon +
bulkheads and no galley counter, with no error. Modeling the integrated galley
inside the salon is deferred.

## R4 — Custom (non-canonical) layouts stay boxy

The gate keys on canonical layout names, so a caller-supplied YAML path keeps
the boxy `_build_compartment` path (its compartment dims are unconstrained, so
default furniture may not fit). A custom-layout furniture mode is deferred.

## R5 — Version bump

`pyproject.toml` 1.0.6 → 1.0.7 and `storebro.__version__` → 1.0.7 (the spec 010
version-consistency test guards the match).
