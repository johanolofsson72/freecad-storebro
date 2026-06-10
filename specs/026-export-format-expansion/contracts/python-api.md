# Public API Contract Delta: Export Format Expansion

Library; the contract is the public Python export API + the CLI. Spec 026 is additive (MINOR, 1.12.0 → 1.13.0). The shipped-format set is finalized by the T001 spike (glTF deferred; DXF spike-gated).

## Unchanged (back-compat guarantee)

- `export_step`, `export_brep`, `export_stl`, `export_fcstd` — existing call sites (single body / document, no gzip) behave exactly as before and produce **byte-identical** output to spec 002 (SC-005).
- `ExportArtifact`, `ExportInputError`, `ExportWriteError` — unchanged.

## Added — function parameters (additive, defaulted)

- `export_step/brep/stl(body_or_bodies, ...)` — the first parameter now also accepts an **iterable of bodies** (assembly); a single body is unchanged.
- `gzip: bool = False` on `export_step/brep/stl/fcstd` (and the new functions) — deterministic gzip when true; target path must end `.gz`.

## Added — functions

- `export_obj(body_or_bodies, target_path, *, overwrite=True, tessellation_tolerance=0.001, gzip=False) -> ExportArtifact` — Wavefront OBJ from the canonical mesh.
- `export_iges(body_or_bodies, target_path, *, overwrite=True, gzip=False) -> ExportArtifact` — IGES B-rep (global-section scrubbed).
- `export_dxf_profile(body_or_bodies, target_path, *, plane="xz", overwrite=True, gzip=False) -> ExportArtifact` — 2D profile DXF (hand-written R12 ASCII). **Ships only if the spike confirms determinism.**
- All exported from `storebro` and added to `export.__all__`.

## Deferred (not shipped this spec)

- **glTF** — the only headless exporter path is unavailable in console/CI FreeCAD; deferred (research.md R1).
- Full-assembly-in-FCStd — FCStd already serializes the whole document.

## Behavior contract

- **Assembly**: passing >1 body combines them into one compound (B-rep) / merged canonical mesh (mesh), ordered deterministically; the output reflects every body (SC-001).
- **Single body**: byte-identical to spec 002 (SC-005).
- **gzip**: the `.gz` output's decompressed bytes equal the un-gzipped export; two gz are byte-identical (SC-004).
- **Determinism**: two identical exports of any shipped format have equal SHA-256 (SC-003).
- **Validation**: wrong extension / `.gz`-without-gzip / empty bodies / degenerate DXF → `ExportInputError`/`ExportWriteError` (SC-007).

## Added — CLI

- `storebro build --format {fcstd,step,stl,brep,obj,iges[,dxf]}` — new shipped formats added.
- `storebro build --gzip` — gzip the chosen format (path gains `.gz`).
- The CLI exports the **full assembly** (hull + deck + interior + propulsion) by default for the multi-body formats (was hull-only).
