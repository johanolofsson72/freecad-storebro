# Feature Specification: Parametric Robustness — Non-Finite Rejection

**Feature Branch**: `029-parametric-robustness`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Module-wide hardening: reject non-finite (NaN/inf) values in every geometry/dimension field of every parameter dataclass (hull/deck/interior/propulsion), matching the existing per-field positivity validation." (Scoped down from the original spec 029 — expression bindings + hard-chine variant moved to spec 031 per the 2026-06-11 register rewrite.)

## Overview

Every geometry parameter in the library is a frozen dataclass that validates itself in `__post_init__` — positivity, angular ranges, cross-field geometric sanity — and raises a module-specific `ParameterError` (`HullParameterError`, `DeckParameterError`, the interior parameter error, `PropulsionParameterError`) on the first violation. But the positivity checks are written as `value <= 0` / `value < 0`, which **silently accept non-finite floats**: `float("inf")` passes `> 0`, and `float("nan")` passes *every* comparison (NaN compares false to everything, so `nan <= 0` is `False` → "valid"). A `nan` or `inf` dimension then flows into the FreeCAD geometry build, producing a corrupt/unbuildable shape or a non-reproducible artifact — violating constitution principle II (reproducibility) and the project's fail-fast principle (invalid parameters must raise `ValueError` with the offending value and the valid range).

The propulsion module already closes this hole: its `_require_positive` / `_require_non_negative` helpers check `math.isfinite(value)` first, and two NACA-ratio fields validate finiteness explicitly. The hull, deck, and interior parameter dataclasses do **not** — they accept `inf`/`nan` and propagate them. This spec extends non-finite rejection to **every geometry/dimension float field of every parameter dataclass**, so the whole library fails fast and identically on a non-finite input, matching the propulsion module's existing guard. This is a pure hardening fix: no new entities, no new state, no new public API, no geometry change for any valid input.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Non-finite dimension is rejected at construction (Priority: P1)

A library consumer (or a buggy upstream computation) constructs a parameter dataclass with a `nan` or `inf` dimension (e.g. `HullParameters(loa=float("inf"))`, `DeckParameters(cabin_trunk_height=float("nan"))`). The library must reject it immediately with the module's `ParameterError`, naming the offending field — never build geometry from it.

**Why this priority**: It is the entire feature and closes a correctness/reproducibility gap (constitution II + fail-fast) that currently lets corrupt geometry through.

**Independent Test**: For each parameter dataclass, construct it with a non-finite value (`nan`, `inf`, `-inf`) in a geometry/dimension field; assert the module's `ParameterError` is raised, naming that field.

**Acceptance Scenarios**:

1. **Given** a parameter dataclass with a geometry/dimension field, **When** it is constructed with `float("nan")` in that field, **Then** the module's `ParameterError` is raised naming that field.
2. **Given** the same, **When** constructed with `float("inf")` (or `-inf`), **Then** the module's `ParameterError` is raised naming that field.
3. **Given** any existing valid parameter set, **When** constructed, **Then** it still succeeds and produces byte-identical geometry to before this change (no behavior change for valid input).

---

### Edge Cases

- **NaN compares false to everything**: a `value <= 0` guard lets `nan` through (`nan <= 0` is `False`). The finite-check MUST be ordered so NaN is rejected — i.e. `not math.isfinite(value)` (or `not isfinite or value <= 0`), not a comparison that NaN sneaks past.
- **`inf` passes positivity**: `inf > 0` is `True`, so a positivity-only guard accepts it. The finite-check closes this.
- **Already-guarded fields**: the propulsion `naca_thickness_ratio` fields and the `_require_positive`/`_require_non_negative` helpers already reject non-finite — those stay as-is (no double-guard, no regression).
- **Non-dimension fields**: integer counts (e.g. `station_count`, `blade_count`, `cushion_count`), enum-like strings, and booleans are not floats and are out of scope; only float geometry/dimension fields get the finite guard.
- **Sentinel values**: fields using a finite sentinel like `-1.0` for "auto" (e.g. porthole `forward_x`) must keep accepting their sentinel — the finite guard rejects `nan`/`inf` but a finite sentinel is finite, so it passes the finite check and is handled by the existing sentinel logic.
- **First-violation semantics**: validation raises on the first offending field (existing behavior); the finite check is part of that same per-field pass, so error messages stay deterministic.

## Clarifications

### Session 2026-06-11

