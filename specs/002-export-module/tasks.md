---
description: "Task list for the export module (spec 002)"
---

# Tasks: Export Module

**Input**: Design documents from `/specs/002-export-module/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/python-api.md](./contracts/python-api.md), [quickstart.md](./quickstart.md), [spec.allium](./spec.allium)

**Tests**: REQUIRED per constitution principle V (Test-Gated Releases). Every public writer has at least one unit + one geometry test (SC-005), 5+ invalid-input cases exist (SC-006), and one forced-failure test exists per writer (SC-007).

**Organization**: Tasks grouped by user story. Implementation tasks that touch the same file (`src/storebro/export.py`) are sequential — `[P]` only marks tasks on distinct files with no dependency on incomplete work.

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Distinct files, no dependencies on incomplete tasks
- **[Story]**: US1 / US2 / US3 (no label for Setup, Foundational, Polish)

## Path Conventions

Single Python project, src-layout (continues from spec 001):
- Library source: `src/storebro/`
- Tests: `tests/unit/` (no FreeCAD), `tests/geometry/` (marker `requires_freecad`)
- Hash baselines: `tests/geometry/fixtures/expected_hashes.toml`
- Examples: `docs/examples/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify the spec 001 scaffolding still applies, extend it where the export module needs new infrastructure (hash baseline fixture). No story label.

- [X] T001 Verify spec 001 scaffolding intact: `src/storebro/__init__.py`, `src/storebro/_freecad_check.py`, `tests/conftest.py`, `tests/unit/__init__.py`, `tests/geometry/__init__.py`, `tests/geometry/conftest.py` all exist; `uv run pytest --collect-only` runs cleanly
- [X] T002 Create `tests/geometry/fixtures/` directory and an empty placeholder `tests/geometry/fixtures/expected_hashes.toml` with a header comment explaining the keying convention from `research.md` R6
- [X] T003 [P] Create `tests/geometry/fixtures/refresh_hashes.py` — a small script that builds the default hull, calls every writer, computes SHA-256 of each output, and prints TOML stanzas to stdout. The maintainer runs this on a FreeCAD-equipped host once per FreeCAD version bump and pastes the output into `expected_hashes.toml` (per research.md R6)

**Checkpoint**: directory tree clean; `uv run pytest --collect-only` reports the existing spec-001 tests and no collection errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Public exception types, the input/output value objects, and the shared helpers (`_resolve_target_path`, `_atomic_write`, `_sorted_subshapes`, `_sha256_of_file`). All four writers in US1/US2/US3 depend on these.

**⚠️ CRITICAL**: No US1/US2/US3 work can begin until this phase is complete.

- [X] T004 Create `src/storebro/export.py` and define the public exception classes at the top: `ExportInputError(ValueError)` with `(field, reason, offending_value=None)` constructor and message format per data-model §4; `ExportWriteError(RuntimeError)` with `(message, *, target_path=None, underlying=None, format=None, detected_version=None, supported_range=None)` and message format per data-model §5
- [X] T005 In `src/storebro/export.py` (after T004), define `ExportArtifact` as `dataclass(frozen=True)` with fields `target_path`, `format`, `byte_count`, `sha256`, `build_duration_seconds` per data-model §3
- [X] T006 In `src/storebro/export.py` (after T005), implement private `_resolve_target_path(path, expected_extensions, overwrite)` per data-model §1: resolve absolute path, validate parent exists and is a directory, target is not a directory, extension matches expected set, raise `ExportInputError` with structured `field`/`reason`/`offending_value` on every failure mode
- [X] T007 In `src/storebro/export.py` (after T006), implement private `_resolve_tessellation_tolerance(value)` per data-model §2: reject `value <= 0` or NaN with `ExportInputError("tessellation_tolerance", ...)`; return the validated float
- [X] T008 In `src/storebro/export.py` (after T007), implement private `_atomic_write(target_path, body_bytes)` per research.md R7: `tempfile.mkstemp(dir=target.parent, prefix=f".{name}.", suffix=".tmp")`, write + `fsync`, `os.replace` to target, raise `ExportWriteError` wrapping the underlying `OSError` on any failure (including cross-filesystem) after `os.unlink`-ing the tmp; suppress unlink errors with `contextlib.suppress(OSError)`
- [X] T009 In `src/storebro/export.py` (after T008), implement private `_sorted_subshapes(shape)` per research.md R5: recursively sort `shape.SubShapes` by `(CenterOfMass.x, CenterOfMass.y, CenterOfMass.z, _shape_type_rank(ShapeType))` lex order; return sorted children with their own subshapes likewise sorted
- [X] T010 [P] In `src/storebro/export.py` (T010 touches a separate concern in the same file — wait until T009 completes), implement private `_sha256_of_file(path)`: stream the file in 64 KB chunks through `hashlib.sha256`, return the lower-case 64-char hex digest
- [X] T011 Update `src/storebro/__init__.py` to re-export `ExportArtifact`, `ExportInputError`, `ExportWriteError` (writers themselves come in later phases). Add them to `__all__`.
- [X] T012 [P] `tests/unit/test_export_errors.py`: assert `issubclass(ExportInputError, ValueError)` and `issubclass(ExportWriteError, RuntimeError)`; verify every attribute is set by `__init__`; verify message format cites field/reason/offending_value per data-model §4 and §5 — at minimum 5 distinct cases covering the SC-006 invalid-input budget
- [X] T013 [P] `tests/unit/test_export_paths.py`: parameterize over every validation rule in `_resolve_target_path`: missing parent directory, target is a directory, wrong extension per format (5+ cases: `.txt` for STEP, `.dat` for STL, etc.), `overwrite=False` with existing file, target with no extension; each case raises `ExportInputError` with the expected `field` and a `reason` string that names the failure mode

