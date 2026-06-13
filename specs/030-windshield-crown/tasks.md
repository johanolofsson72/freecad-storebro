# Tasks: Windshield Crown (transverse arched top edge)

**Feature**: `specs/030-windshield-crown` | **Track**: light | **Spec**: [spec.md](./spec.md)

One user story (P1 — the crown is the whole feature). Single source file
(`src/storebro/deck.py`) + two new test files. FreeCAD is absent on the dev machine, so geometry
assertions are `requires_freecad` (maintainer runs them); unit tests cover validation.

## Phase 1: Setup

- [ ] T001 Confirm the working tree is clean and read the current `WindshieldParameters`,
  `_slab_sketch`, `_slab_sketch_rect`, `_build_windshield`, `_is_single_valid_solid`, and
  `_reject_nonfinite_floats` definitions in `src/storebro/deck.py` to anchor the edits.

## Phase 2: Foundational (blocking prerequisites)

- [ ] T002 Add a named module-level constant for the crown polyline resolution in
  `src/storebro/deck.py` (e.g. `_WINDSHIELD_CROWN_SEGMENTS = 16`, even so a vertex lands on the
  apex Y=0; no magic numbers in the body — constitution I).

## Phase 3: User Story 1 — Crowned windshield top edge (P1)

**Goal**: The windshield's transverse top edge arches upward at the centerline (default 60 mm),
falling to the corners; the frame opening + glass pane are preserved; reproducible + manifold or
flat-top fallback.

**Independent test**: build the default superstructure → top-edge Z at Y=0 exceeds top-edge Z at the
corners by ~`crown_height`, body is one solid, frame/glass present; `crown_height=0.0` reproduces
the pre-030 windshield byte-identically.

### Parameter + validation

- [ ] T003 [US1] Add the `crown_height: float = 60.0` field to `WindshieldParameters` in
  `src/storebro/deck.py` (after `thickness`), with a one-line docstring/comment noting mm, OFF=0.0,
  valid `[0, top_width/2)`.
- [ ] T004 [US1] In `WindshieldParameters.__post_init__`, append the bound check after the existing
  blocks: reject unless `0.0 <= crown_height < top_width / 2` with
  `DeckParameterError("windshield_crown_height", crown_height, "[0, top_width/2) mm")`. Confirm
  `_reject_nonfinite_floats(self)` already runs first so NaN/±inf is rejected (spec 029).

### Geometry — arched section sketch + crowned loft with fallback

- [ ] T005 [US1] Add a `_slab_sketch_arched` helper in `src/storebro/deck.py` mirroring
  `_slab_sketch` but replacing the single top edge with an `_WINDSHIELD_CROWN_SEGMENTS`-segment
  polyline tracing the circular-arc profile `y(x) = sqrt(R²−x²) − (R−r)` with `R=(hw²+r²)/(2r)`,
  `r=crown_height`, sampled at evenly spaced `x ∈ [−hw, +hw]`; bottom + side edges unchanged; close
  the loop with `_pd_close_loop_constraints`. Deterministic (no Sketcher arc/solver) per research D1.
- [ ] T006 [US1] Refactor the section-sketch + `AdditiveLoft` creation inside `_build_windshield`
  into an inner helper `_make_sections_and_loft(crowned: bool)` returning `(loft, created_objs)`;
  when `crowned` use `_slab_sketch_arched` for all three sections (uniform rise, matching vertex
  topology — research D2), else the existing `_slab_sketch` (byte-identical flat path).
- [ ] T007 [US1] Wire the manifold-or-fallback gate in `_build_windshield`: compute
  `want_crown = ws.crown_height > 0.0`; build `_make_sections_and_loft(want_crown)`; if
  `want_crown and not _is_single_valid_solid(body.Shape)` remove the crowned sketches+loft from the
  doc and the `added` list and restore `body.Tip` (the pulpit idiom ~deck.py:3403), then rebuild
  `_make_sections_and_loft(False)`. Keep the shared datums and the spec 011 frame/glass block
  untouched and running on the finalised body.
- [ ] T008 [US1] Verify the spec 011 frame opening + glass-pane block still runs unchanged after the
  gate (no edits needed beyond ensuring it executes on the finalised `body`); the crown only adds
  material above the corners so `frame_border` margin is preserved by construction (research D4).

### Tests — unit (no FreeCAD)

- [ ] T009 [P] [US1] Create `tests/unit/test_windshield_crown.py`: default `crown_height == 60.0`;
  accepts `0.0`; accepts a valid mid value; rejects negative, rejects `>= top_width/2`, rejects
  `nan`/`+inf`/`-inf` (each `DeckParameterError`); boundary `top_width/2` exactly rejected,
  `top_width/2 - epsilon` accepted.
- [ ] T010 [P] [US1] Extend `tests/unit/test_windshield_parameters.py` (and
  `test_deck_public_docstrings`/`__all__` coverage if applicable) so the new field doesn't regress
  existing parameter tests; ensure the dataclass still constructs with all-default kwargs.

### Tests — geometry (requires_freecad, maintainer runs)

- [ ] T011 [P] [US1] Create `tests/geometry/test_windshield_crown_geom.py` (`@pytest.mark.requires_freecad`):
  (a) default build → windshield top-edge Z at Y=0 > top-edge Z at corners by ≈ `crown_height`
  (within tolerance); (b) body is a single valid solid (`Solids == 1`, `isValid()`); (c) glazing on
  → `WindshieldFrameOpening` + `Deck_WindshieldGlass` present and frame border ≥ `frame_border` on
  all sides; (d) `crown_height=0.0` build is byte-identical to a pinned flat-top baseline
  (reproducibility / back-compat); (e) two default builds in one process are byte-identical.

### Existing-baseline audit (analyze remediation F1)

- [ ] T0AUDIT [US1] Audit existing `requires_freecad` windshield-dependent geometry tests for
  flat-top assumptions broken by the crowned default (60 mm): `tests/geometry/test_superstructure_curvature.py`,
  `test_deck_variant_backcompat.py`, `test_deck_determinism.py`, `test_render_determinism.py`,
  `test_render_apply.py`, `test_deck_windshield_frame_glass.py`. Where a test intends the *flat* top,
  pin it with `crown_height=0.0`; where it should reflect the new default, update the baseline.
  Determinism tests stay valid (output is still deterministic, just a new value). Record which
  baselines changed.

## Phase 4: Polish & cross-cutting

- [ ] T012 Bump version `1.13.2 → 1.14.0` (additive MINOR) in the package version source and add a
  CHANGELOG entry noting the visible default-geometry change (windshield now crowned by default;
  `crown_height=0.0` restores the flat top).
- [ ] T013 Run gates: `uv run pytest -m "not requires_freecad"`, `uv run ruff check .`,
  `uv run mypy src/`; fix any failures. Run the humanizer skill over the CHANGELOG/commit text
  before delivery.

## Dependencies

- T001 → T002 → (T003, T004) → (T005 → T006 → T007 → T008) → tests (T009–T011) → T012 → T013.
- T003/T004 (param) are independent of T005–T008 (geometry) but both precede the geometry tests.
- T009, T010, T011 are mutually parallel `[P]` (distinct files).

## Implementation strategy (MVP)

MVP = US1 in full (T001–T011): the crown plus its validation, fallback, and tests. T012–T013 are
release hygiene. There is no smaller viable slice — the feature is a single geometric refinement.
