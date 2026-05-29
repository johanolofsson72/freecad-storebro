# Tasks: Basic Deck Hardware

**Input**: Design documents from `specs/010-deck-hardware-basic/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/python-api.md

**Tests**: REQUIRED — constitution V (test-gated releases) + spec.md Success Criteria. Functional coverage (≥1 test per implemented function) + destructive validation tests across the 6 attack categories.

> **Verification status (2026-05-29):** FreeCAD is **not installed on the implementation host**, so the `requires_freecad` geometry tier (T013–T015, T020, T025–T030, T034) and the FreeCAD GUI visual signoff are **WRITTEN but PENDING execution on a FreeCAD 1.1+ host** (per CLAUDE.md's missing-FreeCAD fallback). Verified here: 475 unit tests pass (`-m "not requires_freecad"`), `ruff check src/ tests/` clean, `mypy --strict src/` clean. The geometry run + visual eyeball against `docs/references/Alternativ3.JPG` MUST complete before tagging v1.0.4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different file, no dependency on an incomplete task)
- **[Story]**: US1 (rubrail), US2 (bow furniture), US3 (lifelines + cleats)
- All paths relative to repo root.

---

## Phase 1: Setup

- [x] T001 Bump version: set `version = "1.0.4"` in `pyproject.toml` and `__version__ = "1.0.4"` in `src/storebro/__init__.py` (corrects stale `1.0.2`) — FR-019.
- [x] T002 Add a version-consistency test in `tests/unit/test_version_consistency.py` asserting `storebro.__version__` equals the `pyproject.toml` version string.

## Phase 2: Foundational (BLOCKING — all stories depend on these)

- [x] T003 In `src/storebro/deck.py`, add the five frozen parameter dataclasses with `__post_init__` validation per data-model §1.1–1.5: `RubrailParameters`, `BowPulpitParameters`, `LifelineParameters`, `AnchorLockerParameters`, `CleatParameters`. Reuse the existing `DeckParameterError` and the per-field validation idiom from `CabinTrunkParameters`.
- [x] T004 In `src/storebro/deck.py`, add the `DeckHardwareParameters` composite (data-model §1.6) with `field(default_factory=...)` for all five sub-dataclasses. No composite-level cross-field invariants.
- [x] T005 In `src/storebro/deck.py`, add the five frozen wrapper dataclasses per data-model §2: `Rubrail`, `BowPulpit`, `Lifelines`, `AnchorLocker`, `Cleats` (meters at the wrapper boundary).
- [x] T006 In `src/storebro/deck.py`, extend the `Deck` aggregate (data-model §3) with the five new wrapper fields + `parameters_hardware`, appended after the existing six sub-bodies.
- [x] T007 Update `deck.__all__` and `src/storebro/__init__.py` (imports + `__all__`, alphabetical) to export the six new public names (contracts/python-api.md). Verify no new cross-module import is introduced (FR-020).
- [x] T008 [P] Unit tests for each parameter dataclass validation branch: `tests/unit/test_rubrail_parameters.py`, `test_bow_pulpit_parameters.py`, `test_lifeline_parameters.py`, `test_anchor_locker_parameters.py`, `test_cleat_parameters.py` (mirror `tests/unit/test_pillar_parameters.py`). Cover every `__post_init__` branch incl. `rubrail_forward_x<>aft_x`, `lifeline_height_fraction` bounds (0, 1], and all per-field positivity/non-negativity branches.
- [x] T009 [P] Unit test `tests/unit/test_deck_hardware_parameters.py` for the composite defaults + default_factory independence (mirrors `test_deck_superstructure_parameters.py`).

## Phase 3: User Story 1 — Rubrail along the sheer (P1) 🎯 MVP

**Goal**: A wooden rubrail follows the actual sampled sheer on both sides by default.

**Independent test**: `build_deck(build_hull())` → `deck.rubrail` body spans most of LOA, sits at sheer Z within tolerance on both sides, symmetric.

- [x] T010 [US1] In `src/storebro/deck.py`, implement `_build_rubrail(hull, deck_plate, target_doc, added, *, hardware)` — per-side `PartDesign::Body` with `AdditiveLoft` (Ruled=True) between rectangular cross-section sketches on YZ-parallel datums at the sampled sheer stations (research R1), wrapped in a `Part::Compound` named `Deck_Rubrail`. Seat Z via `_resolve_deck_top_z_at` / `_sample_hull_sheer`. Honor zero-extent fallback (FR-016).
- [x] T011 [US1] Cross-deck validation in `build_deck`: reject `rubrail.aft_x > deck_plate aft edge` with `DeckParameterError("rubrail_aft_x<>deck_aft_edge", ...)` (data-model §6).
- [x] T012 [US1] Wire `_build_rubrail` into `build_deck` after `_build_railings` resolution but per the build sequence (plan §Build Sequence step 2); append to `added`; resolve `parameters_hardware or DeckHardwareParameters()`; populate `Deck.rubrail`.
- [x] T013 [P] [US1] Geometry test `tests/geometry/test_deck_hardware_rubrail_sheer.py`: rubrail top-Z at each station within `sheer_seating_tolerance_mm` of sampled sheer; spans ≥ 80% LOA.
- [x] T014 [P] [US1] Geometry test `tests/geometry/test_deck_hardware_symmetric.py`: port/starboard rubrail bodies mirror across Y=0 (extend later for cleats in US3).
- [x] T015 [P] [US1] Geometry test `tests/geometry/test_deck_hardware_partdesign_feature_types.py`: rubrail bodies are PartDesign with AdditiveLoft features (no raw mesh) — FR-002.

## Phase 4: User Story 2 — Bow furniture: pulpit + anchor locker (P2)

**Goal**: Tubular bow pulpit + raised anchor-locker hatch on the foredeck.

**Independent test**: default deck has a tubular `bow_pulpit` forward of the cabin trunk at guard-rail height, and an `anchor_locker` box within the deck footprint forward of the cabin trunk.

- [x] T016 [US2] In `src/storebro/deck.py`, implement `_build_bow_pulpit(hull, deck_plate, target_doc, added, *, hardware)` — tubular stanchion Pads + connecting top-rail Pads (research R2), one `PartDesign::Body` `Deck_BowPulpit`, symmetric about centerline, bases seated via `_resolve_deck_top_z_at`. Zero-stanchion fallback (FR-016).
- [x] T017 [US2] In `src/storebro/deck.py`, implement `_build_anchor_locker(deck_plate, cabin_trunk, target_doc, added, *, hardware)` — raised box `PartDesign::Body` `Deck_AnchorLocker` (sketch + Pad), seated on foredeck top Z (research R4).
- [x] T018 [US2] Cross-deck validation in `build_deck`: reject anchor locker overlapping cabin trunk (`anchor_locker_center_x<>cabin_trunk`) and past deck forward edge (`anchor_locker_center_x<>deck_forward_edge`) per data-model §6.
- [x] T019 [US2] Wire `_build_bow_pulpit` + `_build_anchor_locker` into `build_deck` (plan §Build Sequence steps 3–4); append to `added`; populate `Deck.bow_pulpit`, `Deck.anchor_locker`.
- [x] T020 [P] [US2] Geometry test `tests/geometry/test_deck_hardware_anchor_locker_placement.py`: locker BoundBox within deck footprint and `XMax <= cabin_trunk.forward_x`.
- [x] T021 [P] [US2] Unit test additions in `tests/unit/test_deck_destructive_validation.py`: anchor-locker-overlap and rubrail-past-edge rejection raise `DeckParameterError` before any FreeCAD call.

## Phase 5: User Story 3 — Lifelines + cleats (P3)

**Goal**: Lifelines strung between railing posts; cleats along the sheer.

**Independent test**: default deck has lifeline tube(s) between the 6 railing posts/side and 4 cleats (2 fwd, 2 aft) seated on the deck top; zero-post railing → no lifelines, no error.

- [x] T022 [US3] In `src/storebro/deck.py`, implement `_build_cleats(hull, deck_plate, target_doc, added, *, hardware)` — per (station, side) `PartDesign::Body` (base pad + horn bar, research R5), wrapped in `Part::Compound` `Deck_Cleats`, seated via `_resolve_deck_top_z_at`. Default count math per data-model §1.5. Zero-count fallback (FR-016).
- [x] T023 [US3] In `src/storebro/deck.py`, implement `_build_lifelines(deck_plate, target_doc, added, *, hardware, railings_params)` — one horizontal tube Pad per side per line between the railing posts (research R3), `Part::Compound` `Deck_Lifelines`. Skip entirely when resolved railing `post_count_per_side == 0` (FR-017) → empty compound.
- [x] T024 [US3] Wire `_build_cleats` + `_build_lifelines` into `build_deck` (plan §Build Sequence steps 5–6, lifelines LAST after railings); pass the resolved railing params; append to `added`; populate `Deck.cleats`, `Deck.lifelines`.
- [x] T025 [P] [US3] Geometry test `tests/geometry/test_deck_hardware_cleat_seating.py`: each cleat BoundBox ZMin >= deck-top-Z − 1.0 mm; total cleat count == 4 default; port/starboard symmetric.
- [x] T026 [P] [US3] Geometry test `tests/geometry/test_deck_hardware_lifeline_no_posts.py`: railing with `post_count_per_side=0` → `lifelines` empty compound, no exception (FR-017).

## Phase 6: Cross-cutting + destructive + signoff

- [x] T027 Geometry test `tests/geometry/test_deck_hardware_default_call.py`: default `build_deck(build_hull())` returns all five hardware wrappers non-null; no error; document contains the new bodies (SC-001).
- [x] T028 Geometry test `tests/geometry/test_deck_hardware_determinism.py`: two builds with identical inputs → identical shape digests / byte-identical export for the hardware bodies (SC-004, constitution II).
- [x] T029 Geometry test `tests/geometry/test_deck_hardware_rollback.py`: inject a FreeCAD failure during hardware build → document restored to pre-call state, all added bodies removed (FR-013, SC-006). Mirror `test_deck_construction_rollback.py`.
- [x] T030 Geometry test `tests/geometry/test_deck_hardware_zero_counts.py`: zero cleats / zero lifelines / zero pulpit stanchions build without raising (FR-016).
- [x] T031 [P] Destructive tests (6 attack categories) in `tests/unit/test_deck_destructive_validation.py`: invalid input (NaN, negative, extreme length, zero), boundary (forward_x==aft_x, height_fraction==0 and ==1.0, center_x at exact deck edge), wrong/again construction (double build on same doc), skip-steps (hardware params without superstructure), type misuse (int where float). ≥8 scenarios.
- [x] T032 Update existing body-count assertions: `tests/geometry/test_deck_default_call.py` and `test_deck_default_labels.py` now expect the additional hardware bodies/labels (back-compat behavior change per spec Assumptions).
- [x] T033 [P] Update `tests/unit/test_deck_public_docstrings.py` + `tests/unit/test_deck_back_compat.py`: every new public dataclass/function has a one-line docstring with an example; legacy `build_deck(hull)` still returns a valid `Deck`.
- [x] T034 Geometry visual-signoff test `tests/geometry/test_deck_hardware_visual_signoff.py`: produce `tests/fixtures/signoff/storebro_v1_0_4_signoff.FCStd`, record its SHA-256, assert reproducible build (mirrors `test_deck_visual_signoff.py`).
- [x] T035 Run the full gate: `uv run pytest`, `uv run ruff check .`, `uv run mypy src/`. Fix any failures. Then `graphify update .` to refresh the knowledge graph.

---

## Dependencies & execution order

- **Phase 1 → Phase 2 → Phase 3** (MVP) → Phase 4 → Phase 5 → Phase 6.
- Phase 2 (T003–T009) BLOCKS all user stories (dataclasses + Deck aggregate + exports must exist first).
- US1/US2/US3 builder functions are independent of each other but all wire into the single `build_deck` orchestrator (T012, T019, T024 touch the same function → sequential, not [P]).
- Test tasks marked [P] touch distinct new files → parallelizable within their phase.

## Parallel example (Phase 2)

```
T008 (5 unit test files) ∥ T009 (composite unit test)   # after T003–T007 land
```

## MVP scope

US1 (rubrail) alone is a shippable increment — it is the single highest-value visual tell and is independently testable. US2 and US3 layer on incrementally.

## Implementation strategy

Incremental: land Phase 1+2, then US1 end-to-end (impl + tests green), then US2, then US3, then the cross-cutting/destructive/signoff phase. Keep `build_deck` rollback list (`added`) inclusive of every new body so partial failure rolls back the whole deck.
