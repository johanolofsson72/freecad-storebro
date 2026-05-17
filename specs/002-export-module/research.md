# Research: Export Module (Phase 0)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-17

Resolves the unknowns identified during planning. Each section uses the `Decision / Rationale / Alternatives` format.

---

## R1. STEP writer — backend API + AP214 schema handling

### Decision

Use `Part.export([shape], target_path)` (FreeCAD's high-level Part-workbench exporter) with the AP214 schema chosen via the FreeCAD preference `User parameter:BaseApp/Preferences/Mod/Import/hSTEP/Scheme`. The preference is set to `"AP214"` once at module load via FreeCAD's `Preferences` API; the setting is read-only-effective at export time and does not persist outside the FreeCAD session.

After `Part.export()` writes the file, the writer post-processes the bytes in memory: regex-replace the timestamp line in the STEP HEADER section (`FILE_NAME` field has an ISO timestamp) and the originating-system line (`/* */` comment with the username) with the project's sentinel string. Then write the canonical bytes to the target via the atomic-rename discipline.

### Rationale

- `Part.export()` is FreeCAD's documented high-level STEP exporter; it handles compound shapes, units, and the schema preference correctly across the 1.1+ range.
- Setting the schema via the in-memory FreeCAD preference (not by writing the user's `~/.FreeCAD/user.cfg`) means the writer is side-effect-free outside the process. Multiple processes can each set their own schema preference without races.
- Post-processing the bytes in memory keeps the timestamp scrub deterministic — FreeCAD writes a STEP file, we patch the header lines, we write the result to disk. No "monkey-patch FreeCAD's STEP writer" hacks.

### Alternatives considered

- **`Shape.exportStep(path)`** (lower-level): rejected because it doesn't respect the schema preference and forces AP203 by default in some FreeCAD versions. Less consistent.
- **External `step-tools` library**: rejected — adds a non-FreeCAD dependency for a problem FreeCAD already solves.
- **Write STEP from scratch in Python**: rejected — re-implementing STEP serialization is a multi-month project that buys nothing FreeCAD doesn't already give us.

### Determinism considerations

The STEP HEADER section is the only known timestamp-bearing field FreeCAD writes. Body content is deterministic given canonical subshape ordering (see R5). Post-processing regex pattern:

```
/^FILE_NAME\s*\(.+\)/m  → FILE_NAME (... fixed sentinel ...)
/^FILE_DESCRIPTION\s*\(.+\)/m  → FILE_DESCRIPTION (... fixed sentinel ...)
```

The exact regex set is finalized in the implementation phase; the spec-level commitment (FR-018) is that the producer field reads `"freecad-storebro"`.

---

## R2. STL writer — `Mesh.export` with controlled tessellation

### Decision

Use FreeCAD's `Mesh.export([mesh], target_path)` after building a `Mesh.Mesh` from the source Body via `MeshPart.meshFromShape(Shape=body.Shape, LinearDeflection=tolerance_meters * 1000.0, AngularDeflection=0.5)`.

`LinearDeflection` is FreeCAD's internal name for absolute linear chord deviation, in millimeters (FreeCAD's internal unit). The writer converts the public-API meters → internal millimeters.

`AngularDeflection` is a complementary tessellation knob (controls how aggressively curves are subdivided around tight bends). Fixed at `0.5` (radians, ≈ 28.6°) — coarse enough not to dominate tessellation count, fine enough that smooth hulls look smooth. NOT exposed as a public kwarg in v1.0; locked to keep the tessellation surface small.

STL output is binary (FR-011). `Mesh.export()` selects binary vs ASCII based on the file extension and a writer preference; binary is the default for `.stl`. We additionally pass a `Mesh.write` call with explicit `Mesh.Mesh.write(filename, "STL", "STLB")` formatter selector if needed to force binary in any FreeCAD version that defaulted to ASCII.

### Rationale

- `Mesh.export()` is the documented high-level STL writer in FreeCAD; it produces valid binary STL.
- `LinearDeflection` is the exact knob the spec needs — absolute chord deviation, not relative.
- Binary STL is reproducibility-friendlier than ASCII: no float-formatting locale issues, no line-ending issues, no whitespace ambiguity.

### Alternatives considered

- **Custom `Mesh.Mesh` triangulation followed by hand-rolled STL writer**: rejected — duplicates FreeCAD logic for no determinism gain; FreeCAD's binary STL output is already deterministic given fixed triangle ordering.
- **Use `Part.makeFacets()` to triangulate, then write triangles ourselves**: rejected for the same reason.
- **Expose `AngularDeflection` as a public kwarg**: rejected for v1.0 — adds a second knob that materially changes triangle count without measurable user benefit. Can be added in v1.1+ if demand emerges (deferred).

### Determinism considerations

`Mesh.export()` writes triangle list in the same order as `Mesh.Mesh.Topology.Facets`. To ensure that order is deterministic across FreeCAD-internal element reshuffling, the writer sorts the source `Mesh.Mesh` facets by their centroid (FR-019 applied to triangles) before writing. The sort is in-place on a copy; the caller's Body is not mutated.

Watertight check (SC-008) uses `Mesh.Mesh.isSolid()` plus `Mesh.Mesh.hasNonManifolds()`/`hasSelfIntersections()` from FreeCAD's Mesh module. If any of these report a non-watertight result, the writer raises `ExportWriteError` (mesh build failed to honor the source's closed-shell topology — usually due to tolerance interaction).

