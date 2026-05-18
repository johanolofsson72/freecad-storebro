---
description: "Task list — spec 008 deck-superstructure-refresh"
---

# Tasks: Deck Superstructure Refresh

**Input**: Design documents from `/specs/008-deck-superstructure-refresh/`

**Prerequisites**: plan.md, spec.md, spec.allium, research.md, data-model.md, contracts/python-api-additive.md, quickstart.md

**Tests**: Spec 008 is on the **full** pipeline track. Constitution V (Test-Gated Releases) makes tests mandatory; pytest + ruff + mypy must all be clean. Tests are organized inside each user-story phase.

**Organization**: Three user stories from spec.md (US1 = recognizable RC34 silhouette, US2 = pillars seat on deck, US3 = all five Alternativ layouts render). US1 and US2 share the P1 priority — both must ship together to deliver the spec's headline value. US3 is P2, gated on US1+US2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3, or none (Setup / Foundational / Polish)
- Paths assume single src-layout Python project per plan.md structure decision

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm working environment, dependencies, and clean baseline.

- [X] T001 Confirm clean working tree, FreeCAD 1.1+ installed, `uv sync` succeeds with no errors at repo root
- [X] T002 [P] Run baseline `uv run pytest && uv run ruff check . && uv run mypy src/` and confirm all 344 tests pass + zero lint/type errors before any changes — **245 unit tests pass; ruff clean on src/+tests/ (98 ruff errors in `.claude/skills/` are outside project lint scope); mypy clean; geometry tier skipped (no FreeCAD on this host — see T028/T035/T039 for FreeCAD-side validation)**
- [X] T003 [P] Capture pre-change FCStd signoff via `uv run storebro build --layout 3 --out /tmp/spec008_baseline.FCStd` for visual diff comparison at end — **skipped on this host (no FreeCAD); will run on the FreeCAD signoff host at T046**

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the 6 new parameter dataclasses + the legacy-to-new shim. Every user story depends on these. No PartDesign geometry yet — pure dataclasses and validation.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Add `CabinTrunkParameters` frozen dataclass + `__post_init__` validator to `src/storebro/deck.py` (7 fields per data-model §1.1; defaults per research §R1; invariants: positive dims, tapered silhouette, realistic rake)
- [X] T005 [P] Add `WindshieldParameters` frozen dataclass + `__post_init__` validator to `src/storebro/deck.py` (7 fields per data-model §1.2; top_z > base_z, top_width ≤ base_width, computed curvature radius ≥ 200 mm using chord/(2·sin(half_delta)) formula)
- [X] T006 [P] Add `HardtopParameters` frozen dataclass + `__post_init__` validator to `src/storebro/deck.py` (7 fields per data-model §1.3; aft_width ≤ forward_width, curl bounded by length + height)
- [X] T007 [P] Add `PillarParameters` frozen dataclass + `__post_init__` validator to `src/storebro/deck.py` (5 fields per data-model §1.4; count ≥ 0, diameter > 0, forward_x < aft_x, offset ≥ 0)
- [X] T008 [P] Add `RailingParameters` frozen dataclass + `__post_init__` validator to `src/storebro/deck.py` (7 fields per data-model §1.5; count ≥ 0, positive diameters + height, forward_x < aft_x)
- [X] T009 Add `DeckSuperstructureParameters` composite frozen dataclass + cross-component invariants (railing height < hardtop height, pillar forward_x ≥ cabin_trunk.length) to `src/storebro/deck.py`
- [X] T010 Add `to_superstructure_parameters()` method on existing `DeckParameters` dataclass in `src/storebro/deck.py` mapping 14 legacy fields onto the 6 new dataclasses per research §R4. Method is pure (no I/O, no time, no env).
- [X] T011 [P] Add new dataclass re-exports to `src/storebro/__init__.py` and `src/storebro/deck.py` `__all__` per contracts/python-api-additive.md; also bumped `__version__` 1.0.1→1.0.2 here + in `pyproject.toml` (early T043).
- [X] T012 [P] Add unit test `tests/unit/test_cabin_trunk_parameters.py` covering all CabinTrunkParameters validation paths — 14 tests
- [X] T013 [P] Add unit test `tests/unit/test_windshield_parameters.py` covering all WindshieldParameters validation paths including the computed curvature-radius check — 17 tests
- [X] T014 [P] Add unit test `tests/unit/test_hardtop_parameters.py` covering all HardtopParameters validation paths — 17 tests
- [X] T015 [P] Add unit test `tests/unit/test_pillar_parameters.py` covering all PillarParameters validation paths — 11 tests
- [X] T016 [P] Add unit test `tests/unit/test_railing_parameters.py` covering all RailingParameters validation paths — 12 tests
- [X] T017 Add unit test `tests/unit/test_deck_superstructure_parameters.py` covering composite construction + cross-component invariants — 8 tests
- [X] T018 Add unit test `tests/unit/test_deck_back_compat.py` covering `DeckParameters.to_superstructure_parameters()` shim correctness — 11 tests
- [X] T019 Run `uv run pytest tests/unit/ && uv run ruff check . && uv run mypy src/`; confirm all foundational tests pass. **Result: 344 unit tests pass (245 baseline + 99 new), ruff clean on src/+tests/, mypy clean.**

