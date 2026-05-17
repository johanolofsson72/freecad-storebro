# Feature Specification: Export Module

**Feature Branch**: `002-export-module`

**Created**: 2026-05-17

**Status**: Draft

**Input**: User description: "the export module — STEP / STL / BREP / .FCStd writers with byte-identical deterministic output for the same input"

## Clarifications

### Session 2026-05-17

- Q: Which STEP schema version should the STEP writer emit? → A: **AP214** (Automotive Design, ISO 10303-214). FreeCAD's default, broadest interchange compatibility across mainstream CAD tools, well-supported reading and writing across the FreeCAD 1.1+ matrix.
- Q: What is the default STL tessellation tolerance? → A: **0.001 m (1 mm) linear chord deviation**. Absolute (not relative to bounding box). Balanced for both 3D printing and render preview; user-overridable via the `tessellation_tolerance` kwarg per FR-010.
- Q: How does the `.FCStd` writer achieve byte-identical reproducibility given FreeCAD's zip-with-XML container? → A: **Best-effort scrub**. The writer post-processes the FreeCAD-saved `.FCStd` zip in-place: rewrites the zip-entry timestamps to a fixed epoch, scrubs `<Document>`-level `CreationDate`, `LastModifiedDate`, `CreatedBy`, `LastModifiedBy` XML elements to fixed sentinel values, and re-packs the zip with deterministic entry ordering. The pinned SHA-256 baseline is per FreeCAD version; a FreeCAD-version bump is allowed to invalidate the baseline (semver PATCH + CHANGELOG note per constitution VII).
- Q: What canonical sort key produces deterministic topology output ordering across writers? → A: **Lexicographic sort of subshape centroids in `(x, y, z)`** with FreeCAD-internal `ShapeType` as a tie-breaker. Centroid is invariant under FreeCAD-internal element reshuffling and stable across the supported FreeCAD version range.
- Q: What sentinel value populates STEP and BREP "creator"/"originator"/"author" fields? → A: **`"freecad-storebro"` (project name, NO version suffix)**. Keeps byte determinism stable across PATCH bumps; revising it is reserved for semver MAJOR.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - FreeCAD scripter exports a hull Body to STEP for downstream CAD work (Priority: P1)

A FreeCAD scripter (Python user, the same persona who consumed spec 001's hull module) wants to take a `Hull` they just built and write its underlying FreeCAD Body to a `.step` file so they can open it in a non-FreeCAD CAD tool (SolidWorks, Fusion 360, FreeCAD's own viewer, etc.). They expect: a single function call, a file on disk, and — critically — running the same script tomorrow produces byte-for-byte the same file.

**Why this priority**: STEP is the dominant neutral CAD interchange format. Without STEP export the hull module has no path to downstream tooling and the library's stated audience ("FreeCAD scripters, restorers, naval architecture students") cannot do their actual work. Byte-identical output is the single non-negotiable invariant of the entire project (constitution principle II) — this story is the slice that proves the invariant works end-to-end.

**Independent Test**: From a Python REPL with FreeCAD on PATH, run `from storebro import build_hull, export_step; h = build_hull(); export_step(h.body, "/tmp/boat.step")`. Verify the file exists, the SHA-256 of its bytes matches a fixed expected hash, and re-running the script produces the same hash.

**Acceptance Scenarios**:

1. **Given** a freshly-built default hull, **When** the scripter calls the STEP writer with a target path, **Then** a STEP file is written at that path and the SHA-256 of its bytes matches the SHA-256 of any other run with the same inputs on the same FreeCAD version.
2. **Given** the same hull and target path, **When** the scripter runs the export twice in two separate Python processes, **Then** the two files are byte-identical.
3. **Given** a STEP file produced by this module, **When** the scripter opens it in a non-FreeCAD CAD tool, **Then** the geometry is faithful to the source FreeCAD Body within the format's own tolerances (i.e. STEP did not corrupt the geometry on its way out).

---

### User Story 2 - Boat restorer writes a complete `.FCStd` for archival and GUI inspection (Priority: P2)

A boat restorer (or scale modeler) ran the future CLI (spec 005) — or wrote a one-line script — to produce a complete FreeCAD document with the hull, deck, and interior layouts. They want to save that document to disk as a `.FCStd` file so they can open it in the FreeCAD GUI later, share it with collaborators, or archive it. They expect: the file opens cleanly in the FreeCAD GUI on any supported version, with the full parametric history intact, and that two restorations of the same parameter set archive identical bytes.

**Why this priority**: `.FCStd` is the native FreeCAD container; it preserves the parametric history that downstream STEP/STL/BREP exports cannot. Restorers archive `.FCStd` as the source-of-truth and re-export to neutral formats on demand. This story validates that the archival pathway works and that archival reproducibility holds.

