# Tasks: Deck Hardware Detailing

**Feature**: 022 | **Track**: light | **Spec**: [spec.md](./spec.md)

## Phase 1: Setup
- [x] T001 Baseline: `uv run pytest -m "not requires_freecad"` + ruff + mypy green before changes.

## Phase 2: Render roles (US1, US5)
- [x] T002 [US1/US5] `render.py`: add `("Deck_RubrailChromeInsert", "metal")` BEFORE `("Deck_Rubrail", "trim")` and `("Deck_AnchorLockerLid", "trim")` BEFORE `("Deck_AnchorLocker", "superstructure")` in `_ROLE_RULES`. (Weld beads under `Deck_BowPulpit*` already → metal.)

## Phase 3: Parameter dataclasses + validation (all US)
- [x] T003 [US1] `RubrailParameters`: add `outboard_fillet=12.0`, `chamfer_width=12.0`, `chrome_insert=True`, `insert_height=18.0`, `insert_thickness=8.0` + `__post_init__` validation per data-model.
- [x] T004 [US2] `BowPulpitParameters`: add `bend_radius=40.0`, `weld_beads=True`, `weld_bead_radius=18.0` + validation.
- [x] T005 [US3] `LifelineParameters`: add `sag_depth=25.0` + validation (`>= 0`).
- [x] T006 [US4] `CleatParameters`: add `base_taper=0.7`, `horn_rise=32.0` + validation.
- [x] T007 [US5] `AnchorLockerParameters`: add `cavity_depth=90.0`, `cavity_inset=40.0`, `lid=True`, `lid_thickness=20.0` + validation (`cavity_depth < height`, `cavity_inset < min(length,width)/2`).

## Phase 4: Shared helpers
- [x] T008 `deck.py`: add `_pd_additive_pipe(body, name, path_pts_xz_or_xyz, profile_circle_spec, added)` factoring the spec 020 swept-rail pattern (path sketch Spine + profile sketch Profile + `Solids==1` gate), and `_pd_revolve_torus(body, name, center, axis, major_r, minor_r, added)` for weld beads. Reuse where they cut duplication; inline if a builder's geometry is too specific.

## Phase 5: Builder refinements (US1–US5)
- [x] T009 [US1] `_build_rubrail`: replace the rectangular section with a rounded arc section (outboard_fillet); manifold-or-fallback to a chamfered straight section; emit a separate `Deck_RubrailChromeInsert_{side}` AdditiveLoft strip when `chrome_insert`. Set `Rubrail.has_chrome_insert`.
- [x] T010 [US2] `_build_bow_pulpit`: build the bent tube via `_pd_additive_pipe` along an arc-filleted path (bend_radius); add a `_pd_revolve_torus` weld bead at each joint when `weld_beads`; manifold-or-fallback to the existing straight `_pd_circle_pad` cylinders. Preserve zero-stanchion empty body.
- [x] T011 [US3] `_build_lifelines`: replace the straight `_pd_circle_pad` tube with a catenary `AdditivePipe` (`a=span²/8·sag`, sampled ≤12 pts) when `sag_depth>0`; manifold-or-fallback to the straight tube; `sag_depth==0` reproduces spec 010 exactly.
- [x] T012 [US4] `_build_cleats`: replace the box base + straight horn with a tapered `Ruled=True` AdditiveLoft base + curved `AdditivePipe` horns whose neck-posts overlap the base (fuse → single solid). Preserve cleat count + zero-count empty compound.
- [x] T013 [US5] `_build_anchor_locker`: cut a blind `PartDesign::Pocket` cavity (cavity_depth/cavity_inset, leaving a floor) into the locker; emit a separate `Deck_AnchorLockerLid` body when `lid and cavity_depth>0`; `cavity_depth==0` reproduces the spec 010 solid box. Set `AnchorLocker.has_cavity`.

## Phase 6: Unit tests (no FreeCAD)
- [x] T014 [P] [US1] Unit: `RubrailParameters` defaults + each validation rejection (fillet/chamfer/insert bounds).
- [x] T015 [P] [US2] Unit: `BowPulpitParameters` defaults + validation (bend_radius>=0, weld_bead_radius>0).
- [x] T016 [P] [US3] Unit: `LifelineParameters` defaults + `sag_depth>=0` validation.
- [x] T017 [P] [US4] Unit: `CleatParameters` defaults + `base_taper∈(0,1]`, `horn_rise>0` validation.
- [x] T018 [P] [US5] Unit: `AnchorLockerParameters` defaults + `cavity_depth<height`, `cavity_inset` validation.
- [x] T019 [P] Unit: `render.role_for_label("Deck_RubrailChromeInsert_Port")=="metal"`, `("Deck_AnchorLockerLid")=="trim"`, and `("Deck_Rubrail")` still `"trim"`, `("Deck_AnchorLocker")` still `"superstructure"` (ordering regression).

## Phase 7: Geometry tests (requires_freecad)
- [x] T020 [US1] Geometry: rubrail teak side bodies + chrome insert each `Solids==1 && isValid()`; insert omitted when `chrome_insert=False`.
- [x] T021 [US2] Geometry: bow pulpit `Solids==1 && isValid()` with bends; weld-bead bodies present; zero-stanchion empty; forced sweep failure → straight fallback still valid.
- [x] T022 [US3] Geometry: lifeline `Solids==1 && isValid()`; mid-span Z below ends by ≈sag_depth when `sag_depth>0`; straight when `0`; forced failure → fallback valid.
- [x] T023 [US4] Geometry: each cleat `Solids==1 && isValid()`; top footprint < base footprint (taper); total cleat count == spec 010 count; zero-count empty compound.
- [x] T024 [US5] Geometry: locker `Solids==1 && isValid()` with a top cavity; separate lid body present; `cavity_depth=0` → solid box, no lid.
- [x] T025 Geometry (NOBOOL, FR-007): hull + deck-plate `Shape.Volume` and vertex count identical with vs without `parameters_hardware` (build both, compare).
- [x] T026 Geometry (STL, SC-003): export the full deck to STL; assert watertight (no naked edges) on the refined hardware bodies.

## Phase 8: Polish
- [x] T027 Version 1.7.0 -> 1.8.0 (`__init__.py`, `pyproject.toml`, `test_version_consistency`).
- [x] T028 Verify: full unit + ruff + mypy clean; run the geometry tier on FreeCAD 1.1.1 (bundled PYTHONPATH); produce a signoff `.FCStd`. Run generated docs/commit text through `humanizer`. **Back-compat (FR-011/SC-004) proof**: the pre-existing spec 010 hardware unit + geometry tests build with the new defaults and still pass unchanged — no public type/field/function removed; assert the existing `build_deck(...)`-with-default-hardware path is unbroken.

## Notes
- Light track: single synchronous build, no state machine → **/tla skipped** (triviality gate, per specs 010/012/013/014/016/019/020 precedent).
- All four "next-tier" refinements (rounded fillet, weld beads, true catenary, lid) were promoted from deferred to in-scope during elicitation.
- Manifold-or-fallback gates (T010, T011, and T009's chamfer fallback) mirror the spec 020 swept-rail `swept_ok = ... len(sh.Solids)==1` pattern.
