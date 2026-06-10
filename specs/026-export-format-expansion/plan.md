# Implementation Plan: Export Format Expansion

**Branch**: `026-export-format-expansion` | **Date**: 2026-06-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/026-export-format-expansion/spec.md`

## Summary

Broaden the spec 002 export surface, all in `src/storebro/export.py` (+ CLI flags): full-assembly (multi-body) export for the non-FCStd formats, OBJ, IGES, optional deterministic gzip, and — spike-permitting — a 2D DXF profile. Reuses the spec 002 machinery (canonical mesh facet ordering, sorted sub-shapes, header/timestamp scrubbing, atomic write, SHA-256). Constitution II is non-negotiable: a format ships only if a pre-implementation spike (T001) proves it byte-reproducible; non-reproducible / headless-infeasible formats are deferred.

**Headless reality (capability probe, this host):** `Shape.exportIges` and `Mesh.Mesh.write(.obj)` work in console mode; the GUI workbench modules `importGltf` / `importDXF` / `importOBJ` are **unavailable headless**. So IGES (B-rep), OBJ (canonical mesh), assembly (compound / merged mesh), and gzip are the headless-feasible, deterministic core. glTF requires the GUI exporter → **deferred** (hand-writing glTF buffers is disproportionate to its value). DXF is hand-written as minimal R12 ASCII from a 2D X-Z projection (deterministic; spike-gated).

## Technical Context

**Language/Version**: Python 3.11+ (FreeCAD 1.1 bundled Python)
**Primary Dependencies**: FreeCAD 1.1+ (`Part`, `Mesh`, `MeshPart`), stdlib `gzip`/`hashlib`/`zipfile`. No new third-party deps.
**Storage**: writes export artifacts to disk (atomic write, spec 002).
**Testing**: `pytest` (unit: extension validation, gzip determinism, DXF byte-shape — no FreeCAD where possible; geometry: `requires_freecad`), `ruff`, `mypy --strict`.
**Target Platform**: FreeCAD 1.1+ macOS/Linux, **console/headless** (the deploy + CI path) — GUI-only exporters are out.
**Project Type**: Single library (`src/storebro/`).
**Performance Goals**: human-scale (seconds); the assembly merge of all bodies is the dominant cost.
**Constraints**: byte-identical output (constitution II, the gating constraint); single-body exports byte-identical to spec 002; mesh in the export adapters only (constitution III).
**Scale/Scope**: one module (`export.py`, ~946 LOC) + CLI flags + version. Net additions: assembly combination, OBJ/IGES writers (+ DXF if spike-clean), gzip wrapper, per-format determinism scrubbing, CLI `--gzip` + new `--format` choices + full-assembly default.

## Constitution Check

| Principle | Status | Compliance |
|---|---|---|
| I. Parametric Everything | ✅ | New params (mesh tessellation for OBJ, DXF projection plane, gzip toggle) are named with defaults. |
| II. Reproducibility (NON-NEGOTIABLE) | ✅ | THE gating constraint. A format ships only if the T001 spike proves it byte-identical after scrubbing; non-reproducible formats are deferred. Single-body exports stay byte-identical to spec 002. Determinism tests per shipped format. |
| III. FreeCAD-Idiomatic | ✅ | B-rep via `Shape.exportIges`/`Part.Compound`; mesh via the spec 002 `_build_canonical_mesh` + `Mesh.write`; DXF hand-written from `Part`-projected edges. Mesh stays in the export adapters (the named mesh-export exception). |
| IV. Reference Fidelity | ✅ | Export-only; geometry unchanged. The assembly export makes the *whole boat* exportable (more faithful than today's hull-only drop). |
| V. Test-Gated | ✅ | New unit (extension, gzip, DXF bytes) + geometry (assembly content, OBJ/IGES validity, per-format determinism, single-body byte-identity) tests. ruff + mypy gate. |
| VI. Public OSS / SemVer | ✅ | Additive (new functions / additive `bodies`+`gzip` params with defaults). MINOR bump 1.12.0 → 1.13.0. |
| VII. FreeCAD Version Discipline | ✅ | Uses only headless-available FreeCAD APIs (the probe confirmed exportIges + Mesh.write); GUI-only exporters are explicitly deferred. |

**Result: PASS** (no violations; deferrals are constitution-II-driven, not violations).

## Project Structure

```text
specs/026-export-format-expansion/
├── plan.md research.md data-model.md quickstart.md contracts/python-api.md
├── spec.md spec.allium tasks.md

src/storebro/
├── export.py            # THE feature — assembly combine, OBJ/IGES/DXF writers, gzip, per-format scrub
├── cli.py               # new --format choices + --gzip; full-assembly default for multi-body formats
└── __init__.py / pyproject.toml  # new export fns exported; __version__ 1.12.0 -> 1.13.0