---

## R3. BREP writer — direct `Shape.exportBrep(path)`

### Decision

`shape.exportBrep(path)` is FreeCAD's native BREP writer. BREP is OpenCASCADE's binary-text hybrid format; FreeCAD's serializer is already deterministic for a fixed shape topology in the supported FreeCAD version range.

The writer applies the recursive centroid sort (FR-019) to the shape before calling `exportBrep` to ensure subshape ordering is canonical. After write, the writer reads the file back, regex-normalizes any `Originator` / `Creator` comment lines to the project sentinel, and re-writes via atomic rename.

### Rationale

- `exportBrep` is the canonical OpenCASCADE BREP serializer and is what every BREP-consuming tool expects.
- BREP is dense; rewriting it ourselves is impractical and would lose round-trip fidelity with FreeCAD.

### Alternatives considered

- **OpenCASCADE direct `BRepTools::Write`** via PythonOCC: rejected — adds a non-FreeCAD dependency and FreeCAD's wrapper already calls into the same OpenCASCADE function.
- **Skip BREP altogether**: rejected — BREP is the most-faithful FreeCAD-to-FreeCAD interchange format; restorers archiving their work expect it alongside STEP.

### Determinism considerations

OpenCASCADE's BREP writer is deterministic for fixed input. The only nondeterminism risk is (a) the order subshapes appear inside Compounds — addressed by FR-019 — and (b) the originator comment — addressed by the post-processing scrub.

---

## R4. `.FCStd` writer — zip post-processing scrub

### Decision

Three-step procedure:

1. **`Document.saveAs(tmp_path)`** — let FreeCAD serialize the document normally into a temp `.FCStd` file (which is a zip containing XML + binary BREP entries).
2. **In-process scrub**: read the temp zip into memory via `zipfile.ZipFile(io.BytesIO(...), "r")`, then:
   - For each zip entry, rewrite `date_time = (1980, 1, 1, 0, 0, 0)` (the lowest value the DOS time format supports inside zip).
   - For the `Document.xml` entry, parse the XML, replace `CreationDate`, `LastModifiedDate`, `CreatedBy`, `LastModifiedBy` element text with the configured sentinel values from spec.allium config (`"1980-01-01T00:00:00Z"` for dates, `"freecad-storebro"` for user fields), then serialize back deterministically (sort attributes, fixed indent, LF line endings).
   - Re-pack the zip in alphabetical order of entry names with `compression=zipfile.ZIP_STORED` (no compression) — `ZIP_DEFLATED` has version-of-zlib reproducibility risks; `ZIP_STORED` is bit-exact regardless of zlib version.
3. **Atomic rename** the canonicalized in-memory bytes to the target path.

### Rationale

- Letting FreeCAD do the heavy lifting (the document → zip serialization) preserves round-trip fidelity. Re-implementing that from scratch is a non-starter.
- The scrub touches only the parts of the zip that leak time/user/host info. Body geometry (the BREP entries inside the zip) is already deterministic per R3.
- `ZIP_STORED` trades file size for byte-determinism. A 100 KB `.FCStd` may grow to 300 KB without DEFLATE — acceptable for an archival format on a local disk.
- DOS-time epoch `1980-01-01` is the lowest legal value, making the choice unambiguous.