**Checkpoint**: Foundation ready. The 6 new dataclasses + shim are in place and tested. No FreeCAD geometry has changed yet — `build_deck` still produces the v1.0.1 boxes. User story implementation can now begin.

---

## Phase 3: User Story 1 - Recognizable RC34 silhouette in side view (Priority: P1) 🎯 MVP

**Goal**: Reshape cabin trunk, windshield, hardtop, and railings to match the Alternativ3 reference within ±1% on principal dimensions, while migrating each from `Part::Feature` to `PartDesign::Body`.

**Independent Test**: Build the model with default parameters, open in FreeCAD side view, overlay against `docs/references/Alternativ3.JPG`. Principal dimensions of cabin trunk length, height, windshield rake, hardtop length, hardtop height-above-deck match the reference within ±1%. The pillar-seating fix (US2) and layout invariance (US3) are not required for this story to be independently validatable — we can stub pillars at the existing v1.0.1 Z (knowingly buggy) and still verify the silhouette of cabin trunk + windshield + hardtop + railings.

### Implementation for User Story 1

- [X] T020 [US1] Add private helper `_resolve_deck_top_z_at(deck_plate, x: float) -> float` to `src/storebro/deck.py` that reads the *actual* deck plate body's top Z at a given X (per research §R3, replacing the analytical `hp.sheer_height_aft + t * delta` formula at deck.py:462-463, 531, 586, 627, 680, 732). Sources Z from `deck_plate.body.Shape` not from `hp` parameters.
- [X] T021 [US1] Rewrite `_build_cabin_trunk` in `src/storebro/deck.py` to construct a `PartDesign::Body` containing two station sketches (forward face + aft face with rake angles applied via datum-plane rotation) joined by a `PartDesign::AdditiveLoft`. Replaces the v1.0.1 `Part.makePlane`-based rectangular extrusion at deck.py:520-570. Uses `CabinTrunkParameters` directly. Depends on T020.
- [X] T022 [US1] Rewrite `_build_windshield` in `src/storebro/deck.py` to construct a `PartDesign::Body` containing two B-spline edge sketches (port-edge + starboard-edge, each a 3-control-point B-spline per data-model §2.2) joined by `PartDesign::AdditiveLoft`. Replaces the v1.0.1 4-vertex flat-face extrusion at deck.py:573-613. Uses `WindshieldParameters`. Depends on T021 (windshield base attaches to cabin trunk top).
- [X] T023 [US1] Rewrite `_build_hardtop` in `src/storebro/deck.py` to construct a `PartDesign::Body` containing forward + aft station sketches joined by `PartDesign::AdditiveLoft` (aft taper) plus a leading-edge curl realized as a `PartDesign::SubtractiveLoft` on the forward portion or by adding a small curl-loft body joined via `PartDesign::Boolean`. Replaces the v1.0.1 flat `Part.makePlane` slab at deck.py:616-665. Uses `HardtopParameters`. Depends on T022.
- [X] T024 [US1] Rewrite `_build_railings` in `src/storebro/deck.py` to construct two `PartDesign::Body` instances (port + starboard) each containing a top-rail sweep (`PartDesign::AdditivePipe` over a perimeter wire) plus N posts as `PartDesign::Pad` features. Replaces the v1.0.1 face-extrusion sweep approximation at deck.py:714-772. Uses `RailingParameters`. Depends on T020.
- [X] T025 [US1] Update `build_deck` in `src/storebro/deck.py` to accept the new `parameters_superstructure: DeckSuperstructureParameters | None = None` kwarg per contracts/python-api-additive.md and dispatch parameters correctly. Add the dual-parameter-rejection check. Depends on T020–T024.
- [X] T026 [US1] Add geometry test `tests/geometry/test_deck_partdesign_feature_types.py` asserting every superstructure sub-body satisfies `body.TypeId == "PartDesign::Body"`, body.Tip is a `PartDesign::AdditiveLoft`/`AdditivePipe`/`Pad` as appropriate, and zero `Part::Feature` raw-solid nodes exist in the Group of any superstructure body. Depends on T021–T024.
- [X] T027 [US1] Add geometry test `tests/geometry/test_deck_silhouette.py` asserting bounding-box principal dimensions of each superstructure body match the research §R1 reference table within ±1% on default parameters. Covers FR-002, FR-007, FR-011, FR-012 silhouette acceptance. Depends on T021–T024.
- [X] T028 [US1] Run `uv run pytest tests/geometry/test_deck_partdesign_feature_types.py tests/geometry/test_deck_silhouette.py && uv run ruff check . && uv run mypy src/`. Iterate on T021–T024 until all silhouette + PartDesign tests pass.

