# Tasks: Propulsion Fidelity (CAD-faithful machinery)

**Feature**: 021-propulsion-fidelity | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

**Scope**: All production code in `src/storebro/propulsion.py` (+ one line in `render.py`, one flag in `cli.py`, version in `__init__.py`/`pyproject.toml`). Tests in `tests/unit/` and `tests/geometry/`.

**Testing note**: This is a geometry library, NOT interactive UI (per `.claude/rules/specs.md` triage → browser tests N/A). The functional-coverage analog is "≥1 geometry test per builder"; the destructive analog is invalid-parameter, boundary, and gate-failure (fallback) scenarios.

---

## Phase 1: Setup — Reproducibility & Manifold Spike (BLOCKING GATE)

**Gates all geometry work. No production builder ships until its construction passes the spike (clarify Q5, FR-008).**

- [ ] T001 Write and run `/tmp/spike_021_repro.py` (FreeCAD, bundled-python `PYTHONPATH`): build each detailed construction — (a) rudder NACA-polyline `Pad`, (b) propeller stacked-foil `AdditiveLoft (Ruled=True)`, (c) shaft coupling-flange + bolt bosses + fairing fused Pads, (d) strut separate body (barrel+arm fused), (e) engine sump/head/stub fused Pads — ≥3× in fresh documents AND once in the two-open-documents scenario (the spec 022 drift mode). Assert per construction: `Shape.Volume` byte-identical across runs, `len(Solids)==1`, `isValid()`, STL export succeeds. Record the per-construction pass/fail + chosen default (on/off) into `research.md` §R2 spike-result table.

**Checkpoint**: Every construction either proven byte-reproducible (default ON) or flagged drifting (default OFF, opt-in). Defaults in T004 follow this result.

---

## Phase 2: Foundational (blocking prerequisites for all stories)

- [ ] T002 [P] Add NACA foil-math helpers to `src/storebro/propulsion.py`: `_naca_symmetric_half_thickness(x_over_c: float, t: float) -> float` (closed-TE 4-digit, coeff `-0.1036`) and `_naca_section_polyline(chord_mm: float, t: float, n_points: int) -> list[tuple[float, float]]` (ordered closed (u,v) loop, upper LE→TE then lower TE→LE). Pure Python, no FreeCAD import.
- [ ] T003 [P] Add module `config` constants (the `_DEFAULT_*` set in data-model.md §config) to `src/storebro/propulsion.py` — single source of truth for every new dimension (constitution I).
- [ ] T004 Add the appended detail fields + `__post_init__` validation to `EngineParameters`, `ShaftParameters`, `PropellerParameters`, `RudderParameters` in `src/storebro/propulsion.py` (defaults from T003 constants; detail master flags ON per clarify Q1, overridden to OFF for any construction T001 flagged drifting). Validation raises `PropulsionParameterError` before any FreeCAD call (data-model.md §Validation).
- [ ] T005 Add the per-body manifold-or-fallback helper `_detail_or_fallback(...)` to `src/storebro/propulsion.py`: validates `len(Solids)==1 ∧ isValid()`; on failure, rebuild the spec 014 placeholder for CORE parts or signal omission for OPTIONAL supports (research.md §R5). Reuses the spec 014 `added`/`_rollback` discipline.
- [ ] T006 [P] [Unit] Write `tests/unit/test_propulsion_foil_math.py`: `_naca_symmetric_half_thickness` is 0 at x=0 and x=1 (closed TE), positive interior, max forward of mid-chord; `_naca_section_polyline` returns a closed non-self-intersecting loop with max thickness in the chord interior; determinism (same inputs → identical list).
- [ ] T007 [P] [Unit] Write `tests/unit/test_propulsion_detail_params.py`: every new field default; each validation rejection (`naca_thickness_ratio` ≤0 / ≥1; `coupling_flange_diameter_mm ≤ diameter_mm`; `2·sump_inset_mm ≥ width_mm`; `root_pitch_deg == tip_pitch_deg` with airfoil on; `strut_arm_width_mm ≤ 0`; non-finite values) raises `PropulsionParameterError`; detail-off construction is accepted.

**Checkpoint**: foil math + parameters + fallback scaffolding exist and are unit-green (no FreeCAD needed). Geometry stories can proceed in parallel.

---

## Phase 3: User Story 1 — Airfoil propeller blades (P1) 🎯 MVP

**Goal**: each blade is a symmetric-NACA foil that twists root→tip; gate-failure falls back to the spec 014 flat blade.
**Independent test**: `tests/geometry/test_propulsion_propeller_foil.py` green — foil mid-span section, non-zero twist, `Solids==1`, STL, determinism.