### Alternatives considered

- **Patch FreeCAD's `Document.save()` to write deterministic zips**: rejected — invasive, breaks across FreeCAD versions, would need maintainer-level changes upstream.
- **Use `ZIP_DEFLATED` with `mtime=0`**: rejected because DEFLATE output is not bit-exact across `zlib` versions (different Linux distros / macOS releases ship different `zlib`). `ZIP_STORED` removes the variable.
- **Drop `.FCStd` determinism for v0.1**: rejected (clarify Q3 chose best-effort scrub).

### Determinism considerations

The ordering of XML attributes matters. `xml.etree.ElementTree` does not guarantee attribute order; the writer uses `lxml` ... actually `lxml` is not on the dependency list. **Plan revision**: serialize XML via a small custom serializer that sorts attributes alphabetically before writing each tag. Stdlib-only, deterministic.

---

## R5. Recursive centroid sort (FR-019)

### Decision

Implement `_sorted_subshapes(shape)` recursively:

```python
def _sorted_subshapes(shape):
    """Return subshapes of `shape` sorted by (centroid.x, centroid.y, centroid.z, shape_type)."""
    children = list(shape.SubShapes)
    children.sort(key=lambda s: (
        s.CenterOfMass.x,
        s.CenterOfMass.y,
        s.CenterOfMass.z,
        _shape_type_rank(s.ShapeType),  # Vertex=1, Edge=2, ... Compound=7
    ))
    return [_recursively_sort(child) for child in children]
```

`_recursively_sort` returns the child with its own subshapes likewise sorted. The sort terminates at vertex-level leaves.

### Rationale

- Geometric centroid is invariant under FreeCAD-internal element reshuffling (the same edge always sits at the same centroid).
- `ShapeType` tiebreaker handles the edge case where two subshapes share the same centroid (e.g. coincident vertex/vertex from a degenerate construction).
- Recursive application means Compound children are also sorted, satisfying the OQ3 resolution.

### Alternatives considered

- **FreeCAD-internal index order**: rejected — index order changes when FreeCAD recomputes a feature, breaking determinism.
- **Hash of subshape geometry**: rejected — `Shape.hashCode()` is per-process and not stable across FreeCAD invocations.
- **Spatial Morton-code (Z-order curve)**: rejected — more complex, no determinism advantage over a plain lex sort.

### Determinism considerations

Floating-point centroid coordinates have a small risk of cross-FreeCAD-version drift (different optimizers, slightly different float results). For v0.1.0-alpha this risk is mitigated by pinning the FreeCAD version in the hash baseline. v0.2.0 may add a quantization step (`round(coord, 9)`) if real drift is observed.

---

## R6. SHA-256 baseline format + storage

### Decision

`tests/geometry/fixtures/expected_hashes.toml`:

```toml
# Hash baselines for export module geometry tests.
# Key format: "<format>__<freecad_version>__<source_hash>__<kwargs_hash>"
# - format: fcstd|step|stl|brep
# - freecad_version: "1.1.0" (major.minor.patch from FreeCAD.Version())
# - source_hash: SHA-256 of HullParameters.__repr__() for the source hull
# - kwargs_hash: SHA-256 of sorted writer kwargs (e.g. {"tessellation_tolerance": 0.001})

[step__1_1_0__abc123__def456]
sha256 = "..."

[stl__1_1_0__abc123__def456]
sha256 = "..."
# ...
```

Tests look up the expected hash by computing the key from the test inputs and the running FreeCAD version, then compare against the SHA-256 of the produced file. If the lookup misses, the test fails with a message instructing the maintainer to: (a) verify the geometry visually, (b) run `python tests/geometry/fixtures/refresh_hashes.py`, (c) commit the updated TOML with a PATCH bump and a CHANGELOG entry.

### Rationale

- TOML is human-readable, stdlib-parseable, version-controllable, and merge-friendlier than JSON for large tables.
- Keying by `(format, freecad_version, source_hash, kwargs_hash)` lets a single TOML file hold every baseline that has ever been valid; we never delete a baseline, we just add new rows when something changes.
- A FreeCAD-version bump becomes "add 4 rows" (one per format), not "rewrite every test".

### Alternatives considered

- **Inline hashes inside test code**: rejected — test files become brittle on every FreeCAD version bump.
- **Per-format separate hash files**: rejected — splits a small dataset across 4+ files for no benefit.