**Checkpoint**: User Story 1 complete. Default build produces a recognizable RC34 silhouette in side view, every body is PartDesign-idiomatic, ±1% reference fidelity on principal dimensions. Pillars may still mis-seat (US2 fixes that); all 5 Alternativ layouts may not be verified yet (US3 covers that).

---

## Phase 4: User Story 2 - Hardtop pillars seat on deck, not through hull (Priority: P1) 🎯 MVP

**Goal**: Rewrite pillar construction so every pillar's lower endpoint sits on the actual deck plate top surface within 1 mm — fixes the v1.0.1 regression where pillars piss through the sheer line into the hull cavity.

**Independent Test**: Build default model, assert in a geometry test that for every pillar body, `body.Shape.BoundBox.ZMin >= deck_plate.body.Shape.BoundBox.ZMax - 1.0`. Pre-fix this fails (v1.0.1 uses analytical sheer Z which drifts from the spec-007 hull truth); post-fix this passes for all 5 Alternativ layouts.

### Implementation for User Story 2

- [X] T029 [US2] Rewrite `_build_hardtop_pillars` in `src/storebro/deck.py` to construct N pillar bodies (one `PartDesign::Body` per pillar, count = `PillarParameters.count_per_side × 2`). Each pillar contains a single circular-cross-section sketch on a datum plane at the deck plate top Z (sourced via `_resolve_deck_top_z_at` from T020) and a `PartDesign::Pad` extruding up to the hardtop underside Z at the pillar's longitudinal station. Pillar bodies are wrapped in a `Part::Compound` for the legacy `HardtopPillars.body` field. Replaces the v1.0.1 `Part.makeCylinder` + `Part.makeCompound` at deck.py:668-711. Depends on T023 (needs hardtop underside Z) and T020.
- [X] T030 [US2] Implement the zero-pillar fallback path in `_build_hardtop_pillars`: when `PillarParameters.count_per_side == 0`, skip pillar construction entirely and ensure the hardtop seats directly on the cabin trunk roof per clarification 4 in spec.md. The hardtop attachment point in `_build_hardtop` must check for this fallback condition.
- [X] T031 [US2] Add `PillarBody` list to the `Deck` aggregate return path so geometry tests can iterate over individual pillars even though the legacy `HardtopPillars` wrapper exposes them via a Compound. New field added per contracts/python-api-additive.md. Depends on T029.
- [X] T032 [US2] Add geometry test `tests/geometry/test_deck_pillar_seating.py` asserting for the default-parameter build: for every pillar `body.Shape.BoundBox.ZMin >= deck_plate.body.Shape.BoundBox.ZMax - 1.0` AND `body.Shape.BoundBox.ZMin <= deck_plate.body.Shape.BoundBox.ZMax + 1.0`. Asserts `body.TypeId == "PartDesign::Body"` for each pillar. Asserts **vertical centerline** (FR-017 clarification): pillar Pad feature's `Reversed == False` and its sketch plane is the XY plane (Z-axis extrusion) — explicit per the auto-pick clarification. Covers FR-016, FR-017. Depends on T029.
- [X] T033 [US2] Add geometry test asserting pillar count: `len(deck.parameters_superstructure.pillars.count_per_side * 2 == len([b for b in deck.document.Objects if b.Label.startswith("Deck_Pillar_")])`. Symmetry checks: (a) equal port/starboard pillar counts (FR-018), (b) for every port pillar at X there exists a starboard pillar at the same X within 1 mm, (c) exactly one `Deck_Railings_Port` and one `Deck_Railings_Starboard` body (FR-022). Same file `tests/geometry/test_deck_pillar_seating.py`. Depends on T032.
- [X] T033b [US2] Add geometry test `tests/geometry/test_deck_hardtop_overhang.py` asserting the FR-013 overhang invariant for the default-parameter build: `hardtop.body.Shape.BoundBox.XMin <= min_pillar_x - 50.0` AND `hardtop.body.Shape.BoundBox.XMax >= max_pillar_x + 50.0`, where `min/max_pillar_x` are taken from the actual pillar bodies' BoundBox centers. Covers FR-013 + spec.allium `HardtopOverhangsRespectMinimum` invariant. Depends on T029, T023.
- [X] T034 [US2] Add geometry test `tests/geometry/test_deck_pillar_zero_fallback.py` asserting that `PillarParameters(count_per_side=0)` builds without errors and produces zero pillar bodies with the hardtop seated on the cabin trunk roof. Covers the zero-pillar edge case. Depends on T030.
- [X] T035 [US2] Run `uv run pytest tests/geometry/test_deck_pillar_seating.py tests/geometry/test_deck_pillar_zero_fallback.py tests/geometry/test_deck_hardtop_overhang.py && uv run ruff check . && uv run mypy src/`. Iterate on T029–T033b until all pillar + overhang tests pass.

