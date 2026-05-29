# Tasks: Interior Detail — Alternativ3, 4 & 5

**Input**: Design documents from `specs/013-interior-detail-alternativ3-5/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/python-api.md

**Tests**: REQUIRED — constitution V + spec.md Success Criteria. Per-layout functional coverage; the validation surface is unchanged from spec 012 (no new dataclasses), so destructive coverage is inherited.

> **Verification status (2026-05-29):** FreeCAD is **not installed on the implementation host**, so the `requires_freecad` geometry tier + GUI signoff are **WRITTEN but PENDING execution on a FreeCAD 1.1+ host**. Spec 013 adds NO new geometry construction (one-constant gate widening reusing spec 012's builders), so its incremental risk is minimal. Verified locally: unit tests, `ruff check src/ tests/`, `mypy --strict src/`. Fourth consecutive spec with an unverified geometry tier — run `pytest -m requires_freecad` for specs 010–013 before tagging.

## Format: `[ID] [P?] [Story] Description`

- **[Story]**: US1 (Alt3/4), US2 (Alt5 no-galley)

---

## Phase 1: Setup

- [x] T001 Bump version: `version = "1.0.7"` in `pyproject.toml`, `__version__ = "1.0.7"` in `src/storebro/__init__.py`, and update `tests/unit/test_version_consistency.py` to `1.0.7`.

## Phase 2: Implementation (the one-constant change)

- [x] T002 In `src/storebro/interior.py`, widen `_FURNISHED_LAYOUTS` to all five canonical names (reuse `_CANONICAL_LAYOUT_NAMES` so the two cannot drift: `_FURNISHED_LAYOUTS = _CANONICAL_LAYOUT_NAMES`). Confirm the per-type dispatch already skips absent types (Alt5 no galley) — no other code change.

## Phase 3: User Story 1 — Alt3 & Alt4 furnished (P1) 🎯 MVP

- [x] T003 [P] [US1] Geometry test `tests/geometry/test_interior_alt3_furnished.py`: Alt3 → all 4 compartments furnished; each furniture piece within its envelope; galley counter `Solids == 1`.
- [x] T004 [P] [US1] Geometry test `tests/geometry/test_interior_alt4_furnished.py`: Alt4 → all 4 furnished; the smaller galley counter + recesses fit and stay a single solid.

## Phase 4: User Story 2 — Alt5 no-galley (P2)

- [x] T005 [P] [US2] Geometry test `tests/geometry/test_interior_alt5_no_galley.py`: Alt5 → forward_cabin/head/salon furnished, no galley furniture, no error; every present compartment has a bulkhead.

## Phase 5: Cross-cutting + gate repurpose

- [x] T006 Update `tests/geometry/test_interior_gate.py` (spec 012): flip the assertion — all five canonical layouts are now furnished; add a case confirming a custom (non-canonical) YAML layout stays boxy (`is_furnished == False`).
- [x] T007 [P] Geometry test `tests/geometry/test_interior_alt345_determinism.py`: two builds of each of Alt3/4/5 with identical params → identical compartment volumes (SC-004).
- [x] T008 [P] Geometry test `tests/geometry/test_interior_alt345_default_fit.py`: default `build_interior` for Alt3/4/5 raises no envelope-overflow error (SC-001/SC-002, FR-003).
- [x] T009 Run the full gate: `uv run pytest`, `uv run ruff check src/ tests/`, `uv run mypy src/`. Fix failures. Then `graphify update .`.

---

## Dependencies & execution order

- Phase 1 → 2 (the gate change) → 3/4/5 (tests, parallelizable). T006 must update the spec 012 gate test to match the new behavior.

## MVP scope

US1 (Alt3/Alt4 furnished) is the bulk; US2 (Alt5 no-galley) is the edge case.

## Implementation strategy

The production change is a single constant. The work is verifying the existing builders generalize to the three new layouts (per-layout tests) and repurposing the spec 012 gate test.
