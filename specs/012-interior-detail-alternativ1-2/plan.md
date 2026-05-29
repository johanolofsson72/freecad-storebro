# Implementation Plan: Interior Detail — Alternativ1 & 2

**Branch**: `master` (solo, direct-push) | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/012-interior-detail-alternativ1-2/spec.md`

## Summary

Replace the boxy Alternativ1/Alternativ2 compartment placeholders in `interior.py` with type-keyed furniture: `forward_cabin` → berth + cushion(s); `galley` → counter with blind sink + stove recesses; `head` → toilet + sink; `salon` → seating + table; plus a thin bulkhead per compartment. Furniture is built as `Part::Feature` B-rep solids (`Part.makeBox`, matching the interior module's existing spec 004 idiom — NOT PartDesign chains), with galley recesses via boolean `Part.Cut`. Detailed furniture is gated to Alt1/Alt2 (Alt3-5 keep boxy placeholders until spec 013, which reuses the generic helpers). A new optional `FurnitureParameters` composite + `parameters_furniture` kwarg on `build_interior`; furniture on by default for Alt1/Alt2. PATCH bump 1.0.5 → 1.0.6; additive API only.

## Technical Context

**Language/Version**: Python 3.11+ (FreeCAD 1.1 bundled Python)

**Primary Dependencies**: FreeCAD 1.1+ Python API (`Part`, `FreeCAD`); PyYAML (existing, for fixtures); no new third-party deps

**Storage**: YAML fixtures (existing, unchanged) — furniture is parameter-driven, not fixture-driven

**Testing**: pytest — `tests/unit/` (no FreeCAD) + `tests/geometry/` (marker `requires_freecad`)

**Target Platform**: macOS + Ubuntu × Python 3.11/3.12, FreeCAD 1.1.1

**Project Type**: Single-project Python library

**Performance Goals**: human-scale seconds

**Constraints**: byte-identical reproducibility (II); ±1% fidelity (IV); B-rep only, no raw mesh (III); galley counter manifold after cuts (FR-007); `interior.py` keeps its existing imports

**Scale/Scope**: one module (`interior.py`, +~450 lines), `__init__.py` exports, version bump; ~6 furniture parameter dataclasses + composite + 4 type-keyed builders + bulkhead builder; ~30 new tests

## Constitution Check

| Principle | Status |
|---|---|
| I. Parametric Everything | PASS — all furniture dims are named dataclass fields with defaults |
| II. Reproducibility | PASS — furniture is a pure function of (compartment spec, params); SC-004 |
| III. FreeCAD-Idiomatic | PASS — Part-workbench B-rep solids + boolean Cut; constitution forbids raw MESH, not Part::Feature (which the interior module already uses). No `Mesh.Mesh`. |
| IV. Reference Fidelity | PASS — defaults plausible vs Alternativ1/2.JPG within ±1% on recorded dims; fine detail exempt |
| V. Test-Gated | PASS (planned) — pytest + ruff + mypy; visual signoff |
| VI. Public OSS / SemVer | PASS — additive, PATCH bump |
| VII. FreeCAD Version Discipline | PASS — no range change |

No violations. **Heightened-risk note** (carried from specs 010/011): FreeCAD is not on the implementation host, so the geometry tier cannot execute here; the galley boolean `Part.Cut` is the only fragile op (blind recess into a solid box → manifold by construction, guarded by a post-cut solid-count assertion).

## Project Structure

```text
specs/012-interior-detail-alternativ1-2/
├── plan.md  spec.md  spec.allium  research.md  data-model.md  quickstart.md
├── contracts/python-api.md  checklists/requirements.md  tasks.md

src/storebro/
├── interior.py   # MODIFIED — 6 furniture param dataclasses + FurnitureParameters
│                 #   composite; per-type builders (_build_berth, _build_galley,
│                 #   _build_head, _build_salon, _build_bulkhead); furniture wrappers;
│                 #   Compartment gains furniture; build_interior parameters_furniture
│                 #   kwarg + Alt1/Alt2 gate; galley counter manifold assert
├── __init__.py   # MODIFIED — export FurnitureParameters (+ sub-dataclasses); __version__ 1.0.6
└── (hull/deck/export/cli — UNCHANGED)

pyproject.toml    # MODIFIED — 1.0.5 → 1.0.6

tests/
├── unit/    # NEW per-dataclass validation tests + version test update
└── geometry/  # NEW requires_freecad: berth/cushion, galley counter manifold + cuts,
            #   head fittings, salon, bulkhead, gate (Alt3 boxy), determinism,
            #   rollback, zero-count, stl-watertight, visual signoff; MODIFIED
            #   existing interior tests asserting boxy compartment counts for Alt1/2
```

**Structure Decision**: All furniture lives in `interior.py` — it owns the compartment specs the furniture is keyed to. Furniture is built by per-compartment-type dispatch on `CompartmentSpec.compartment_type`, gated by `layout_name in {Alternativ1, Alternativ2}`. The builders are generic (keyed only by type + envelope), so spec 013 enables Alt3-5 by widening the gate.

## Furniture design (per compartment type, all Part::Feature B-rep)

- **forward_cabin → Berth**: a base box (`Part.makeBox`, height `base_height`, inset `wall_inset` from compartment walls) + `cushion_count` cushion boxes on top (`cushion_thickness`). Within envelope.
- **galley → Counter**: a worktop box (height `counter_height`, thickness `counter_thickness`) with a sink recess and a stove recess cut via `Part.Cut` of shallow boxes (depth < thickness) from the top. The result is one fused solid; manifold-assert (`Solids == 1`, `isValid`).
- **head → Toilet + Sink**: a pedestal+bowl box (toilet) and a sink box, positioned against the compartment walls.
- **salon → Seating + Table**: an L-/box settee (`seat_height`) + a table (top + pedestal, `table_height`).
- **Bulkhead**: a thin box (`thickness`) spanning the compartment width/height at its aft boundary.
- Each compartment's wrapper `body` becomes a `Part::Compound` of its furniture pieces (+ bulkhead).

## Cross-artifact note (for /speckit.analyze)

The `spec.allium` was elicited with `is_partdesign_body` invariants before the construction technique was reconsidered. Analyze will reconcile those to `is_brep_solid` (Part::Feature), keeping the volume>0 + single-solid (galley) invariants intact.

## Verification risk

FreeCAD not on host → geometry tier + GUI signoff WRITTEN but PENDING. Lower boolean risk than spec 011 (only the galley counter uses a cut, into an axis-aligned box — the simplest possible manifold-safe recess). Unit + ruff + mypy gate locally.

## Complexity Tracking

No constitution violations — table intentionally empty.
