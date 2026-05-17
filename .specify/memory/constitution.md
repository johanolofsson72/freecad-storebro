<!--
  Sync Impact Report
  Version change: 0.0.0 → 1.0.0 (initial ratification)
  Added principles:
    - I. Parametric Everything
    - II. Reproducibility (NON-NEGOTIABLE)
    - III. FreeCAD-Idiomatic
    - IV. Reference Fidelity
    - V. Test-Gated Releases
    - VI. Public OSS by Default
    - VII. FreeCAD Version Discipline
  Added sections:
    - Technology Stack
    - Distribution & Release Strategy
    - Development Workflow
    - Governance
  Templates requiring updates:
    - .specify/templates/plan-template.md — ✅ no changes needed (generic)
    - .specify/templates/spec-template.md — ✅ no changes needed (generic)
    - .specify/templates/tasks-template.md — ✅ no changes needed (generic)
  Follow-up TODOs: none
-->

# freecad-storebro Constitution

## Core Principles

### I. Parametric Everything

All geometry MUST be derived from named parameters with defaults — no hard-coded
dimensions, no magic numbers in function bodies. If a value appears in code, it
MUST either be a named argument with a default OR a declared constant exported
from the module's parameter namespace. A `2.34` floating in a hull function is
a constitution violation and a PR blocker. Reviewers MUST reject any geometry
function that cannot be re-driven by changing only its inputs.

### II. Reproducibility (NON-NEGOTIABLE)

Given identical input parameters, the library MUST produce byte-identical output
(`.FCStd`, `.step`, `.stl`). No timestamps in output files. No nondeterministic
ordering of topology elements. No environment-dependent paths embedded in
artifacts. Geometric assertions in tests are evaluated against tolerances; output
file bytes are evaluated against checksums. A run that produces a different
hash for the same inputs is a P0 bug.

### III. FreeCAD-Idiomatic

The library MUST use FreeCAD's native B-rep abstractions (`Part`, `Sketch`,
`Body`, `PartDesign`) for all geometry construction. Bypassing into raw mesh
manipulation (`Mesh.Mesh`, vertex-by-vertex generation) is FORBIDDEN except in
explicitly named mesh-export adapters. Generated documents MUST remain editable
in the FreeCAD GUI after generation — every solid, sketch, and feature node
keeps its parametric history intact.

### IV. Reference Fidelity

The default parameter set MUST produce hull and interior geometry that matches
the historical Storebro proportions (sourced from `docs/references/`) within a
declared tolerance (target: ±1% on LOA, beam, draft, freeboard). The five
canonical interior layouts (Alternativ1–5) MUST be reproducible from shipped
fixture data. New layouts MAY be added via user code; they MUST NOT replace the
canonical defaults.

### V. Test-Gated Releases

Every PR MUST pass: `pytest` (incl. geometry property tests for volume,
bounding box, topology counts), `ruff` (lint + format), and `mypy --strict`
(static typing). These are enforced via GitHub Actions branch protection — a
red CI is mechanically un-mergeable. In addition, every PR that touches public
geometry functions MUST include a manual visual verification note in the PR
description: the author opened the generated `.FCStd` in the FreeCAD GUI and
the geometry looks correct.

### VI. Public OSS by Default

The repository is MIT-licensed. All design discussions happen in public issues
or PRs — no private decisions on shared code. Public API surface (anything not
prefixed with `_`) is governed by semantic versioning: breaking changes require
a MAJOR bump and a documented migration path. Internal helpers (`_` prefix) MAY
change freely.

### VII. FreeCAD Version Discipline

The library MUST declare its supported FreeCAD version range in `pyproject.toml`
metadata and in `README.md`. CI MUST test against every supported FreeCAD
version. When FreeCAD's API breaks (it does — see 1.0 → 1.1 workbench
breakages), the library MUST either: (a) add a compatibility shim and bump
PATCH, or (b) drop the old version, document the drop in `CHANGELOG.md`, and
bump MINOR. Silent breakage is FORBIDDEN.

