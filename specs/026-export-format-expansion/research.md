# Phase 0 Research: Export Format Expansion

All NEEDS CLARIFICATION were resolved in `/clarify`. This records the export-API/reproducibility decisions that gate implementation.

## R1 — Headless exporter availability (capability probe)

**Decision**: Use only headless-available FreeCAD APIs. Probe result (FreeCAD 1.1.1, console, `/tmp` probe):

| Path | Headless? | Use |
|---|---|---|
| `Shape.exportIges(path)` | ✅ available | IGES (B-rep) |
| `Mesh.Mesh.write(path)` (.obj) | ✅ available | OBJ (mesh) |
| `Part.Compound([...])` | ✅ | assembly (B-rep) |
| `MeshPart.meshFromShape` + merge | ✅ | assembly (mesh) |
| `gzip.compress(data, mtime=0)` | ✅ (stdlib) | gzip |
| `importGltf` (GUI workbench) | ❌ ModuleNotFoundError | glTF → DEFER |
| `importDXF` (GUI workbench) | ❌ ModuleNotFoundError | DXF → hand-write ASCII |

**Rationale**: The deploy + CI path is headless (constitution VII / the GitHub-Actions deploy job runs console FreeCAD). A format that needs the GUI exporter cannot be produced in CI, so it cannot be a shipped, tested format. glTF's only exporter is the GUI `importGltf` module → **deferred**. DXF's `importDXF` is GUI-only too, but DXF is plain ASCII text, so a minimal R12 DXF can be hand-written from `Part`-projected edges with no GUI module — and hand-writing gives full byte control (trivially deterministic).

**Alternatives**: Hand-write glTF (JSON + base64/GLB buffers) from the canonical mesh (rejected — large, disproportionate to value; deferred is cleaner). Require a GUI FreeCAD session for glTF (rejected — breaks headless CI + reproducibility testing).

## R2 — Per-format byte-reproducibility (the spike, T001, FR-007)

**Decision**: Reuse the spec 002 determinism machinery and prove each candidate byte-identical before shipping:
- **OBJ**: `_build_canonical_mesh` (spec 002 — canonical facet order) → `Mesh.write(.obj)`. Scrub any leading comment header (FreeCAD may emit a version/date comment) the way `_canonicalize_step_header`/`_canonicalize_brep_header` scrub theirs.
- **IGES**: `Shape.exportIges` on the combined compound. The IGES *global section* carries a timestamp + the file name → scrub it (adapt the STEP header canonicalizer). The B-rep section is geometry-deterministic given the sorted compound.
- **Assembly (B-rep)**: `Part.Compound` of the bodies' shapes, ordered by the spec 002 `_sorted_subshapes` so compound order is stable regardless of body-construction order.
- **Assembly (mesh)**: merge per-body canonical meshes in the same sorted order; re-canonicalize facet order on the merged mesh.
- **DXF**: hand-written R12 ASCII from projected edges, sorted deterministically — no timestamp, no handles (R12 ASCII needs none) → deterministic by construction.
- **gzip**: `gzip.compress(data, mtime=0)` (no filename) → deterministic.

**Spike result (T001, `/tmp/spike_026_repro.py`, FreeCAD 1.1.1 console, 2026-06-10):**
```
[x] OBJ (Mesh.write .obj)            raw bytes identical ×2 (header is a STATIC URL
                                     "# Created by FreeCAD <...>", no timestamp)        -> SHIP
[x] IGES (Shape.exportIges)          B-rep deterministic, BUT global section carries a
                                     date token (e.g. 20260610.204357) -> MUST scrub
                                     `\d{8}\.\d{6}` -> fixed; SHIP with date scrub        -> SHIP
[x] assembly compound STEP           byte-identical ×2 with the real
                                     `_canonicalize_step_header` (9a1476b6...)            -> SHIP
[x] assembly compound BREP           byte-identical ×2 with `_canonicalize_brep_header`
                                     (082f3d8c...)                                        -> SHIP
[x] assembly merged mesh (STL/OBJ)   raw identical ×2; bbox spans all bodies (24 facets) -> SHIP
[x] DXF hand-written R12 ASCII       raw identical ×2; 16 projected segments, no
                                     timestamp/handles -> deterministic by construction   -> SHIP
[x] gzip (mtime=0)                   identical ×2; gunzip == raw                          -> SHIP
[x] glTF                             importGltf ModuleNotFoundError (GUI-only) headless   -> DEFER
```
**Conclusion**: ships = assembly (STEP/STL/BREP), OBJ, IGES (with the date scrub), DXF, gzip. Deferred = glTF (headless-unavailable). The IGES date scrub is the one new scrubber needed; STEP/BREP reuse the existing canonicalizers; OBJ/DXF/gzip are deterministic by construction.