- Q: Does "geometry/dimension float field" include angle fields (deadrise, transom/rake angles) and non-negative offset fields, or only positive lengths? → A: All float fields that feed geometry — positive lengths, radii, ratios, **angles**, and non-negative **offsets**. A non-finite value in any of them corrupts the build, so all are guarded. The only floats excluded are finite "auto" sentinels (e.g. `-1.0`, handled by existing sentinel logic) and non-geometry config constants.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every geometry/dimension **float** field of every parameter dataclass (`hull.py`, `deck.py`, `interior.py`, `propulsion.py`) MUST reject non-finite values (`nan`, `+inf`, `-inf`) at construction, raising that module's `ParameterError` naming the offending field.
- **FR-002**: The finite check MUST be NaN-safe — it MUST reject `nan` even though `nan` passes the existing `<= 0` / `< 0` comparisons (use `math.isfinite`, not a comparison NaN can pass).
- **FR-003**: For any **valid** (finite) parameter set, behavior MUST be unchanged: construction still succeeds and the generated geometry is byte-identical to before this change.
- **FR-004**: The error raised MUST be the module's existing `ParameterError` type, naming the field and (where the existing pattern does) the valid range — consistent with the current positivity/range errors. No new error type.
- **FR-005**: Fields that already reject non-finite (propulsion's `_require_positive` / `_require_non_negative` helpers and the two `naca_thickness_ratio` checks) MUST remain correct and MUST NOT be double-guarded or regressed.
- **FR-006**: Sentinel-based fields (a finite sentinel meaning "auto", e.g. `-1.0`) MUST keep accepting their sentinel; only `nan`/`inf` are newly rejected.
- **FR-007**: Integer count fields, booleans, and enum-like string fields are out of scope (they cannot hold `nan`/`inf`); only float geometry/dimension fields are guarded. "Geometry/dimension float field" includes **angles** and non-negative **offsets**, not just positive lengths (per Clarifications). Finite "auto" sentinels stay accepted.
- **FR-008**: The fix MUST be expressed as validation + tests only — no new entities, no state machine, no public-API change, no `.allium`, no `/tla` (spec-only track).
- **FR-009**: Every guarded dataclass MUST gain a unit test asserting `nan` and `inf` rejection on at least one representative geometry field (alongside the existing positivity tests), so the guard is regression-protected.

### Key Entities

- **Parameter dataclass**: an existing frozen dataclass holding geometry/dimension parameters with a `__post_init__` validator (HullParameters, DeckParameters and its component classes, the interior furniture/compartment parameter classes, the propulsion parameter classes).
- **Finite guard**: the per-field check `math.isfinite(value)` applied before/with the existing positivity/range comparison, raising the module's `ParameterError`. May be factored into a small per-module helper (mirroring propulsion's `_require_positive`/`_require_non_negative`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Constructing any parameter dataclass with `nan`, `+inf`, or `-inf` in a geometry/dimension field raises that module's `ParameterError` naming the field.
- **SC-002**: All existing parameter-validation tests still pass; all existing valid-input geometry tests still pass (no behavior change for valid input).
- **SC-003**: Every guarded dataclass has a unit test covering `nan` + `inf` rejection.
- **SC-004**: `uv run pytest` (unit), `uv run ruff check .`, and `uv run mypy src/` are all clean.
- **SC-005**: A representative geometry build (`storebro build`) produces a byte-identical artifact to the pre-029 build for the same inputs (reproducibility preserved).

## Assumptions

- **Mechanism**: a small per-module finite-rejection helper (mirroring `propulsion._require_positive`) applied to each float geometry/dimension field inside the existing `__post_init__`/`_validate_*` pass, raising the module's existing `ParameterError`. The propulsion module already has this — extend the pattern to hull/deck/interior (and any unguarded propulsion float field).
- **Scope boundary**: only float geometry/dimension fields. Integer counts, enums, booleans, and finite sentinels are not in scope. No public API, no geometry, no expression bindings, no hull variant (those are spec 031).
- **Spec-only track**: hardening fix with no new entities or state transitions → no `.allium`, no `/tla`. The constraint is expressed as per-dataclass unit tests (the existing validation test files gain `nan`/`inf` cases).
- **Reproducibility**: valid inputs are untouched, so all geometry remains byte-identical; no FreeCAD runtime is needed to verify the new guards (they are pure-Python `__post_init__` checks, unit-testable without FreeCAD).
