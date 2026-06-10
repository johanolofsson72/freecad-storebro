# Phase 1 Data Model: Export Format Expansion

All types live in `src/storebro/export.py`. New functions/params are additive with defaults (back-compat). The shipped-format set is finalized by the T001 spike (glTF deferred; DXF spike-gated).

## Format / extension table

`_KNOWN_EXTENSIONS` (currently step/stl/brep/fcstd) gains:
```
"obj":  (".obj",),
"iges": (".iges", ".igs"),
"dxf":  (".dxf",),        # only if the spike ships DXF
```
A `.gz` suffix is accepted on top of any format's extension when `gzip=True` (e.g. `boat.stl.gz`, `boat.iges.gz`); validation checks the inner extension then the `.gz` suffix.

## Public functions

### Existing (signatures unchanged; `body` widened, `gzip` added)
```
export_step(body_or_bodies, target_path, *, overwrite=True, gzip=False) -> ExportArtifact
export_brep(body_or_bodies, target_path, *, overwrite=True, gzip=False) -> ExportArtifact
export_stl (body_or_bodies, target_path, *, overwrite=True, tessellation_tolerance=0.001, gzip=False) -> ExportArtifact
export_fcstd(document, target_path, *, overwrite=True, gzip=False) -> ExportArtifact
```
`body_or_bodies`: a single Body (byte-identical to spec 002) OR an iterable of Bodies (assembly → compound / merged mesh).

### New
```
export_obj (body_or_bodies, target_path, *, overwrite=True, tessellation_tolerance=0.001, gzip=False) -> ExportArtifact
export_iges(body_or_bodies, target_path, *, overwrite=True, gzip=False) -> ExportArtifact
export_dxf_profile(body_or_bodies, target_path, *, plane="xz", overwrite=True, gzip=False) -> ExportArtifact   # spike-gated
```

All return the spec 002 `ExportArtifact` (format, target_path, byte_count, sha256) and respect `overwrite` + atomic write.

## Internal helpers

| Helper | Role |
|---|---|
| `_combine_bodies(body_or_bodies) -> Shape` | 1 body → its `.Shape` (back-compat); N → `Part.Compound` ordered by `_sorted_subshapes`. |
| `_combine_meshes(body_or_bodies, tol) -> Mesh` | merge per-body canonical meshes (sorted order), re-canonicalize facet order. |
| `_maybe_gzip(data: bytes, enabled: bool) -> bytes` | `gzip.compress(data, mtime=0)` when enabled, else `data`. |
| `_canonicalize_iges_header(raw: bytes) -> bytes` | scrub the IGES global-section timestamp + filename (adapt `_canonicalize_step_header`). |
| `_scrub_obj_header(raw: bytes) -> bytes` | strip a nondeterministic leading comment line if `Mesh.write` emits one. |
| `_project_edges_xz(shape) -> list[segment]` | project edges onto X-Z, drop Y, sorted segments (for DXF). |
| `_write_r12_dxf(segments) -> bytes` | hand-written minimal R12 ASCII DXF (no timestamp/handles). |

`_combine_bodies`/`_combine_meshes` reuse `_sorted_subshapes` (spec 002) so the assembly order is deterministic regardless of body-construction order.

## Validation

- **Extension**: each format validates its target extension via the extended `_KNOWN_EXTENSIONS`; `gzip=True` requires a `.gz` suffix (`ExportInputError` otherwise).
- **Empty/invalid input**: an empty `body_or_bodies`, a body with no shape, or a degenerate DXF projection (no edges) raises `ExportInputError`/`ExportWriteError`.
- **Tessellation tolerance**: reuse the spec 002 `_resolve_tessellation_tolerance` for OBJ (same validation as STL).

## Determinism (constitution II)

- Mesh formats (STL, OBJ): canonical facet order via `_build_canonical_mesh`; assembly meshes merged in sorted order then re-canonicalized.
- B-rep formats (STEP, BREP, IGES): sorted compound via `_sorted_subshapes`; IGES global-section scrubbed.
- DXF: hand-written, sorted segments, no timestamp.
- gzip: `mtime=0`.
- Single body, no gzip → byte-identical to the spec 002 export (SC-005, dedicated test).

## Compatibility

- `_KNOWN_EXTENSIONS` widening + the `.gz` rule are additive.
- `body` → `body_or_bodies` widening + `gzip` kwarg are back-compat (single body unchanged).
- New functions exported from `storebro/__init__.py` + `export.__all__`.
- CLI: `--gzip` flag + new `--format` choices; full-assembly default for multi-body formats.
- Version 1.12.0 → 1.13.0.