**Rationale**: FR-007 — a format ships on-by-default only if proven byte-identical. The spec 002 scrub patterns are the proven tools; the spike confirms each new format reaches byte-identity (or is deferred).

## R3 — Assembly API shape (clarify Q2)

**Decision**: Each export function accepts `body_or_bodies: Body | Iterable[Body]`. A single `Body` → its `.Shape` used directly (byte-identical to spec 002 — no compound). An iterable → `_combine_bodies` builds a `Part.Compound` (B-rep) or a merged canonical mesh (mesh), ordered by `_sorted_subshapes`. The existing `export_step/stl/brep` signatures already take a single body; widening the parameter to also accept an iterable is additive and back-compatible.

**Rationale**: clarify Q2 — one entry point per format, single-body byte-identical, assembly opt-in by passing a list. Avoids a parallel `export_assembly_*` surface.

**Alternatives**: Separate `export_assembly_step(...)` functions (rejected — doubles the surface). A generic `export(model, fmt, ...)` dispatcher (rejected — the per-format functions are the established public API; a dispatcher can wrap them in the CLI).

## R4 — gzip (clarify Q5)

**Decision**: A `gzip: bool = False` kwarg on each export function. When true, the final bytes are `gzip.compress(bytes, mtime=0)` (Python stdlib, mtime zeroed, no embedded filename) and the target path must end in `.gz`. The decompressed bytes equal the un-gzipped export (a unit test gunzips and compares).

**Rationale**: clarify Q5 — orthogonal, deterministic, composes with every format by wrapping the bytes before the atomic write. mtime=0 is the one knob needed for gzip determinism.

## R5 — DXF 2D profile (clarify Q4)

**Decision**: Project the combined shape's edges onto the X-Z plane (drop Y), collect the projected line segments, sort them deterministically (by endpoint tuple), and hand-write a minimal AutoCAD R12 ASCII DXF (HEADER + ENTITIES with `LINE` entities). No timestamp, no handles (R12 ASCII does not require them) → deterministic by construction. A degenerate projection (no edges) raises `ExportWriteError`. The projection plane is a parameter defaulting to `xz`.

**Rationale**: clarify Q4 — the side/profile silhouette is what the reference photos show. Hand-writing R12 ASCII sidesteps the GUI `importDXF` module and gives full byte control (the surest path to determinism). Spike-gated: ship only if the spike confirms clean byte-identity (it should, by construction).

**Alternatives**: GUI `importDXF.export` (rejected — unavailable headless). TechDraw projection (rejected — heavier, GUI-oriented). Full HLR hidden-line removal (deferred — a silhouette of projected edges is sufficient for a profile).

## R6 — Backward compatibility & versioning

**Decision**: `export_step/stl/brep/fcstd` keep their signatures (the `body` param just also accepts an iterable; `gzip` is an additive defaulted kwarg). New functions `export_obj`, `export_iges`, (`export_dxf_profile`) are additive. CLI gains `--gzip` + new `--format` choices and exports the full assembly by default for multi-body formats. → additive surface → **MINOR** bump 1.12.0 → **1.13.0**.

**Rationale**: Constitution VI semver. Single-body exports stay byte-identical (SC-005); the CLI full-assembly default fixes a real bug (today's hull-only drop) and is covered by the updated flag-baseline test.
