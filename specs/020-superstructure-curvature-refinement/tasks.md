# Tasks: Superstructure Curvature Refinement

**Feature**: 020 | **Track**: full | **Spec**: [spec.md](./spec.md)

## Phase 1: Setup
- [x] T001 Baseline: unit + ruff + mypy.

## Phase 2: Hardtop smooth curl (US1)
- [x] T002 [US1] `HardtopParameters` += `curl_sections: int = 7` (validated >= 2).
- [x] T003 [US1] `_build_hardtop`: replace the 3-section loft with a dense Ruled=True loft whose forward `curl_sections` sketches trace a cosine drop over `leading_edge_curl_length`; keep aft taper; Ruled=True.

## Phase 3: Swept perimeter top-rail (US2)
- [x] T004 [US2] `_build_railings`: build the top-rail as a `makePipeShell` sweep of a circular profile along the closed perimeter wire; on sweep failure fall back to the spec 010 straight per-side cylinder (FR-005). Posts unchanged.

## Phase 4: Crowned windshield (US3)
- [~] T005 [US3] (DEFERRED — windshield already Ruled=False-smooth; transverse crown endangers spec 011 frame/pane → follow-on spec) `WindshieldParameters` += `crown_height: float = 60.0`, `crown_sections: int = 5` (validated); `_build_windshield`: arch the top via dense Ruled=True sections; preserve the spec 011 frame/pane.

## Phase 5: Tests
- [x] T006 [P] [US1] Geometry: hardtop `Solids==1`+valid, ZMax <= topside (0 overshoot), faces > 3-section baseline; STL ok.
- [x] T007 [P] [US2] Geometry: swept top-rail valid solid; railing STL ok; zero-post graceful.
- [~] T008 [P] [US3] (DEFERRED with T005) Geometry: windshield `Solids==1`+valid + crowned (mid top Z > corner top Z); frame + pane still build.
- [x] T009 [US1] Fix existing hardtop/windshield/railing geometry tests that assert the old faceted shapes; preserve their manifold assertions.

## Phase 6: Polish
- [x] T010 Version 1.5.0 -> 1.6.0 (init, pyproject, version test).
- [x] T011 Full verify on FreeCAD 1.1.1 + ruff + mypy.

## Notes
- All three spike-proven (/tmp/spike_020.py). Full track; /tla skipped (synchronous geometry, no state machine).
- Swept rail has a manifold-or-fallback gate (spec 018 discipline).