**Independent Test**: Build the default hull, call the `.FCStd` writer, open the resulting file in the FreeCAD GUI, confirm the document tree contains the parametric Body with editable hull dimensions. Re-run the build + export sequence and confirm the two `.FCStd` files have identical SHA-256.

**Acceptance Scenarios**:

1. **Given** a FreeCAD document containing a parametric Storebro hull, **When** the restorer calls the `.FCStd` writer, **Then** a `.FCStd` file is written and re-opening it in the FreeCAD GUI restores the full document with parametric history (Body, sketches, loft, mirror, fusion).
2. **Given** the same source document, **When** the writer is called twice (with the same FreeCAD version), **Then** the two `.FCStd` files have identical SHA-256 — no embedded timestamps, no embedded usernames, no environment-dependent absolute paths.

---

### User Story 3 - Naval architecture student exports STL for 3D printing or render previews (Priority: P3)

A naval architecture student wants to take a hull variant they generated and produce an `.stl` file for either 3D-printing a study model or loading into a render tool (Blender, KeyShot, etc.). They expect: a watertight mesh, deterministic triangle ordering across runs (so a hash-based test can pin it), and a tessellation tolerance they can adjust via a documented parameter.

**Why this priority**: STL is the most-requested format for hobbyist downstream work (3D print, render). It is also the canonical "explicit mesh-export adapter" exception to constitution principle III — the rest of the library is B-rep-only, but STL by definition is a triangle mesh. This story validates that the exception is honored without bleeding into the other writers.

**Independent Test**: Build the default hull, call the STL writer with a documented tessellation tolerance, verify the produced file is a valid binary STL with a positive triangle count, and confirm the SHA-256 is identical across two runs with the same parameters and tolerance.

**Acceptance Scenarios**:

1. **Given** a hull Body and a tessellation tolerance, **When** the student calls the STL writer, **Then** a binary STL file is produced with a non-empty triangle list and the file passes a "watertight mesh" check (every edge shared by exactly two triangles).
2. **Given** two runs with the same hull parameters and the same tessellation tolerance, **When** both invoke the STL writer, **Then** the resulting files are byte-identical.
3. **Given** two runs with different tessellation tolerances, **When** both invoke the STL writer, **Then** the resulting files are NOT byte-identical (tighter tolerance → more triangles, looser → fewer).

---

### Edge Cases