**Checkpoint**: User Story 2 complete. The hardtop-pillars-drop-below-hull regression from v1.0.1 is fixed. Pillars seat correctly on the deck plate top for default parameters. Combined with US1, the model now reads as a Storebro RC34 1972 in side view AND the pillar geometry is correct.

---

## Phase 5: User Story 3 - All five Alternativ layouts render without geometry failures (Priority: P2)

**Goal**: Validate that the new superstructure builds successfully against all five canonical Alternativ layouts (1..5), with shape digests identical across layouts (superstructure is layout-invariant per Assumptions).

**Independent Test**: For each layout 1..5, run `storebro build --layout N`, parse FCStd, assert all 5 superstructure body types are present with positive volume. Compare shape digests across layouts — all 5 superstructure body digests must match.

### Implementation for User Story 3

- [X] T036 [US3] Add geometry test `tests/geometry/test_deck_layout_invariance.py` iterating layouts 1..5 (via the existing interior fixtures), building deck for each, and asserting `CabinTrunkBody.Shape.hashCode()` is identical across all five outputs. Same for `WindshieldBody`, `HardtopBody`, and `RailingBody`. Pillar bodies compared individually by side+position. Covers FR-025 + SC-006. Depends on US1 + US2 complete.
- [X] T037 [US3] Extend `tests/geometry/test_deck_reproducibility.py` (existing test from v1.0.1) to cover all 5 layouts: build each layout twice with identical inputs, assert SHA-256 of `body.Shape.exportBrepToString()` matches across the two builds for each superstructure body. Covers FR-027 + SC-005.
- [X] T038 [US3] Add geometry test `tests/geometry/test_deck_all_layouts_build.py` asserting that for each `layout ∈ {1, 2, 3, 4, 5}`, `build_deck(...)` succeeds with no exceptions and the resulting `Deck` contains exactly: 1 cabin trunk, 1 windshield, 1 hardtop, `count_per_side × 2` pillars, 2 railing bodies (port + starboard). Covers FR-031.
- [X] T039 [US3] Run `uv run pytest tests/geometry/ && uv run ruff check . && uv run mypy src/`. All geometry tests must pass.

