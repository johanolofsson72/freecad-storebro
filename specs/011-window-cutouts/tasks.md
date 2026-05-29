# Tasks: Window & Porthole Cutouts

**Input**: Design documents from `specs/011-window-cutouts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/python-api.md

**Tests**: REQUIRED — constitution V + spec.md Success Criteria. Functional coverage (≥1 test per implemented function) + destructive validation across the 6 attack categories.

> **Verification status (2026-05-29):** FreeCAD is **not installed on the implementation host**, so the `requires_freecad` geometry tier and the GUI visual signoff are **WRITTEN but PENDING execution on a FreeCAD 1.1+ host**. Boolean Pockets are more runtime-fragile than spec 010's additive bodies; the blind-recess-into-solid design (clarify decisions) minimizes that, but the geometry run MUST complete before tagging v1.0.5. Verified locally: unit tests, `ruff check src/ tests/`, `mypy --strict src/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different file, no incomplete-task dependency)
- **[Story]**: US1 (portholes), US2 (cabin windows), US3 (windshield frame+glass)

---

## Phase 1: Setup

- [x] T001 Bump version: `version = "1.0.5"` in `pyproject.toml` and `__version__ = "1.0.5"` in `src/storebro/__init__.py`. (The version-consistency test from spec 010 guards the match.)

## Phase 2: Foundational (BLOCKING)

- [x] T002 In `src/storebro/hull.py`, add `PortholeParameters` + `HullGlazingParameters` frozen dataclasses with `__post_init__` raising `HullParameterError` (data-model §1). Add `Porthole` wrapper (§3.1). Extend `Hull` aggregate with `portholes` + `parameters_glazing` fields. Update `hull.__all__`.
- [x] T003 In `src/storebro/deck.py`, add `CabinWindowParameters`, `WindshieldGlazingParameters`, `DeckGlazingParameters` frozen dataclasses with `__post_init__` raising `DeckParameterError` (data-model §2). Add `CabinWindows` + `WindshieldGlass` wrappers; add `glass_pane` field to `Windshield`; extend `Deck` with `cabin_windows` + `parameters_glazing`. Update `deck.__all__`.
- [x] T004 Update `src/storebro/__init__.py` imports + `__all__` (alphabetical) to export the 5 new public dataclasses (contracts/python-api.md). Verify no new cross-module imports (hull/deck keep their import sets).
- [x] T005 [P] Unit tests for each new dataclass validation branch: `tests/unit/test_porthole_parameters.py`, `test_hull_glazing_parameters.py`, `test_cabin_window_parameters.py`, `test_windshield_glazing_parameters.py`, `test_deck_glazing_parameters.py`. Cover positivity, corner-radius bound, forward_x<aft_x, enabled flag, default_factory independence.

## Phase 3: User Story 1 — Portholes in the hull (P1) 🎯 MVP

**Goal**: blind circular porthole recesses cut into the hull topsides by default, hull stays manifold.

**Independent test**: `build_hull()` → `hull.portholes.count == 6`, hull `Shape.Solids == 1`, every porthole above the waterline.

- [x] T006 [US1] In `hull.py`, implement `_validate_hull_glazing(hull-derived dims, params)` raising `HullParameterError` for recess_depth ≥ local half-beam, porthole at/below waterline, diameter ≥ freeboard (data-model §6).
- [x] T007 [US1] In `hull.py`, implement `_cut_portholes(body, resolved_params, glazing, added)` — per porthole, an XZ-parallel datum at the topside outer-Y, a circular sketch, and a `PartDesign::Pocket` (Length=recess_depth) appended after the Mirror (new Tip). Port + starboard symmetric; derive forward_x/aft_x/height from the actual hull geometry when sentinel 0. Zero-count fallback (FR-011).
- [x] T008 [US1] In `hull.py`, add the post-cut manifold assertion (`Solids == 1`, `Shape.isValid()`) raising `HullConstructionError` (FR-008). Wire `_cut_portholes` into `build_hull` after `_apply_loft_and_mirror`, inside the existing try/rollback; resolve `parameters_glazing or HullGlazingParameters()`; populate `Hull.portholes`.
- [x] T009 [P] [US1] Geometry test `tests/geometry/test_hull_portholes_manifold.py`: default hull has 6 portholes, `Shape.Solids == 1`, `Shape.isValid()`, all centers above waterline; symmetric port/starboard.
- [x] T010 [P] [US1] Geometry test `tests/geometry/test_hull_porthole_pocket_feature_types.py`: portholes are `PartDesign::Pocket` features on HullBody; no raw mesh.

## Phase 4: User Story 2 — Cabin-trunk side windows (P2)

**Goal**: rounded-rect blind window recesses in the cabin-trunk sides by default; trunk stays manifold.

**Independent test**: `build_deck()` → `deck.cabin_windows.count == 2`, trunk solid count == 1.

