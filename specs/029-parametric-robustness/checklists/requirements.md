# Specification Quality Checklist: Parametric Robustness — Non-Finite Rejection

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-11
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details beyond the necessary mechanism note (kept at the behavior level: reject non-finite, raise the module's ParameterError)
- [x] Focused on user value (fail-fast on corrupt input; constitution II reproducibility)
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified (NaN-compares-false, inf-passes-positivity, sentinels, already-guarded propulsion)
- [x] Scope is clearly bounded (float geometry fields only; expression bindings + hull variant are spec 031)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Spec-only track (hardening; no new entities/state) → no `/allium:elicit`, no `/tla`; the constraint is per-dataclass `nan`/`inf` unit tests.
- The mechanism is already proven in the codebase: `propulsion._require_positive` / `_require_non_negative` check `math.isfinite` first. This spec generalizes that guard to hull/deck/interior.