tests/
├── unit/
│   ├── test_export_extension_validation.py  # NEW — new-format extension checks (no FreeCAD)
│   ├── test_export_gzip_determinism.py       # NEW — deterministic gzip (no FreeCAD)
│   └── test_export_dxf_bytes.py              # NEW — hand-written DXF byte-shape (no FreeCAD, if shipped)
└── geometry/
    ├── test_export_assembly.py               # NEW — multi-body content + ordering
    ├── test_export_obj.py                    # NEW — OBJ validity + determinism
    ├── test_export_iges.py                   # NEW — IGES validity + determinism
    ├── test_export_dxf_profile.py            # NEW — DXF profile (if shipped)
    ├── test_export_gzip_roundtrip.py         # NEW — gzip decompresses to the un-gzipped export
    └── test_export_single_body_unchanged.py  # NEW — single-body byte-identical to spec 002
```

**Structure Decision**: Single library; the feature lives in `export.py` (the spec 002 module), with CLI flags and a version bump. Same shape as spec 027 (CLI enhancements) which grew the CLI without new modules.

## Build Sequence (one task — no stops between steps)

0. **Reproducibility + headless-feasibility spike** (`/tmp/spike_026_*.py`, FreeCAD console) — BLOCKING GATE. For each candidate format (OBJ, IGES, assembly-compound, assembly-mesh, DXF-hand-written, gzip), export twice and assert byte-identical SHA-256 after scrubbing; confirm headless availability. glTF is probed but expected unavailable headless → defer. Record the per-format verdict in research.md; the verdict sets what ships.
1. **Assembly combination** — a `_combine_bodies(bodies)` helper: 1 body → its shape (back-compat); N bodies → `Part.Compound` ordered by the spec 002 `_sorted_subshapes`, or a merged canonical mesh for mesh formats. Thread `bodies: Body | Iterable[Body]` acceptance into the export functions.
2. **gzip wrapper** — a `_maybe_gzip(data, enabled)` returning `gzip.compress(data, mtime=0)` (deterministic) or `data`; a `gzip: bool = False` kwarg on each export function; `.gz` extension validation.
3. **OBJ writer** — `export_obj(body_or_bodies, path, *, tessellation_tolerance, gzip)`: build the canonical mesh (spec 002 `_build_canonical_mesh`), `Mesh.write(.obj)`, scrub any nondeterministic header comment (reuse the header-scrub pattern), atomic write, ExportArtifact.
4. **IGES writer** — `export_iges(body_or_bodies, path, *, gzip)`: `Shape.exportIges` on the combined compound, scrub the IGES global-section timestamp (adapt `_canonicalize_step_header`), atomic write, ExportArtifact.
5. **DXF profile writer (spike-gated)** — `export_dxf_profile(body_or_bodies, path, *, plane="xz", gzip)`: project the combined shape's edges onto the X-Z plane, hand-write minimal R12 ASCII DXF (deterministic, no timestamp/handles), reject a degenerate (no-edge) projection. Ship only if the spike confirms clean determinism.
6. **glTF** — DEFERRED (GUI-only exporter unavailable headless). Record the deferral in research.md + spec.allium; do not add a writer.
7. **Extension table + dispatch** — extend `_KNOWN_EXTENSIONS` with `obj`, `iges`, (`dxf`), and the `.gz` suffix rule; per-format validation.
8. **CLI** — add the shipped new formats to `--format` choices + a `--gzip` flag; export the FULL assembly (all built bodies) by default for the multi-body formats (fixing the hull-only drop), keeping existing invocations parsing.
9. **Exports + version** — export the new functions from `storebro/__init__.py`; bump 1.12.0 → 1.13.0 + version-consistency test.
10. **Tests** (unit + geometry) per the structure; `pytest`/`ruff`/`mypy --strict`.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OBJ/IGES writer emits a nondeterministic header (version/timestamp) | Scrub the header (reuse the spec 002 STEP/BREP header-canonicalization pattern); the T001 spike proves byte-identity before shipping. |
| glTF/DXF unavailable headless | glTF deferred (documented). DXF hand-written from projected edges (no GUI module needed), spike-gated. |
| Assembly compound changes single-body byte output | `_combine_bodies` returns the lone shape unchanged for 1 body → single-body export byte-identical to spec 002 (a dedicated test guards SC-005). |
| CLI full-assembly default changes existing step/stl/brep output | This is the intended fix (today's hull-only is a bug). The CLI flag-baseline test is updated with a spec-026 citation; the single-body *functions* are unchanged. |
| DXF projection degenerate / non-deterministic | Reject an empty projection; hand-write sorted edges (deterministic); defer DXF if the spike shows instability. |
| gzip nondeterminism (mtime/filename in header) | `gzip.compress(data, mtime=0)` with no filename → deterministic; unit test asserts two gz are byte-identical. |

## Phase 2 note

`/speckit-tasks` expands this into dependency-ordered tasks (spike first as a hard gate that sets the shipped-format set, then assembly + gzip [foundational], then per-format writers, CLI, version, tests). `/speckit.analyze` runs between tasks and implement.