- [ ] T008 [US1] Replace `_blade_corners`/the flat-rectangle blade loop in `_build_propeller` (`src/storebro/propulsion.py`) with a foil-blade builder: per blade, `AdditiveLoft (Ruled=True)` through `blade_sections` `_naca_section_polyline` sketches, each scaled by chord-taper and rotated by `pitch(f)=lerp(root_pitch,tip_pitch,f)`, fused with the hub cylinder. Polyline sections only (no arcs).
- [ ] T009 [US1] Wrap the foil-blade build in `_detail_or_fallback` (CORE): on non-manifold, rebuild the spec 014 flat blade for that propeller body. Honour `propeller.airfoil_blades` flag.
- [ ] T010 [US1] Extend the `Propeller` wrapper with `airfoil_requested`, `airfoil_applied`, `root_to_tip_twist_deg` (data-model.md); set them in `_build_propeller`.
- [ ] T011 [P] [US1] Write `tests/geometry/test_propulsion_propeller_foil.py`: default build → each propeller `Solids==1`, `isValid()`, STL OK, is a `PartDesign::Body` (FR-013), `blade_count` blades + hub, `airfoil_applied=True`, `root_to_tip_twist_deg != 0`; mid-span chordwise section thickness peaks in the interior (foil); root vs tip chord orientation differs (twist); `airfoil_blades=False` → spec 014 flat blades; a forced-failure case still yields a valid solid (fallback).

**Checkpoint**: propeller is CAD-faithful and independently verifiable — MVP deliverable.

---

## Phase 4: User Story 2 — Detailed diesel engine block (P2)

**Goal**: stepped diesel silhouette (sump + head/valve-cover + manifold stubs) fused into one solid.
**Independent test**: `tests/geometry/test_propulsion_engine_detail.py` green.

- [ ] T012 [US2] Upgrade `_build_engine` (`src/storebro/propulsion.py`): additive Pads fused into the engine body — a narrower sump below the block (inset `sump_inset_mm`, drop `sump_drop_mm`), a head/valve-cover above (`head_height_mm`), `manifold_stub_count` side cylinder stubs (`manifold_stub_diameter_mm`). Honour `engine.detailed`.
- [ ] T013 [US2] Re-check the within-hull-envelope guard against the DETAILED top Z (block top + head height) and detailed bottom Z (sump); keep `within_hull_envelope`/`pierces_hull_shell` correct; sump bottom must stay above the keel. Wrap in `_detail_or_fallback` (CORE → spec 014 box).
- [ ] T014 [US2] Extend the `EngineBlock` wrapper with `detail_requested`, `detail_applied`; set them.
- [ ] T015 [P] [US2] Write `tests/geometry/test_propulsion_engine_detail.py`: detailed engine `Solids==1`, `isValid()`, STL; sump section narrower than block, head raises top Z, `manifold_stub_count` stubs present; `within_hull_envelope` still true; `detailed=False` → spec 014 box; boundary case (`2·sump_inset` near `width`) handled.

---

## Phase 5: User Story 3 — NACA rudder foil (P2)

**Goal**: rudder blade is a symmetric NACA section over the span; gate-failure falls back to the flat plate.
**Independent test**: `tests/geometry/test_propulsion_rudder_foil.py` green.

- [ ] T016 [US3] Replace the flat blade in `_build_rudder` (`src/storebro/propulsion.py`): closed `_naca_section_polyline` sketch (chord along X, thickness along Y) `Pad` over the span, fuse the existing stock. Honour `rudder.naca_foil`. Wrap in `_detail_or_fallback` (CORE → spec 014 plate).
- [ ] T017 [US3] Extend the `Rudder` wrapper with `naca_requested`, `naca_applied`; set them.
- [ ] T018 [P] [US3] Write `tests/geometry/test_propulsion_rudder_foil.py`: rudder `Solids==1`, `isValid()`, STL; chordwise section is a symmetric foil (rounded LE, TE < 30% of max thickness, max thickness forward of mid-chord); `naca_foil=False` → spec 014 plate.

---

## Phase 6: User Story 4 — Coupling flange + strut bearings (P3)

**Goal**: bolted coupling flange fused into the forward shaft end; a separate P-bracket strut body supports the shaft.
**Independent test**: `tests/geometry/test_propulsion_shaft_detail.py` (coupling + strut portions) green.