- **Output path inside a directory that does not exist**: writer MUST raise a clear typed error citing the missing directory; MUST NOT silently create parent directories (that surprises users with deep typos).
- **Output path is a directory, not a file**: writer MUST raise a clear typed error before touching the filesystem.
- **Output path already exists**: writer overwrites by default (standard scripting expectation) but exposes an opt-in `overwrite=False` to refuse overwrites and raise a typed error instead.
- **Output path has no extension or wrong extension** (e.g. `.txt` for STEP): writer MUST raise a typed error rather than silently write a wrong-extension file.
- **Source Body has no shape** (empty Body, never recomputed): writer MUST raise a typed error before write — empty STEP / STL / BREP / .FCStd files are worse than no file at all.
- **Source document is closed mid-call** (rare but possible if user manipulates FreeCAD state concurrently): writer MUST surface the FreeCAD-side error wrapped in a typed export error.
- **Write fails mid-write** (disk full, permission denied, IO error): writer MUST NOT leave a partial file at the target path. Atomic rename from a temporary file is the expected discipline.
- **Floating-point edge cases producing slightly-different bytes on rerun**: writer MUST guard against this — sort topology elements deterministically, scrub timestamps from format headers, scrub user/host metadata from `.FCStd` containers. A hash drift between two runs with the same inputs is a P0 bug per constitution II.
- **Cross-platform line endings in text-formatted outputs** (STEP and BREP are text): writer MUST emit LF line endings on every platform. Different line endings between Ubuntu and macOS runs would break byte-identical reproducibility.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The export module MUST expose four public writer functions, one per supported format: a `.FCStd` writer that takes a FreeCAD document, and `.step` / `.stl` / `.brep` writers that take a FreeCAD Body (or compatible Shape-carrying object).
- **FR-002**: For identical inputs (same source Body or document, same explicit writer arguments, same FreeCAD version), each writer MUST produce a file whose bytes are identical to those produced by any other invocation. SHA-256 over the output bytes is the canonical comparison.
- **FR-003**: Writers MUST emit no embedded timestamps. STEP headers carry an ISO-style timestamp field by default — the module MUST overwrite it with a fixed, documented sentinel value. Same applies to any "creator", "originator", or "host" field that a format leaves writable.
- **FR-004**: Writers MUST emit no environment-dependent paths inside the output. STEP / BREP / `.FCStd` containers all have fields where a user-name or absolute-path can leak — the module MUST scrub or fix-value these fields.
- **FR-005**: Topology output ordering MUST be deterministic. Where a format permits multiple valid orderings of edges / faces / triangles, the writer MUST pick a canonical ordering (sorted by a deterministic key) and emit it the same way every time.
- **FR-006**: Each writer MUST validate its inputs (source object non-null, source has a Shape, target path has the expected extension, parent directory exists) BEFORE attempting any FreeCAD or filesystem operation, and MUST raise a typed `ExportInputError` (subclassing `ValueError`) on validation failure.
- **FR-007**: Each writer MUST raise a typed `ExportWriteError` (subclassing `RuntimeError`) on filesystem or FreeCAD-side write failure, wrapping the underlying exception. Both exception classes are part of the public module API.
- **FR-008**: Writes MUST be atomic in the user-visible sense: a write that fails mid-stream MUST NOT leave a partial file at the target path. The expected technique is "write to a sibling temporary file in the same parent directory as the target, then rename to the target path on success". If the rename fails for any reason (including the cross-filesystem case where `os.replace()` raises), the writer MUST clean up the temporary file and raise `ExportWriteError` naming the cause — it MUST NOT fall back to a copy+delete because that loses the atomicity guarantee.
- **FR-009**: Each writer MUST accept an optional `overwrite: bool = True` keyword argument. When `False`, the writer MUST refuse to overwrite an existing target and raise `ExportInputError`.
- **FR-010**: The STL writer MUST accept a documented `tessellation_tolerance` keyword argument (a positive float in meters of absolute linear chord deviation, NOT relative to the bounding box). Default: `0.001` (1 mm). Tighter values produce more triangles; the default is balanced for both 3D printing and render preview. The tolerance is the only knob that changes STL output for a given Body — same Body + same tolerance = identical bytes.
- **FR-011**: The STL writer MUST emit binary STL, not ASCII STL. Binary STL is smaller, faster to read, and easier to make byte-deterministic (ASCII STL inherits the same line-ending and float-formatting risks as STEP/BREP without the benefit of compactness).
- **FR-012**: The STL writer is the **only** writer permitted to invoke FreeCAD's mesh APIs (`Mesh.Mesh`, `MeshPart.meshFromShape`, etc.). The constitution III "no raw mesh" rule applies to every other writer in this module.
- **FR-013**: The export module MUST NOT import any other PUBLIC storebro module (`hull`, `deck`, `interior`, `cli`). It operates on FreeCAD types only, not on storebro-public types. Shared INTERNAL helpers (underscore-prefixed modules like `storebro._freecad_check`) are explicitly permitted because they live below the public-module surface and exist precisely to be shared across feature modules. (The rule keeps the public dependency arrow clean: hull → export, not the other way around — while still allowing the project to share leaf-level infrastructure.)
- **FR-014**: The export module MUST work with the FreeCAD version range declared in `pyproject.toml` per constitution principle VII. The same lazy-first-call pattern from spec 001 (FR-013) applies: importing `storebro.export` MUST NOT trigger any FreeCAD check; the check fires on the first writer invocation.
- **FR-015**: All public writer functions MUST have a one-line docstring with at least one runnable usage example, per the project's DX guidance.
- **FR-016**: For text-based formats (STEP, BREP), the writer MUST emit LF line endings on every supported operating system. CRLF leakage would break byte-identical reproducibility across Ubuntu and macOS CI runners.
- **FR-017**: The STEP writer MUST emit conforming **AP214 (ISO 10303-214)** files — FreeCAD's default schema, broadest interchange compatibility. AP203 and AP242 are out of scope for v1.0; v1.1+ may add them behind an explicit `schema` kwarg.
- **FR-018**: The STEP and BREP writers MUST populate the format's "creator", "originator", "author" header fields with the fixed sentinel string `"freecad-storebro"` (project name only, NO version suffix). The unsuffixed sentinel keeps byte determinism stable across PATCH bumps; revising it is reserved for semver MAJOR.
- **FR-019**: When multiple subshapes share an ambiguous ordering inside a format (face list, edge list, triangle list, Compound children), the writer MUST sort them by their geometric centroid in `(x, y, z)` lexicographic order, with the FreeCAD-internal `ShapeType` (`Vertex` < `Edge` < `Wire` < `Face` < `Shell` < `Solid` < `Compound`) as a tie-breaker. The sort MUST apply recursively into Compound children — at every nesting level, siblings are reordered by centroid before the format emits them. Centroid-based sorting is invariant under FreeCAD-internal element reshuffling and stable across the supported FreeCAD version range.
- **FR-020**: The `.FCStd` writer MUST achieve byte-identical reproducibility by post-processing the FreeCAD-saved `.FCStd` zip: rewrite all zip-entry timestamps to a fixed epoch (`1980-01-01T00:00:00Z`, the lowest value the zip format permits), scrub `<Document>`-level `CreationDate`, `LastModifiedDate`, `CreatedBy`, and `LastModifiedBy` XML elements to fixed sentinel values, and re-pack the zip with entries in deterministic alphabetical order. The byte-identical SHA-256 baseline is pinned per FreeCAD version (a FreeCAD-version bump may invalidate it; PATCH bump + CHANGELOG note covers that case per constitution VII).

