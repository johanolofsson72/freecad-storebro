# Tasks: Export Format Expansion

**Feature**: 026-export-format-expansion | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

**Scope**: All production code in `src/storebro/export.py` (+ CLI flags in `cli.py`, version in `__init__.py`/`pyproject.toml`). Tests in `tests/unit/` and `tests/geometry/`.

**Testing note**: export library, NOT interactive UI → the destructive-test analog is invalid-extension, empty-body, degenerate-projection, and byte-identity scenarios. The shipped-format set is finalized by the T001 spike (glTF deferred; DXF spike-gated).

---

## Phase 1: Setup — Reproducibility & Headless-Feasibility Spike (BLOCKING GATE)

**Gates the shipped-format set. No writer ships until its format passes the spike (FR-007, clarify Q1).**

- [ ] T001 Write and run `/tmp/spike_026_repro.py` (FreeCAD console, bundled-python `PYTHONPATH`): for OBJ (canonical mesh + header scrub), IGES (`exportIges` + global-section scrub), assembly-compound (STEP/BREP/IGES of a `Part.Compound`), assembly-merged-mesh (STL/OBJ), hand-written R12-ASCII DXF (X-Z projected edges), and gzip (`mtime=0`) — export twice and assert byte-identical SHA-256 after scrubbing; confirm headless availability and that assembly output reflects all bodies. Confirm glTF's GUI exporter is unavailable headless. Record the per-format ship/defer verdict in research.md §R2.

**Checkpoint**: shipped-format set fixed. glTF deferred; each other format ships only if byte-identical.

---

## Phase 2: Foundational (blocking prerequisites for all stories)

- [ ] T002 [P] Add `_maybe_gzip(data: bytes, enabled: bool) -> bytes` to `src/storebro/export.py` (`gzip.compress(data, mtime=0)` when enabled, else passthrough); add the `.gz` suffix rule to extension validation.
- [ ] T003 Add `_combine_bodies(body_or_bodies) -> Shape` (1 body → its `.Shape`; N → `Part.Compound` ordered by `_sorted_subshapes`) and `_combine_meshes(body_or_bodies, tol) -> Mesh` (merge per-body canonical meshes in sorted order, re-canonicalize) to `src/storebro/export.py`.
- [ ] T004 Extend `_KNOWN_EXTENSIONS` with the shipped new formats (`obj`, `iges`, and `dxf` if shipped); wire per-format extension + `.gz` validation.
- [ ] T005 [P] [Unit] Write `tests/unit/test_export_gzip_determinism.py`: `_maybe_gzip` is deterministic (two calls byte-identical, mtime zeroed); decompresses to the input.
- [ ] T006 [P] [Unit] Write `tests/unit/test_export_extension_validation.py`: each new format accepts its extensions and rejects mismatches; `gzip=True` requires `.gz`; `gzip=False` with `.gz` is rejected.

**Checkpoint**: assembly combination + gzip + extension validation exist (T005/T006 unit-green without FreeCAD).

---

## Phase 3: User Story 1 — Full-assembly export (P1) 🎯 MVP

**Goal**: STEP/STL/BREP accept an iterable of bodies and export the whole boat, deterministically; single body unchanged.
**Independent test**: `tests/geometry/test_export_assembly.py` + `test_export_single_body_unchanged.py` green.

- [ ] T007 [US1] Thread `body_or_bodies` acceptance + `gzip=False` into `export_step`, `export_brep`, `export_stl` in `src/storebro/export.py` via `_combine_bodies`/`_combine_meshes`; wrap output bytes in `_maybe_gzip`; keep single-body path byte-identical to spec 002.
- [ ] T008 [US1] Add `gzip=False` to `export_fcstd` (document export) via `_maybe_gzip`.
- [ ] T009 [P] [US1] Write `tests/geometry/test_export_assembly.py`: a multi-body STEP/STL/BREP export's bounding box / triangle count reflects all bodies (not just the hull); two exports byte-identical (equal SHA-256).
- [ ] T010 [P] [US1] Write `tests/geometry/test_export_single_body_unchanged.py`: `export_step/stl/brep(single_body)` is byte-identical (equal SHA-256) before vs after the `body_or_bodies` change (SC-005) — pin the single-body digest.

**Checkpoint**: the whole boat exports to STEP/STL/BREP — MVP deliverable (the silent-drop bug is fixed).

---

## Phase 4: User Story 2 — OBJ export (P2)

**Goal**: a valid, deterministic Wavefront OBJ of a body or assembly.
**Independent test**: `tests/geometry/test_export_obj.py` green.

- [ ] T011 [US2] Add `export_obj(body_or_bodies, target_path, *, overwrite=True, tessellation_tolerance=0.001, gzip=False)` to `src/storebro/export.py`: canonical mesh → `Mesh.write(.obj)` → `_scrub_obj_header` → atomic write + `_maybe_gzip` → `ExportArtifact`. Export from `__all__`/`storebro`.
- [ ] T012 [P] [US2] Write `tests/geometry/test_export_obj.py`: a valid OBJ (vertices + triangular faces) is written for a body and an assembly; two exports byte-identical; a gzipped OBJ round-trips.