- [ ] T019 [US4] Add a coupling flange to `_build_shaft` (`src/storebro/propulsion.py`): a coaxial collar disc `Pad` (Ø `coupling_flange_diameter_mm`) + a ring of `coupling_bolt_count` bolt-head boss Pads at the forward (local x≈0) end, fused into the shaft body. Honour `shaft.coupling_flange`; set `Shaft.has_coupling_flange`.
- [ ] T020 [US4] Add the NEW `Strut` wrapper dataclass + `_build_strut` builder (separate `Propulsion_Strut` `PartDesign::Body`): a bearing barrel around the shaft mid-run fused with an arm reaching up to the hull bottom at that station; placement on the shaft axis. Honour `shaft.strut_bearing` + `strut_count`; OPTIONAL → `_detail_or_fallback` omits on failure.
- [ ] T021 [US4] Add `struts: list[Strut] = field(default_factory=list)` to the `Propulsion` aggregate; build + collect struts per train in `build_propulsion`; export `Strut` from `__all__` and `storebro/__init__.py`.
- [ ] T022 [P] [US4] Write the coupling + strut portion of `tests/geometry/test_propulsion_shaft_detail.py`: coupling flange present (Ø > shaft Ø) and shaft stays `Solids==1`; strut is a separate `PartDesign::Body` (FR-013), `Solids==1` valid body whose top Z reaches up toward the hull bottom; `coupling_flange=False`/`strut_bearing=False` → spec 014 shaft + empty `struts`.

---

## Phase 7: User Story 5 — Through-hull shaft-log fairing (P3)

**Goal**: additive faired boss around the shaft-exit station, fused into the shaft; hull never cut.
**Independent test**: `tests/geometry/test_propulsion_shaft_detail.py` (fairing portion) green; hull unchanged.

- [ ] T023 [US5] Add the shaft-log fairing to `_build_shaft` (`src/storebro/propulsion.py`): a faired (stepped/tapered) coaxial boss (Ø ratio `shaft_log_fairing_diameter_ratio`, length `shaft_log_fairing_length_mm`) at the exit station, fused into the shaft (replaces/augments the spec 014 stern-tube boss). Honour `shaft.shaft_log_fairing`; OPTIONAL → omit on failure; set `Shaft.has_shaft_log_fairing`. Hull never booleaned.
- [ ] T024 [P] [US5] Write the fairing portion of `tests/geometry/test_propulsion_shaft_detail.py`: fairing present → shaft `Solids==1`/`isValid()`/STL; `hull.body.Shape.Volume` identical with vs without propulsion and `hull_modified=False`; `shaft_log_fairing=False` → spec 014 shaft.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T025 [P] Add `("Propulsion_Strut", "bronze")` to `render._ROLE_RULES` in `src/storebro/render.py`; thread strut bodies into the `build_propulsion` render-target list.
- [ ] T026 [P] Add optional `--no-propulsion-detail` flag to `src/storebro/cli.py`: builds `PropulsionParameters` with all detail flags off (spec 014 placeholder). Default path stays detailed-on.
- [ ] T027 Bump version 1.10.0 → 1.11.0 in `src/storebro/__init__.py` and `pyproject.toml`; update the version-consistency test.
- [ ] T028 [P] Write `tests/geometry/test_propulsion_detail_determinism.py`: two consecutive default builds → byte-identical `Shape.Volume` for every detailed body (engine, shaft, propeller, rudder, strut) and equal exported-shape digest; full assembly STL export succeeds (SC-002/SC-008). Include a single-screw (`engine_count=1`) detailed build asserting the same detail is applied per-train (FR-014).
- [ ] T029 [P] Write `tests/geometry/test_propulsion_placeholder_equiv.py`: a build with every detail flag off is byte-identical to the spec 014 build (volume + digest per body; `struts == []`) (SC-006).
- [ ] T030 Run the gate: `uv run pytest` (unit) + `PYTHONPATH=… uv run pytest -m requires_freecad` (geometry) + `uv run ruff check .` + `uv run mypy src/`. Fix any failures. Build the signoff `.FCStd` via `storebro build --layout Alternativ3` and record its SHA-256.

---

## Dependencies & Execution Order

- **T001 (spike) blocks everything** — its result sets the T004 defaults.
- **Phase 2 (T002–T007) blocks all stories** — foil math, params, fallback helper.
- **Stories are independent after Phase 2**: US1 (T008–T011), US2 (T012–T015), US3 (T016–T018), US4 (T019–T022), US5 (T023–T024) touch different builders in the same file → run sequentially to avoid edit conflicts, but have no logical inter-dependency. US4 and US5 both touch `_build_shaft` → do US4 then US5 (or one combined edit pass).
- **Phase 8 polish** depends on the stories it references (T025 needs T020's strut; T028/T029 need all builders; T027 last).
- **[P]** marks parallelizable *test-writing* and independent-file tasks (unit tests, render line, CLI flag) — production edits to `propulsion.py` are serialized.

## MVP

**US1 (propeller foil) alone is a shippable increment** — the highest-impact visual win. Phases 1–3 deliver it; Phases 4–7 add the remaining four parts; Phase 8 finalizes.

## Implementation Strategy

Spike-gate first (Phase 1) → foundational math/params/fallback (Phase 2) → propeller MVP (Phase 3) → engine/rudder/coupling+strut/fairing (Phases 4–7) → polish + full verification (Phase 8). One continuous run (continuous-execution rule); the only legitimate stops are spike-driven default flips (recorded, not blocking) and any genuine ambiguity.