### Key Entities

- **ExportRequest**: The named inputs to a writer — the source object (Body or document), the target path, and format-specific options (`overwrite`, `tessellation_tolerance` for STL). Conceptual entity; may be implemented as keyword arguments or a dataclass per `/speckit-plan`.
- **ExportArtifact**: The file produced by a writer. Carries a documented SHA-256 fingerprint that the test suite uses as a regression gate. Lives at the target path; the writer returns enough metadata for the caller to verify success (resolved absolute path, byte count, SHA-256).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For each of the four supported formats, two back-to-back writes of the same input on the same FreeCAD version produce SHA-256-identical files. STEP uses AP214 (FR-017), STL uses the documented default `tessellation_tolerance = 0.001` (FR-010), all writers use the centroid sort key (FR-019) and the `"freecad-storebro"` creator sentinel (FR-018), and the `.FCStd` writer applies the zip-scrub procedure (FR-020). This is the constitutional principle II checkpoint and a P0 invariant.
- **SC-002**: Default-hull export to STEP completes in under 5 seconds on a developer laptop. STL with default tessellation completes in under 10 seconds. `.FCStd` and BREP in under 3 seconds each. (Wall-clock budgets; users tolerate seconds, not minutes.)
- **SC-003**: A STEP file produced by this module opens cleanly in at least one mainstream non-FreeCAD CAD tool (FreeCAD's own viewer counts as a fallback baseline) without geometry corruption — verified manually and recorded in the PR description.
- **SC-004**: A `.FCStd` file produced by this module opens cleanly in the FreeCAD GUI on every supported FreeCAD version with the parametric history intact (Body, sketches, loft, mirror, fusion all editable) — verified manually and recorded in the PR description per constitution V.
- **SC-005**: Every public writer function has at least one unit test (validation, path handling, exception coverage) AND at least one geometry-integration test (actually invokes FreeCAD, writes the file, validates the bytes). SC-006 from spec 001 generalized to this module.
- **SC-006**: At least 5 distinct invalid-input test cases exist (missing path, wrong extension, non-existent parent directory, target is a directory, empty Body) and each raises `ExportInputError` with a message that names the offending input.
- **SC-007**: At least 1 forced-failure test exists for each writer that confirms `ExportWriteError` wrapping when the underlying FreeCAD or filesystem call raises.
- **SC-008**: STL files produced at the default tessellation pass a watertight-mesh check (every edge shared by exactly two triangles) for any well-formed hull input.

## Assumptions

- **Scope of "export"**: write only, no read-back. The module produces files but does not parse them. A separate future spec could add `import_step`/`import_stl` if there's demand.
- **Format support**: exactly four formats in v1.0 — `.FCStd`, STEP (AP214 schema only — see FR-017), STL (binary, per FR-011), BREP. No DXF, no IGES, no glTF, no OBJ. No STEP AP203 or AP242. Those join in v1.1+ if demand exists.
- **Single-object exports**: each writer call handles ONE source object. Multi-body exports are out of scope; callers compose multiple writer calls themselves.
- **No compression**: STEP / BREP are text; STL is binary. None are compressed by this module. Adding gzipped variants is out of scope for v1.0.
- **FreeCAD runtime**: FreeCAD 1.1+ Python API available. The module sits behind the same lazy first-call version check pattern as spec 001's hull module.
- **Filesystem semantics**: POSIX-ish — atomic rename inside the same filesystem is assumed available. Windows is out of scope for v1.0 (the project's CI matrix targets Ubuntu + macOS).
- **Reproducibility scope**: byte-identical for fixed (source object, target path, writer kwargs, FreeCAD version) tuple. A FreeCAD-version-bump can change the bytes and that is acceptable per constitution VII — versioned hash baselines, not eternal hashes.
- **Caller owns the source object lifetime**: the writer reads from the source object but does not modify it, does not extend its lifetime, and does not close the source document. Cleanup of the source is the caller's job.
- **Path-type API**: writers accept either `str` or `pathlib.Path` for the target. Internally everything is `pathlib.Path`. No `os.PathLike` magic beyond what `pathlib.Path()` already accepts.
- **No telemetry, no logging in v1.0**: same as spec 001 clarify Q4 — errors are exceptions, success returns the artifact metadata.
- **Test environment**: pytest with two tiers (unit for path/extension/validation logic, geometry for actual file writes); SHA-256 fingerprints pinned in test fixtures and updated only when a deliberate format-impacting change happens (PATCH bump + CHANGELOG note).