**Checkpoint**: foundational unit tests pass: `uv run pytest tests/unit/test_export_errors.py tests/unit/test_export_paths.py -v`.

---

## Phase 3: User Story 1 - FreeCAD scripter exports hull Body to STEP (Priority: P1) 🎯 MVP

**Goal**: A scripter calls `export_step(hull.body, "/tmp/boat.step")` and gets back an `ExportArtifact`. Re-running produces byte-identical output (constitution II checkpoint). STEP HEADER fields are scrubbed to the project sentinel; LF line endings on every OS.

**Independent Test**: from a Python REPL with FreeCAD on PATH, run `from storebro import build_hull, export_step; a = export_step(build_hull().body, "/tmp/a.step"); b = export_step(build_hull().body, "/tmp/b.step"); assert a.sha256 == b.sha256` — passes on a fresh run.

### Implementation (sequential — same file `src/storebro/export.py`)

- [X] T014 [US1] In `src/storebro/export.py`, implement private `_set_step_schema_to_ap214()` per research.md R1: read+set FreeCAD's `User parameter:BaseApp/Preferences/Mod/Import/hSTEP/Scheme` preference to `"AP214"` via FreeCAD's `Preferences` / `ParameterGrp` API. Idempotent; cached after first call.
- [X] T015 [US1] In `src/storebro/export.py`, implement private `_canonicalize_step_header(raw_bytes)` per research.md R1: regex-replace the `FILE_NAME` and `FILE_DESCRIPTION` lines in the STEP HEADER section with fixed sentinel strings (`"freecad-storebro"` producer + `"1980-01-01T00:00:00"` timestamp); regex-replace any line endings with LF; return the canonicalized bytes
- [X] T016 [US1] In `src/storebro/export.py`, implement public `export_step(body, target_path, *, overwrite=True)` per contracts/python-api.md: (a) call `_freecad_check.ensure_supported_freecad()`; (b) `_resolve_target_path(target_path, [".step", ".stp"], overwrite)`; (c) validate `body.Shape` non-empty (raise `ExportInputError("body", "shape is empty")` otherwise); (d) `_set_step_schema_to_ap214()`; (e) `time.perf_counter()` start; (f) build a canonical-ordered Shape via `_sorted_subshapes(body.Shape)` (or use the original Shape if FreeCAD's STEP exporter handles ordering — see research.md R5); (g) call `Part.export([canonical_shape], tmp_path)` into a tempfile; (h) read tmp bytes, `_canonicalize_step_header`, `_atomic_write` to target; (i) wrap any FreeCAD/IO exception in `ExportWriteError(format="step", ...)`; (j) `_sha256_of_file(target_path)` and return `ExportArtifact(format="step", ...)`
- [X] T017 [US1] Update `src/storebro/__init__.py` to re-export `export_step`. Add to `__all__`.

### Tests for US1 (parallel; distinct files)

- [X] T018 [P] [US1] `tests/geometry/test_export_step.py`: build a default hull, call `export_step` to a temp path, assert: returned `ExportArtifact.format == "step"`, `byte_count > 0`, `build_duration_seconds < 5.0` (SC-002 STEP budget, analyze remediation A1), SHA-256 matches the baseline in `expected_hashes.toml` for the running FreeCAD version (skip-or-fail on missing baseline with a clear "run refresh_hashes.py" message), file content starts with `"ISO-10303-21;"`, FILE_NAME line contains `"freecad-storebro"` and not the local user/hostname, `b"\r\n" not in output_bytes` (FR-016 LF endings, analyze remediation A2)
- [X] T019 [P] [US1] `tests/geometry/test_export_step_determinism.py`: two back-to-back `export_step` calls with the same body produce byte-identical files (SHA-256 equality), regardless of run order or wall-clock interval
- [X] T020 [P] [US1] `tests/geometry/test_export_step_atomicity.py`: monkeypatch `Part.export` to raise mid-call; assert `ExportWriteError` raised AND no partial file at the target path (FR-008)

**Checkpoint**: `uv run pytest -m requires_freecad tests/geometry/test_export_step*.py -v` green.

---

## Phase 4: User Story 2 - Boat restorer writes complete .FCStd (Priority: P2)

**Goal**: A restorer calls `export_fcstd(hull.document, "/tmp/boat.FCStd")` and gets an archival file. Reopening it in the FreeCAD GUI restores the document with full parametric history. Two writes of the same document produce identical bytes (zip-scrub procedure honors constitution II for the most non-deterministic FreeCAD format). Includes BREP since the same persona archives both formats.

**Independent Test**: build a default hull, call `export_fcstd(hull.document, path)`, run `FreeCAD.openDocument(path)`, assert the reopened document has the same Body labels and dimension properties as the original. Then run the writer twice and assert SHA-256 equality.

### Implementation (sequential — same file `src/storebro/export.py`)

- [X] T021 [US2] In `src/storebro/export.py`, implement private `_canonical_xml_serialize(tree)` per research.md R4: walk an `xml.etree.ElementTree` and emit text with sorted attribute order per element, fixed indent (2 spaces), LF line endings; return UTF-8 bytes
- [X] T022 [US2] In `src/storebro/export.py`, implement private `_scrub_fcstd_zip(raw_zip_bytes)` per research.md R4: open the zip in memory, for each entry rewrite `date_time = (1980, 1, 1, 0, 0, 0)`; for `Document.xml` parse with `xml.etree.ElementTree`, set `CreationDate` and `LastModifiedDate` to `"1980-01-01T00:00:00Z"`, set `CreatedBy` and `LastModifiedBy` to `"freecad-storebro"`, re-serialize via `_canonical_xml_serialize`; re-pack the zip with alphabetical entry order and `compression=zipfile.ZIP_STORED`; return the canonicalized bytes
- [X] T023 [US2] In `src/storebro/export.py`, implement public `export_fcstd(document, target_path, *, overwrite=True)` per contracts/python-api.md: (a) `ensure_supported_freecad()`; (b) `_resolve_target_path(target_path, [".FCStd", ".fcstd"], overwrite)`; (c) recompute the document (`document.recompute()`); (d) `time.perf_counter()` start; (e) `document.saveAs(tmp_path_inside_target_parent_dir)`; (f) read tmp bytes, `_scrub_fcstd_zip`, `_atomic_write` to target; (g) wrap any FreeCAD/IO exception in `ExportWriteError(format="fcstd", ...)`; (h) `_sha256_of_file` and return `ExportArtifact(format="fcstd", ...)`
- [X] T024 [US2] In `src/storebro/export.py`, implement private `_canonicalize_brep_header(raw_bytes)` per research.md R3: regex-scrub any `Originator`/`Creator` comment line to the project sentinel; normalize line endings to LF; return bytes
- [X] T025 [US2] In `src/storebro/export.py`, implement public `export_brep(body, target_path, *, overwrite=True)`: similar shape to `export_step` but call `body.Shape.exportBrep(tmp_path)` (FreeCAD's native BREP writer), then `_canonicalize_brep_header` + `_atomic_write`. Wrap exceptions in `ExportWriteError(format="brep", ...)`. Return `ExportArtifact(format="brep", ...)`
- [X] T026 [US2] Update `src/storebro/__init__.py` to re-export `export_fcstd` and `export_brep`. Add both to `__all__`.

### Tests for US2 (parallel; distinct files)

- [X] T027 [P] [US2] `tests/geometry/test_export_fcstd.py`: build hull → `export_fcstd` → assert format/byte_count/SHA-256-against-baseline; assert `build_duration_seconds < 3.0` (SC-002 .FCStd budget, analyze remediation A1); reopen with `FreeCAD.openDocument(path)` and assert the reopened doc has a `Hull` Body with all 8 named properties intact (`LOA`, `BeamMax`, `Draft`, `Freeboard`, `SheerHeightAft`, `SheerHeightFwd`, `DeadriseAmidships`, `TransomAngle`)
- [X] T028 [P] [US2] `tests/geometry/test_export_fcstd_metadata.py`: unzip the written `.FCStd` into memory; parse `Document.xml`; assert `CreatedBy == "freecad-storebro"`, `LastModifiedBy == "freecad-storebro"`, `CreationDate == "1980-01-01T00:00:00Z"`, `LastModifiedDate == "1980-01-01T00:00:00Z"`; assert all zip entries have `date_time == (1980, 1, 1, 0, 0, 0)`; assert entries appear in alphabetical order; assert no entry uses `ZIP_DEFLATED`
- [X] T029 [P] [US2] `tests/geometry/test_export_fcstd_determinism.py`: two back-to-back `export_fcstd` calls → identical SHA-256
- [X] T030 [P] [US2] `tests/geometry/test_export_brep.py`: build hull → `export_brep` → assert format/SHA-256-against-baseline; assert `build_duration_seconds < 3.0` (SC-002 BREP budget, analyze remediation A1); file content starts with `"DBRep_DrawableShape"` (BREP magic); assert `b"\r\n" not in output_bytes` (FR-016 LF endings, analyze remediation A2); `Originator` comment contains `"freecad-storebro"`
- [X] T031 [P] [US2] `tests/geometry/test_export_brep_determinism.py`: two back-to-back `export_brep` calls → identical SHA-256

**Checkpoint**: `uv run pytest -m requires_freecad tests/geometry/test_export_fcstd*.py tests/geometry/test_export_brep*.py -v` green.

---

## Phase 5: User Story 3 - Naval architecture student exports STL (Priority: P3)

**Goal**: A student calls `export_stl(hull.body, "/tmp/boat.stl")` and gets a watertight binary STL with deterministic triangle ordering. Custom `tessellation_tolerance` produces a measurably different (but byte-deterministic-for-that-value) output. STL is the sole mesh emitter (FR-012).

**Independent Test**: build a hull, call `export_stl(body, path)` and `export_stl(body, path2, tessellation_tolerance=0.0001)`; the two files have different byte counts (the second is larger because tighter tolerance → more triangles) but each is byte-identical when written twice with the same arguments. Mesh passes watertight check.

### Implementation (sequential — same file `src/storebro/export.py`)

- [X] T032 [US3] In `src/storebro/export.py`, implement private `_build_canonical_mesh(body_shape, tessellation_tolerance_m)` per research.md R2: call `MeshPart.meshFromShape(Shape=body_shape, LinearDeflection=tolerance_m * 1000.0, AngularDeflection=0.5)`; sort the returned `Mesh.Mesh` facets in-place on a copy by their centroid (apply FR-019 to triangles); return the canonical mesh
- [X] T033 [US3] In `src/storebro/export.py`, implement private `_check_watertight(mesh)` per SC-008: assert `mesh.isSolid()` is True and `mesh.hasNonManifolds()` and `mesh.hasSelfIntersections()` are False; on failure raise `ExportWriteError(format="stl", "mesh is not watertight")`
- [X] T034 [US3] In `src/storebro/export.py`, implement public `export_stl(body, target_path, *, overwrite=True, tessellation_tolerance=0.001)`: (a) `ensure_supported_freecad()`; (b) `_resolve_target_path(target_path, [".stl"], overwrite)`; (c) `_resolve_tessellation_tolerance(tessellation_tolerance)`; (d) validate body.Shape non-empty; (e) `time.perf_counter()` start; (f) `_build_canonical_mesh(body.Shape, tessellation_tolerance)`; (g) `_check_watertight(mesh)`; (h) `mesh.write(tmp_path, "STLB")` to force binary STL (FR-011); (i) read tmp bytes, `_atomic_write` to target (no header scrub needed for binary STL); (j) wrap exceptions in `ExportWriteError(format="stl", ...)`; (k) return `ExportArtifact(format="stl", ...)`
- [X] T035 [US3] Update `src/storebro/__init__.py` to re-export `export_stl`. Add to `__all__`.

### Tests for US3 (parallel; distinct files)

- [X] T036 [P] [US3] `tests/geometry/test_export_stl.py`: build hull → `export_stl` → assert format/byte_count/SHA-256-against-baseline; assert `build_duration_seconds < 10.0` (SC-002 STL budget, analyze remediation A1); first 80 bytes are a binary STL header (NOT the ASCII `"solid"` magic); triangle count > 0
- [X] T037 [P] [US3] `tests/geometry/test_export_stl_tessellation.py`: build three STLs from the same body with tolerances `0.005` (coarse), `0.001` (default), `0.0001` (fine). Tighter tolerance produces more triangles, hence larger files. Assert `fine.byte_count > default.byte_count > coarse.byte_count` (FR-010, analyze remediation A5).
- [X] T038 [P] [US3] `tests/geometry/test_export_stl_watertight.py`: `export_stl(hull.body, ...)` produces a mesh where every edge is shared by exactly 2 triangles (SC-008). Use the produced binary STL bytes (parse the triangle table) to verify, OR rely on `Mesh.Mesh.isSolid()` post-hoc.
- [X] T039 [P] [US3] `tests/geometry/test_export_stl_determinism.py`: two back-to-back calls with same tolerance → identical SHA-256; same tolerance across two Python processes also identical (best-effort: assert in-process at minimum)

**Checkpoint**: `uv run pytest -m requires_freecad tests/geometry/test_export_stl*.py -v` green.

---

## Phase N: Polish & Cross-Cutting Concerns

- [X] T040 [P] `tests/geometry/test_export_determinism.py`: parameterize over `[step, stl, brep, fcstd]` — for each format, build hull, write twice to different paths, assert SHA-256 equality. This is the constitutional principle II checkpoint (SC-001) gathered into a single cross-format test. Additionally for non-STL formats: assert the output bytes do NOT contain ASCII STL magic `b"facet normal"` or `b"endsolid"` and do NOT match the binary-STL header pattern (FR-012 — STL is the only mesh emitter, analyze remediation A4).
- [X] T041 [P] `tests/geometry/test_export_atomicity.py`: parameterize over the four writers, each with a forced FreeCAD-side failure (monkeypatch the FreeCAD-call inside the writer to raise); assert `ExportWriteError` raised AND no partial file at target path AND no temp file left behind in the target's parent directory
- [X] T042 [P] `tests/unit/test_export_leaf_module.py`: same pattern as `tests/unit/test_hull_leaf_module.py` from spec 001 — assert `storebro.export` does NOT transitively import `storebro.hull`, `storebro.deck`, `storebro.interior`, `storebro.cli`; AST-walk `src/storebro/export.py` to verify no `from storebro.{deck,interior,cli,hull}` imports appear (FR-013)
- [X] T043 [P] `tests/unit/test_export_public_docstrings.py`: introspect `storebro.export.__all__`; for each public name, assert `__doc__` non-empty AND contains a `>>>` example block (FR-015, mirrors spec 001's docstring test)
- [X] T044 [P] Write `docs/examples/export_quickstart.py` — runnable example mirroring the first three sections of `quickstart.md` (default hull, all four exports, custom tessellation)
- [X] T045 [P] Run `uv run ruff check src/storebro/export.py tests/` and `uv run ruff format --check`; fix any complaints
- [X] T046 [P] Run `uv run mypy --strict src/`; fix any type errors
- [X] T047 Run the full suite `uv run pytest -v`; confirm: all unit tests green; geometry tier green on a FreeCAD-equipped host or cleanly skipped without FreeCAD; total skip count clearly reported
- [X] T048 Initial hash-baseline seed: on a FreeCAD-equipped host run `uv run python tests/geometry/fixtures/refresh_hashes.py` and paste output into `tests/geometry/fixtures/expected_hashes.toml`. Commit baseline + note FreeCAD version in CHANGELOG. (This task is a no-op on a non-FreeCAD host; the user runs it later.)
- [X] T049 Manual visual signoff: open the `.FCStd` produced by `export_fcstd` in the FreeCAD GUI, verify document tree shows the hull's parametric history (Body + sketches + loft + mirror + fusion), capture the "Visually verified in FreeCAD: <version> on <OS>" line for the PR description per constitution V
- [X] T050 [P] Update `README.md`: add export module to the Module table; bump module status if alpha → 0.2.0
- [X] T051 [P] Update `PROJECT-BRIEF.md` Core Modules table to mark `storebro.export` as "v0.2.0-alpha (this spec)"
- [X] T052 Tick `specs/INDEX.md`: change spec 002 marker from `[/]` to `[x]`
- [X] T053 Manual STEP cross-tool signoff (SC-003, analyze remediation A3): run `uv run python -c "from storebro import build_hull, export_step; export_step(build_hull().body, '/tmp/storebro_signoff.step')"`, then open `/tmp/storebro_signoff.step` in at least one non-FreeCAD CAD tool (FreeCAD's own viewer as the documented fallback). Verify the geometry is faithful (no missing faces, no obvious corruption). Capture the tool + version in the PR description: "STEP signoff: opened in <tool> <version> on <OS>".

**Final checkpoint**: spec 002 is done when T047 + T049 + T053 are green AND `specs/INDEX.md` ticks `[x] 002`.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: needs spec 001 already merged; otherwise no upstream deps
- **Phase 2 (Foundational)**: needs Phase 1; BLOCKS US1/US2/US3
- **Phase 3 (US1 STEP)**: needs Phase 2; US1 is the MVP
- **Phase 4 (US2 .FCStd + BREP)**: needs Phase 2; independent of US1 but typically done after US1 for incremental delivery
- **Phase 5 (US3 STL)**: needs Phase 2; independent of US1 and US2
- **Phase N (Polish)**: needs all of US1-US3 done

### Per-task dependencies (the important ones)

- T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 (all touch `src/storebro/export.py` or `__init__.py`, sequential)
- T012, T013 [P] after T011 (need exceptions + helpers importable)
- T014 → T015 → T016 → T017 (US1 implementation sequential within `export.py`)
- T021 → T022 → T023 → T024 → T025 → T026 (US2 sequential within `export.py`)
- T032 → T033 → T034 → T035 (US3 sequential within `export.py`)
- All test tasks (T018-T020, T027-T031, T036-T039) are parallel within their phase AFTER the implementation tasks of that phase complete
- T040, T041, T042, T043 [P] after Phase 5 completion
- T047 needs all test tasks completed
- T048 needs T047 AND a FreeCAD host
- T049 needs T048 + manual action

### Within each user story

- Tests after implementation (geometry tests can't be written before the implementation they call into)
- Models / dataclasses before functions
- Public function before public re-exports

---

## Parallel Opportunities

### Setup (Phase 1)

- T003 parallel with T002

### Foundational (Phase 2)

- T012, T013 parallel after T011

### User Story 1 (Phase 3)

- T018, T019, T020 parallel after T017

### User Story 2 (Phase 4)

- T027, T028, T029, T030, T031 parallel after T026

### User Story 3 (Phase 5)

- T036, T037, T038, T039 parallel after T035

### Polish (Phase N)

- T040, T041, T042, T043, T044, T045, T046, T050, T051 all parallel
- T047 sequential after the above
- T048, T049 sequential after T047

---

## Parallel Example: US1 tests

```bash
# After T017 (export_step is wired up and re-exported), run US1 tests:
uv run pytest tests/geometry/test_export_step.py             # T018
uv run pytest tests/geometry/test_export_step_determinism.py # T019
uv run pytest tests/geometry/test_export_step_atomicity.py   # T020
# Or: uv run pytest tests/geometry/test_export_step*.py -m requires_freecad
```

---

## Implementation Strategy

### MVP First (User Story 1 only — STEP)

1. Complete Phase 1: Setup (`tests/geometry/fixtures/` ready)
2. Complete Phase 2: Foundational (exception types + helpers green)
3. Complete Phase 3: User Story 1 (STEP export with byte determinism)
4. **STOP and VALIDATE**: run the determinism test, open the STEP file in a downstream CAD tool
5. Ship as v0.2.0-alpha if STEP alone unlocks the next workflow (it does — visual signoff for spec 001's hull defaults goes via the STEP file)

### Incremental Delivery

1. Setup + Foundational → toolchain green, exception types importable
2. + US1 (STEP) → minimum scriptable export
3. + US2 (.FCStd + BREP) → archival + FreeCAD-native round-trip
4. + US3 (STL) → 3D print + render targets
5. + Polish → ruff/mypy green, hash baselines seeded, visual signoff captured

### Solo Strategy (this project)

Solo OSS per `project_workflow` memory. Direct push to working branch / main per `.claude/rules/spec-register.md`. Commit at every phase checkpoint; ship v0.2.0-alpha when T049 is green.

---

## Notes

- `[P]` tasks touch distinct files with no dependency on incomplete work.
- All `src/storebro/export.py` tasks are sequential because they share the file.
- Hash baselines in `expected_hashes.toml` are FreeCAD-version-specific by design (research.md R6).
- `.FCStd` byte-determinism is the most fragile invariant — expect baseline refreshes on every FreeCAD version bump per constitution VII.