## Technology Stack

- **Language**: Python 3.11+ (matches FreeCAD 1.1's bundled Python)
- **Packaging**: `uv` for dependency management, `hatchling` as PEP 517 build backend
- **Source layout**: `src/storebro/` (src-layout, not flat)
- **Public API**: `storebro` package; distributed as `freecad-storebro` on PyPI
- **Geometry runtime**: FreeCAD 1.1+ (Python API)
- **Testing**: `pytest` with geometry property assertions; FreeCAD integration tests in a separate marker
- **Lint + format**: `ruff` (replaces black/isort/flake8)
- **Static typing**: `mypy --strict`
- **Repository**: https://github.com/johanolofsson72/freecad-storebro
- **License**: MIT

## Module Layout (flat-module-per-body-part)

```
src/storebro/
  hull.py        # parametric hull (LOA, beam, draft, deadrise, sheer, transom)
  deck.py        # deck plate, cabin trunk, windshield, hardtop, railings
  interior.py    # cabins, galley, heads, salon; loads canonical Alternativ1-5
  export.py      # STEP / STL / BREP / .FCStd writers
  cli.py         # `storebro build --layout 3 --out boat.FCStd` entry point
  fixtures/      # canonical parameter sets for Alternativ1-5
docs/
  references/    # original Storebro cutaway drawings (Alternativ1-5.JPG)
tests/
  unit/          # pure-Python tests, no FreeCAD runtime
  geometry/      # FreeCAD integration tests (pytest marker: requires_freecad)
```

Every module exposes pure functions that take parameters and return FreeCAD
objects. Top-level composition lives in `storebro/__init__.py` or `cli.py` —
never inside a body-part module.

## Distribution & Release Strategy

- PyPI package name: `freecad-storebro`. Import name: `storebro`.
- Semantic versioning. Initial release: `v0.1.0` (hull-only alpha permitted).
  v1.0.0 requires all four v1.0 modules (hull + deck + interior + export/CLI)
  to be usable end-to-end.
- Tags trigger PyPI publish via GitHub Actions (manual approval gate on the
  first release to lock in the PyPI project ownership).
- `CHANGELOG.md` follows keep-a-changelog. Entries are drafted from
  Conventional Commits via the local-LLM changelog hook; the maintainer edits
  before tagging.

## Development Workflow

- Features specified via speckit: `spec.md`, `plan.md`, `tasks.md`.
- Branch naming: `NNN-feature-name` (zero-padded sequence, kebab-case
  description). Single long-lived `main` branch.
- Commit messages: Conventional Commits in English (`feat:`, `fix:`,
  `refactor:`, `test:`, `docs:`, `chore:`).
- All work via PR — including the maintainer's own work. Direct push to `main`
  is reserved for emergency hotfixes only and MUST be documented after the fact.
- All implementations verified with `uv run pytest`, `uv run ruff check .`,
  `uv run mypy src/`.
- Geometry changes additionally verified visually in the FreeCAD GUI (mandatory
  PR description line: "Visually verified in FreeCAD: <version> on <OS>").
- CI matrix: Ubuntu + macOS × Python 3.11 + 3.12 = 4 jobs per PR.

## Governance

This constitution governs all feature development in the freecad-storebro
project. Amendments require:

1. Description of the change and rationale (issue or PR body).
2. Update to this file with version increment.
3. Review of dependent templates and `CLAUDE.md` for consistency.

Versioning follows semantic versioning:
- MAJOR: principle removal or incompatible redefinition.
- MINOR: new principle or material expansion.
- PATCH: clarification or wording fix.

All implementation plans MUST include a Constitution Check section
verifying compliance with these principles.

**Version**: 1.0.0 | **Ratified**: 2026-05-17 | **Last Amended**: 2026-05-17
