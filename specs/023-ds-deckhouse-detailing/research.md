# Phase 0 Research — DS Deckhouse Detailing

## Decision 1 — Front-window recess on the raked face (rotated datum)

- **Decision**: Cut the front window with a `PartDesign::Pocket` on a `YZ_Plane`
  datum rotated about the global Y axis by `front_rake_angle`, positioned at the
  front-face center, with a manifold-or-skip gate.
- **Rationale**: Spike `/tmp/spike_023.py` built the real `_build_deckhouse`,
  added a rotated YZ datum (`Rotation(Vector(0,1,0), front_rake_angle)`,
  `AttachmentOffset` local `(0, face_cz, face_cx)`), and pocketed a centered
  rectangle: `Solids==1`, `isValid()==True` on the first attempt. The rake datum
  is a clean rectangular cut — no arcs — so it has none of the spec 022 arc-loft
  reproducibility trouble.
- **Skip gate**: if the cut ever fails `Solids==1 && isValid()`, the front recess
  is rolled back (deterministically — the gate depends only on geometry), and the
  side windows + raked screen still build.
- **Glass**: a thin pane on the raked face, built as a Pad on a parallel rotated
  datum just proud of the face (glass render role).

## Decision 2 — Mullions as raised Pad bosses

- **Decision**: For each side window, add `mullions_per_window` thin raised
  vertical `PartDesign::Pad` bosses on the deckhouse side face, fused into the
  body.
- **Rationale**: Additive Pads on a PartDesign body fuse to a single solid by
  construction (the spec 016 deckhouse Pad/Pocket idiom). Bosses on the outer
  face read as the window divider bars. Zero count reproduces spec 016.
- **Alternatives**: splitting each recess into sub-recesses (rejected — more
  cuts, more non-manifold surface; raised bars are the clearer frame reading).

## Decision 3 — Helm door as a blind Pocket

- **Decision**: A tall door-shaped blind `PartDesign::Pocket` in a parameterized
  side wall (depth < half-width, like the side windows).
- **Rationale**: Identical manifold discipline to the spec 016 side windows. The
  deckhouse is a filled solid, so a blind recess reads as a closed door; a
  through-cut was reviewed and deferred (it would read as a tunnel).

## Decision 4 — Full DS interior via a bundled layout + `helm` type

- **Decision**: `build_interior(..., superstructure_variant="ds")` loads a
  bundled `DsSaloon.yaml` (enclosed helm saloon + galley + head + forward cabin),
  furnishes it with the spec 012/013 type-keyed builders plus a new `helm`
  furniture builder (console + seat), and uses the DS deckhouse headroom for the
  ceiling check. `"standard"` is untouched.
- **Rationale**: Reuses the proven YAML loader + furniture dispatch (specs
  004/012/013). The `helm` type slots into the existing per-type dispatch like
  `galley`/`head`/`salon`. The enclosed saloon needs the taller deckhouse
  headroom, so the ceiling validation switches limit in DS mode.
- **Alternatives**: a programmatic DS layout (rejected — the YAML-fixture path is
  the established idiom and keeps the layout data-driven); cut-through openings +
  hollow shell (reviewed and deferred — keeps the filled-solid deckhouse).

## Summary

The one novel construction (rotated-datum front recess) is spiked and manifold.
Everything else reuses specs 016/012/013 patterns. No NEEDS CLARIFICATION remain.