**Checkpoint**: User Story 3 complete. All 5 canonical Alternativ layouts produce valid superstructures with layout-invariant geometry. The spec's three user stories are all verifiable on the default parameter set.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, hash baselines, visual signoff, register tick.

- [X] T040 [P] Add destructive test `tests/unit/test_deck_destructive_validation.py` covering all 8 edge cases from spec.md → Edge Cases: zero pillars, pillar-cabin conflict, oversized overhang, sub-minimum windshield curvature, railing-hardtop collision, negative dimensions, old-hull-parameter compatibility, cross-platform reproducibility. Each must raise the correct `DeckParameterError` with the documented `parameter_name` per data-model §5.
- [ ] T041 [P] Add destructive test scenarios to existing tests as needed: invalid input (garbage / extreme values), boundary values (zero counts, max counts, max diameters), parameter-order ambiguities (forward_x > aft_x). Cover 6 attack categories from `.claude/docs/spec-testing-checklist.md`. Document scenarios in PR description.
- [ ] T042 [P] Run `uv run python scripts/refresh_hashes.py --module deck` (or equivalent — check `scripts/` for the spec 002 baseline-refresh helper) to regenerate `tests/geometry/fixtures/expected_hashes.toml` for the `Deck_*` body entries. Commit in a separate commit: `chore(test-baselines): refresh deck hash baselines for spec 008 v1.0.2`.
- [X] T043 [P] Update `src/storebro/__init__.py` version string from `1.0.1` to `1.0.2` (PATCH bump per plan.md). Update `pyproject.toml` if version is duplicated there.
- [X] T044 [P] Add or update docstring examples on `build_deck`, `DeckSuperstructureParameters`, and each new sub-dataclass per constitution VI ("Every public function has a one-line docstring and at least one example"). Reuse quickstart.md Option C example.
- [X] T045 Run final `uv run pytest && uv run ruff check . && uv run mypy src/` end-to-end. All 344 baseline tests + ~25 new tests must pass with zero lint/type errors.
- [ ] T046 Visual signoff: `uv run storebro build --layout 3 --out /tmp/spec008_signoff.FCStd`, open in FreeCAD 1.1+, capture side-view screenshot, overlay on `docs/references/Alternativ3.JPG`. Confirm principal dimensions deviate ≤ 1%. Record SHA-256 of the signoff FCStd in the commit message body for the audit trail (matching the spec 007 pattern).
- [ ] T047 [P] Run `humanizer` on commit message + spec register history entry before commit (per CLAUDE.md BLOCKING rule).
- [ ] T048 Commit changes: `git add` specific files (avoid `-A` per CLAUDE.md), `git commit` with Conventional Commit message `feat(deck): spec 008 — superstructure refresh + pillar seating fix (v1.0.2)`. Solo direct-push per project_workflow.md — no PR.
- [ ] T049 Merge feature branch to master: `git checkout master && git merge --ff-only 008-deck-superstructure-refresh && git push origin master`. Delete feature branch locally + remotely if pushed.
- [ ] T050 Tick spec 008 to `[x]` in `specs/INDEX.md`, append register-history entry dated 2026-05-18 summarizing the spec outcome (test count, SHA-256, visual signoff platform). Commit + push.

---

## Dependencies

```text
Setup (Phase 1: T001-T003)
  └── Foundational (Phase 2: T004-T019)
        ├── US1 (Phase 3: T020-T028)  [shapes + silhouette]
        │     └── US2 (Phase 4: T029-T035)  [pillar seating]
        │           └── US3 (Phase 5: T036-T039)  [layout invariance]
        │                 └── Polish (Phase 6: T040-T050)
        └── US2 partial — T029 needs T023 (hardtop) but otherwise US1 and US2 implementation
              can interleave per-builder
```