---

## Phase 5: User Story 3 — IGES export (P2)

**Goal**: a valid, deterministic IGES B-rep of a body or assembly.
**Independent test**: `tests/geometry/test_export_iges.py` green.

- [ ] T013 [US3] Add `export_iges(body_or_bodies, target_path, *, overwrite=True, gzip=False)`: `Shape.exportIges` on the combined compound → `_canonicalize_iges_header` (scrub global-section timestamp/filename) → atomic write + `_maybe_gzip` → `ExportArtifact`. Export from `__all__`/`storebro`.
- [ ] T014 [P] [US3] Write `tests/geometry/test_export_iges.py`: a valid IGES is written for a body and an assembly that re-imports with solids; two exports byte-identical (global section scrubbed).

---

## Phase 6: User Story 5 — 2D DXF profile (P3, spike-gated)

**Goal**: a valid, deterministic 2D X-Z profile DXF (only if T001 ships DXF).
**Independent test**: `tests/geometry/test_export_dxf_profile.py` + `tests/unit/test_export_dxf_bytes.py` green.

- [ ] T015 [US5] (if shipped) Add `_project_edges_xz(shape)` + `_write_r12_dxf(segments)` + `export_dxf_profile(body_or_bodies, target_path, *, plane="xz", overwrite=True, gzip=False)` to `src/storebro/export.py`: project edges onto X-Z (drop Y), sort segments, hand-write minimal R12 ASCII DXF (no timestamp/handles), reject an empty projection. Export from `__all__`/`storebro`.
- [ ] T016 [P] [US5] (if shipped) Write `tests/unit/test_export_dxf_bytes.py` (hand-written DXF byte-shape from a fixed segment list, no FreeCAD) + `tests/geometry/test_export_dxf_profile.py` (a valid DXF with the projected outline; two exports byte-identical; degenerate projection rejected).

---

## Phase 7: User Story 4 + 6 — glTF (deferred) + gzip (P1/P3)

- [ ] T017 [US4] glTF: NO writer — record the deferral (GUI-only exporter unavailable headless) in research.md + spec.allium; ensure `gltf` is NOT in `_KNOWN_EXTENSIONS` / CLI choices.
- [ ] T018 [P] [US6] Write `tests/geometry/test_export_gzip_roundtrip.py`: an STL/OBJ/IGES exported with `gzip=True` decompresses (stdlib `gzip`) to bytes equal to the corresponding un-gzipped export; two gzipped exports byte-identical (SC-004).

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T019 [P] CLI: add the shipped new formats to `--format` choices + a `--gzip` flag in `src/storebro/cli.py`; export the FULL assembly (all built bodies) by default for the multi-body formats (was hull-only). Update the `test_cli_flags_v103.py` baseline with a spec-026 citation for the new flags/choices.
- [ ] T020 Bump version 1.12.0 → 1.13.0 in `src/storebro/__init__.py` and `pyproject.toml`; update the version-consistency test.
- [ ] T021 Run the gate: `uv run pytest` (unit) + `PYTHONPATH=… uv run pytest -m requires_freecad` (geometry) + `uv run ruff check .` + `uv run mypy src/`. Fix failures. Build signoff exports (assembly STEP + OBJ + IGES + a gzipped STL) and record their SHA-256.

---

## Dependencies & Execution Order

- **T001 (spike) blocks everything** — its verdict sets the shipped-format set (DXF in/out; glTF out).
- **Phase 2 (T002–T006) blocks all stories** — gzip, combine, extension validation.
- **Stories after Phase 2**: US1 (T007–T010), US2 (T011–T012), US3 (T013–T014), US5/DXF (T015–T016), gzip (T018) all touch `export.py`/its tests; serialize production edits, no logical inter-dependency. US1 (assembly) is foundational for the others (they reuse `_combine_*`), so do it first.
- **Phase 8**: T019 (CLI) needs the shipped formats; T020/T021 last.
- **[P]** marks parallelizable test-writing + independent unit tasks; production edits to `export.py` are serialized.

## MVP

**US1 (full-assembly export) alone is a shippable increment** — it fixes the silent hull-only drop in STEP/STL/BREP. Phases 1–3 deliver it; Phases 4–7 add OBJ/IGES/DXF/gzip (glTF deferred); Phase 8 finalizes.

## Implementation Strategy

Spike-gate first (Phase 1, sets the shipped set) → foundational gzip/combine/extension (Phase 2) → assembly MVP (Phase 3) → OBJ (Phase 4) → IGES (Phase 5) → DXF if shipped (Phase 6) → glTF defer + gzip roundtrip (Phase 7) → CLI + version + full verification (Phase 8). One continuous run; the only legitimate stops are spike-driven ship/defer verdicts (recorded, not blocking).