---

## R7. Atomic rename + cleanup (FR-008, OQ2 resolution)

### Decision

```python
def _atomic_write(target_path: Path, body_bytes: bytes) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=target_path.parent,                     # same parent → same filesystem
        prefix=f".{target_path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(body_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)            # atomic on same filesystem
    except OSError as exc:
        # Cross-filesystem rename, permission denied, disk full, etc.
        # Per spec OQ2 resolution: clean up + raise ExportWriteError. No fallback.
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise ExportWriteError(...) from exc
```

The `tempfile.mkstemp(dir=target_path.parent)` call places the temp file in the same parent directory, which is on the same filesystem in the common case. Cross-filesystem failures (where the target's parent is a bind mount or similar) raise `OSError` from `os.replace`, which the writer wraps in `ExportWriteError`.

### Rationale

- Atomic rename inside one filesystem is POSIX-guaranteed via `os.replace`.
- `fsync` before `os.replace` ensures the temp file's data is on disk before the rename — protects against power loss.
- No copy+delete fallback per OQ2 resolution: raise clearly so the user knows the atomicity guarantee is unavailable for their setup.

### Alternatives considered

- **`os.rename` instead of `os.replace`**: rejected — `os.rename` on Windows refuses to overwrite an existing target; `os.replace` is cross-platform and POSIX-equivalent on Unix.
- **Copy+delete fallback for cross-filesystem case**: rejected per OQ2.

---

## R8. Testing strategy

### Decision

Two-tier pytest layout matching spec 001's pattern, extended with hash-baseline regression tests:

- **Unit tier** (`tests/unit/test_export_*.py`):
  - `test_export_paths.py`: every path/extension/overwrite validation rule produces the documented `ExportInputError` shape (FR-006 + Edge Cases).
  - `test_export_errors.py`: exception class hierarchy, attribute shape, message format. Pure-Python.

- **Geometry tier** (`tests/geometry/test_export_*.py`):
  - `test_export_step.py`: build hull → `export_step` → SHA-256 matches baseline; STEP HEADER contains `"freecad-storebro"` and not the user's hostname.
  - `test_export_stl.py`: build hull → `export_stl` → SHA-256 matches baseline; mesh is watertight; tighter tolerance increases triangle count.
  - `test_export_brep.py`: build hull → `export_brep` → SHA-256 matches baseline.
  - `test_export_fcstd.py`: build hull → `export_fcstd` → SHA-256 matches baseline; reopen in FreeCAD round-trips the document tree.
  - `test_export_determinism.py`: parameterized over the four formats — two back-to-back writes produce identical bytes.
  - `test_export_atomicity.py`: monkey-patch FreeCAD's writer to raise mid-write; assert no partial file at the target path.
  - `test_export_leaf_module.py`: import-isolation check (FR-013), same pattern as spec 001's `test_hull_leaf_module.py`.

### Rationale

Mirrors the spec 001 testing convention. Every public function has at least one unit + geometry test (SC-005), at least 5 invalid-input cases in `test_export_paths.py` (SC-006), and one forced-failure test per writer (SC-007).

---

## Summary of decisions

| ID | Decision | Resolves |
|---|---|---|
| R1 | `Part.export()` + AP214 schema preference + STEP HEADER scrub | FR-017, FR-018 |
| R2 | `Mesh.export()` + `LinearDeflection`-driven tessellation + binary STL + facet centroid sort | FR-010, FR-011, FR-012 |
| R3 | `Shape.exportBrep()` + post-write originator scrub | FR-001 (BREP), FR-018 |
| R4 | `Document.saveAs` + zip-scrub (epoch timestamps + XML metadata fix-up + `ZIP_STORED` + alphabetical entry order) | FR-020, clarify Q3 |
| R5 | Recursive centroid + ShapeType lex sort | FR-005, FR-019, OQ3 |
| R6 | TOML hash-baseline storage keyed by (format, freecad_version, source_hash, kwargs_hash) | FR-002, SC-001, constitution VII |
| R7 | `os.replace` atomic rename + `fsync`; no cross-FS fallback (raise instead) | FR-008, OQ2 |
| R8 | Two-tier pytest with hash regression tests | SC-005, SC-006, SC-007, SC-008 |

All NEEDS CLARIFICATION markers resolved. Ready for Phase 1 design.