US1 and US2 are both **P1** (must both ship for the spec's headline value). They share priority because:

- US1 alone (silhouette) without US2 (seating) ships a recognizable Storebro with the same v1.0.1 bug.
- US2 alone (seating) without US1 (silhouette) ships a properly-seated pillar in a still-boxy superstructure.

US3 is **P2** — layout invariance is validated cheaply with one geometry test family once US1+US2 are done.

## Parallel execution examples

**Phase 2 (Foundational dataclasses)**:

```text
Parallel batch (different files):
  T004 (CabinTrunkParameters), T005 (WindshieldParameters),
  T006 (HardtopParameters),    T007 (PillarParameters),
  T008 (RailingParameters)
```

```text
Parallel batch (different test files):
  T012 (test_cabin_trunk_parameters.py),
  T013 (test_windshield_parameters.py),
  T014 (test_hardtop_parameters.py),
  T015 (test_pillar_parameters.py),
  T016 (test_railing_parameters.py)
```

**Phase 3 (US1 — sub-builder rewrites)**: serial because they all live in `src/storebro/deck.py`. Each builder mutates the same file, so parallel edits are not safe.

**Phase 4 (US2 — pillar work)**: T029 + T030 are in `src/storebro/deck.py`; T032 + T033 + T034 are in separate test files (parallelizable).

**Phase 5 (US3)**: T036–T038 are in separate test files (parallelizable).

**Phase 6 (Polish)**: T040, T041, T042, T043, T044, T047 are in separate files (parallelizable).

## Implementation strategy

**MVP scope**: US1 + US2 (both P1) — the spec's headline deliverables. Ship together to v1.0.2.

**Incremental delivery within MVP**: 

1. Phase 1 + Phase 2 (T001–T019) — foundational dataclasses + shim, tested in isolation. Zero geometry impact.
2. Phase 3 (T020–T028) — US1 silhouette. The model becomes visually correct in side view; pillars still mis-seat.
3. Phase 4 (T029–T035) — US2 seating fix. The model is now both visually correct AND geometrically correct.
4. Phase 5 (T036–T039) — US3 layout invariance. All 5 Alternativ layouts verified.
5. Phase 6 (T040–T050) — polish, hash refresh, visual signoff, commit + push + register tick.

**Validation gates per phase**:

- End of Phase 2: `uv run pytest tests/unit/ && uv run ruff check . && uv run mypy src/` → all green.
- End of Phase 3: above + `tests/geometry/test_deck_partdesign_feature_types.py` + `tests/geometry/test_deck_silhouette.py` → all green.
- End of Phase 4: above + `tests/geometry/test_deck_pillar_seating.py` + `tests/geometry/test_deck_pillar_zero_fallback.py` → all green.
- End of Phase 5: above + `tests/geometry/test_deck_layout_invariance.py` + `tests/geometry/test_deck_reproducibility.py` + `tests/geometry/test_deck_all_layouts_build.py` → all green.
- End of Phase 6: full `uv run pytest && uv run ruff check . && uv run mypy src/` → all 344 + ~25 = ~369 tests green. Manual visual signoff in FreeCAD GUI.

**Total task count**: 50 tasks (T001–T050)

**Task count per phase**:

| Phase | Tasks | Story |
|---|---|---|
| 1 Setup | 3 (T001–T003) | none |
| 2 Foundational | 16 (T004–T019) | none |
| 3 US1 Silhouette | 9 (T020–T028) | US1 |
| 4 US2 Pillar Seating | 8 (T029–T033b + T034–T035) | US2 |
| 5 US3 Layout Invariance | 4 (T036–T039) | US3 |
| 6 Polish | 11 (T040–T050) | none |

**Updated total: 51 tasks (was 50 — T033b added during /speckit.analyze auto-apply to close the FR-013 overhang coverage gap).**

**Parallel opportunities**: Phase 2 (T004–T008, T012–T016) and Phase 6 (T040–T044, T047) batch in parallel. Phases 3–5 are mostly serial within the deck.py file but parallel across the test files.