- [x] T011 [US2] In `deck.py`, implement `_cut_cabin_windows(cabin_trunk, glazing, target_doc, added)` — per side, a rounded-rect sketch on a datum at the trunk side outer-Y, blind `PartDesign::Pocket` (Length=recess_depth) into the trunk body. Validate recess_depth < trunk half-width and opening fits the wall (raise `DeckParameterError`). Zero-count fallback.
- [x] T012 [US2] In `deck.py`, add post-cut manifold assertion for the cabin trunk (raise `DeckConstructionError`); wire `_cut_cabin_windows` into `build_deck`; populate `Deck.cabin_windows`.
- [x] T013 [P] [US2] Geometry test `tests/geometry/test_deck_cabin_windows.py`: default deck cuts 1 window/side, symmetric, trunk solid count == 1, each opening within the wall extents.

## Phase 5: User Story 3 — Windshield frame + glass (P3)

**Goal**: windshield becomes a frame (slab with through-opening) + a distinct glass-pane body; disabled → solid slab.

**Independent test**: `build_deck()` → `deck.windshield.body` has an opening, `deck.windshield.glass_pane` is a distinct body; `enabled=False` → solid slab, `glass_pane is None`.

- [x] T014 [US3] In `deck.py`, rework `_build_windshield`: after the slab loft, add a `PartDesign::Pocket` (Type=ThroughAll) of the central opening leaving `frame_border`; validate `2*frame_border < slab width/height` (raise `DeckParameterError`). Build a separate `Deck_WindshieldGlass` PartDesign::Body (Pad of the opening, thickness=glass_thickness) at the slab mid-plane. Return `Windshield` with `glass_pane` populated.
- [x] T015 [US3] In `deck.py`, honor `WindshieldGlazingParameters(enabled=False)`: keep the spec 008 solid slab, `glass_pane=None` (FR-011). Thread `parameters_glazing` through `build_deck` to `_build_windshield`.
- [x] T016 [P] [US3] Geometry test `tests/geometry/test_deck_windshield_frame_glass.py`: framed windshield has a through-opening (frame solid count == 1, volume < solid-slab volume), glass pane is a distinct body with positive volume; `enabled=False` → solid slab + `glass_pane is None`.

## Phase 6: Cross-cutting + destructive + signoff

- [x] T017 Geometry test `tests/geometry/test_glazing_default_call.py`: default `build_hull()`/`build_deck()` produce glazing; document contains the new Pocket/glass objects (SC-001, SC-002).
- [x] T018 Geometry test `tests/geometry/test_glazing_determinism.py`: two builds with identical inputs → identical glazed-body volumes (SC-005, II).
- [x] T019 Geometry test `tests/geometry/test_glazing_rollback.py`: inject a failure during a cut → document restored to pre-call state (FR-012, SC-006), for both hull and deck.
- [x] T020 Geometry test `tests/geometry/test_glazing_zero_counts.py`: zero portholes / zero windows / windshield disabled build the un-cut solids without raising (FR-011).
- [x] T021 Geometry test `tests/geometry/test_glazing_stl_watertight.py`: `export_stl` of the default glazed hull still yields a watertight mesh (SC-004, the spec 009 regression guard).
- [x] T022 [P] Destructive unit tests in `tests/unit/test_glazing_destructive_validation.py`: 6 attack categories at the dataclass layer — invalid (negative/zero), boundary (corner_radius*2 == height, frame_border at half-width, forward_x == aft_x), type misuse, zero-count no-ops. ≥8 scenarios.
- [x] T023 Update existing windshield tests for the frame+glass change: `tests/geometry/test_deck_default_call.py`, `tests/geometry/test_deck_default_labels.py`, and any windshield-single-solid assertion (expected back-compat behavior change per spec Assumptions).
- [x] T024 [P] Update `tests/unit/test_deck_public_docstrings.py` + `test_hull_public_docstrings.py` coverage (new public names need one-line docstrings with `>>>` examples); confirm `test_deck_back_compat.py` + `test_hull_*` still green.
- [x] T025 Geometry visual-signoff test `tests/geometry/test_glazing_visual_signoff.py`: produce `tests/fixtures/signoff/storebro_v1_0_5_signoff.FCStd`, record SHA-256, assert reproducible build (mirrors spec 010's signoff test).
- [x] T026 Run the full gate: `uv run pytest`, `uv run ruff check src/ tests/`, `uv run mypy src/`. Fix failures. Then `graphify update .`.

---

## Dependencies & execution order

- Phase 1 → 2 → 3 (MVP) → 4 → 5 → 6.
- Phase 2 (T002–T005) BLOCKS all stories (dataclasses + aggregates + exports first).
- US1 touches `hull.py`; US2/US3 touch `deck.py` — US1 is independent of US2/US3 and can land first. T008/T012/T015 wire into the single builder per module (sequential within a module).
- [P] test tasks touch distinct new files.

## MVP scope

US1 (portholes) alone is a shippable increment — the highest-impact "this hull has a cabin" cue and the riskiest mechanic, so it leads.

## Implementation strategy

Land Phase 1+2, then US1 end-to-end (impl + manifold assertion + tests), then US2, then US3, then cross-cutting/destructive/signoff. Keep each module's rollback list inclusive of every added object so partial failure rolls back the whole build.
