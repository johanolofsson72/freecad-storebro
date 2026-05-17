# Contract: `storebro.export` Public Python API

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Date**: 2026-05-17

Public API contract for the export module. Governed by semantic versioning (constitution VI): breaking changes require a MAJOR bump and a documented migration path.

---

## Module path

```python
import storebro.export
# or, re-exported from the package root:
from storebro import (
    export_step, export_stl, export_brep, export_fcstd,
    ExportArtifact, ExportInputError, ExportWriteError,
)
```

`storebro.export.__all__`:

```python
__all__ = [
    "export_brep",
    "export_fcstd",
    "export_step",
    "export_stl",
    "ExportArtifact",
    "ExportInputError",
    "ExportWriteError",
]
```

---

## Function: `export_step`

```python
def export_step(
    body: "FreeCAD.DocumentObject",
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
) -> ExportArtifact:
    """Write a FreeCAD Body to an AP214 STEP file.

    Args:
        body: A FreeCAD object with a non-empty `.Shape` attribute (typically
            a Part::Body, but any Shape-bearing object works).
        target_path: Destination file path. Must end in `.step` or `.stp`.
            Parent directory must already exist.
        overwrite: If False, raises ExportInputError when target exists.

    Returns:
        ExportArtifact with the SHA-256 of the produced bytes.

    Raises:
        ExportInputError: Invalid path, wrong extension, parent dir missing,
            empty body, or target exists with overwrite=False.
        ExportWriteError: FreeCAD version unsupported, FreeCAD raises during
            export, or atomic rename fails.

    Example:
        >>> from storebro import build_hull, export_step
        >>> hull = build_hull()
        >>> art = export_step(hull.body, "/tmp/boat.step")
        >>> len(art.sha256) == 64  # SHA-256 hex digest  # doctest: +SKIP
        True
    """
```

### Contract guarantees

1. **AP214 schema.** Output STEP files conform to ISO 10303-214.
2. **Header sentinel.** The STEP HEADER `FILE_NAME` and `FILE_DESCRIPTION` lines contain `"freecad-storebro"` (no version) and a fixed-epoch timestamp (FR-003, FR-018).
3. **LF line endings.** No CRLF, regardless of OS (FR-016).
4. **Byte-identical reproducibility.** Two calls with the same `body`/`target_path`/`overwrite`/FreeCAD-version produce SHA-256-identical files.
5. **Atomicity.** A failed write leaves no partial file at `target_path`.

---

## Function: `export_stl`

```python
def export_stl(
    body: "FreeCAD.DocumentObject",
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
    tessellation_tolerance: float = 0.001,
) -> ExportArtifact:
    """Write a FreeCAD Body to a binary STL file.

    Args:
        body: A FreeCAD object with a non-empty `.Shape` attribute.
        target_path: Destination file path. Must end in `.stl`.
        overwrite: If False, raises ExportInputError when target exists.
        tessellation_tolerance: Absolute linear chord deviation, in meters.
            Default 0.001 m (1 mm). Must be > 0. Tighter values produce
            more triangles.

    Returns:
        ExportArtifact with the SHA-256 of the produced bytes.

    Raises:
        ExportInputError: Invalid path, wrong extension, parent dir missing,
            empty body, non-positive tessellation_tolerance, or target
            exists with overwrite=False.
        ExportWriteError: FreeCAD version unsupported, mesh build fails to
            produce a watertight mesh, FreeCAD raises during export, or
            atomic rename fails.

    Example:
        >>> from storebro import build_hull, export_stl
        >>> hull = build_hull()
        >>> art = export_stl(hull.body, "/tmp/boat.stl", tessellation_tolerance=0.0005)
        >>> art.byte_count > 0  # doctest: +SKIP
        True
    """
```

### Contract guarantees

1. **Binary STL only** (FR-011). No ASCII STL output.
2. **STL is the only mesh emitter.** No other writer in this module produces mesh data (FR-012).
3. **Watertight mesh** for any well-formed closed-shell input (SC-008). If the mesh fails the watertight check, the writer raises `ExportWriteError` rather than producing a non-watertight file.
4. **Byte-identical reproducibility** for the same `(body, tessellation_tolerance, FreeCAD-version)` tuple.

---

## Function: `export_brep`

```python
def export_brep(
    body: "FreeCAD.DocumentObject",
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
) -> ExportArtifact:
    """Write a FreeCAD Body to an OpenCASCADE BREP file.

    Args:
        body: A FreeCAD object with a non-empty `.Shape` attribute.
        target_path: Destination file path. Must end in `.brep` or `.brp`.
        overwrite: If False, raises ExportInputError when target exists.

    Returns:
        ExportArtifact with the SHA-256 of the produced bytes.

    Example:
        >>> from storebro import build_hull, export_brep
        >>> hull = build_hull()
        >>> art = export_brep(hull.body, "/tmp/boat.brep")  # doctest: +SKIP
        >>> art.format
        'brep'
    """
```

### Contract guarantees

1. **OpenCASCADE BREP format** via FreeCAD's native `Shape.exportBrep`.
2. **Originator sentinel.** Any header `Originator`/`Creator` comments contain `"freecad-storebro"` (FR-018).
3. **LF line endings.** No CRLF (FR-016).
4. **Byte-identical reproducibility** for the same `(body, FreeCAD-version)` tuple.

---

## Function: `export_fcstd`

```python
def export_fcstd(
    document: "FreeCAD.Document",
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
) -> ExportArtifact:
    """Write a FreeCAD Document to a deterministic .FCStd archive.

    Args:
        document: An open FreeCAD Document. Will be recomputed before save.
        target_path: Destination file path. Must end in `.FCStd` or `.fcstd`.
        overwrite: If False, raises ExportInputError when target exists.

    Returns:
        ExportArtifact with the SHA-256 of the produced bytes.

    Example:
        >>> from storebro import build_hull, export_fcstd
        >>> hull = build_hull()
        >>> art = export_fcstd(hull.document, "/tmp/boat.FCStd")  # doctest: +SKIP
        >>> art.format
        'fcstd'
    """
```

### Contract guarantees

1. **Reopens cleanly** in the FreeCAD GUI on every supported FreeCAD version, with full parametric history intact (SC-004).
2. **Byte-identical reproducibility** via the zip-scrub procedure (FR-020 + research R4): fixed-epoch zip-entry timestamps, sentinel `<Document>` XML metadata, alphabetical entry order, `ZIP_STORED` compression (no DEFLATE).
3. **No user/host metadata leak** (FR-004): `CreatedBy` and `LastModifiedBy` are scrubbed to `"freecad-storebro"`.

---

## Class: `ExportArtifact`

```python
@dataclass(frozen=True)
class ExportArtifact:
    target_path: pathlib.Path     # Absolute path of the written file
    format: str                   # One of "fcstd", "step", "stl", "brep"
    byte_count: int               # Size of the file in bytes
    sha256: str                   # SHA-256 hex digest, lower-case, 64 chars
    build_duration_seconds: float
```

Frozen, hashable, value-equal. `format` is always one of the four lower-case strings.

---

## Exceptions

### `ExportInputError(ValueError)`

```python
class ExportInputError(ValueError):
    field: str
    reason: str
    offending_value: str | None

    def __init__(self, field: str, reason: str, offending_value: str | None = None): ...
```

Raised before any filesystem or FreeCAD operation when an input is invalid.

### `ExportWriteError(RuntimeError)`

```python
class ExportWriteError(RuntimeError):
    target_path: pathlib.Path | None
    underlying_message: str
    format: str | None
    detected_version: tuple[int, int] | None
    supported_range: str | None

    def __init__(self, message: str, *,
                 target_path: pathlib.Path | None = None,
                 underlying: BaseException | None = None,
                 format: str | None = None,
                 detected_version: tuple[int, int] | None = None,
                 supported_range: str | None = None): ...
```

Raised when FreeCAD or the filesystem fails mid-write, or when the FreeCAD version is unsupported.

---

## Versioning

- **PATCH**: bug fixes, internal refactor, scrub-procedure improvements that don't change the public API, FreeCAD-version-range expansion, new entries in `tests/geometry/fixtures/expected_hashes.toml`.
- **MINOR**: new optional kwargs (additive only), new optional fields on `ExportArtifact`, new exception attributes, new supported formats (DXF, IGES, etc.).
- **MAJOR**: removing a public name, changing a default kwarg value, changing the STEP schema default, changing the STL binary/ASCII default, changing the creator sentinel string.

---

## Out of scope (NOT part of this contract)

- `_resolve_target_path`, `_sorted_subshapes`, `_scrub_fcstd_zip`, `_atomic_write`, `_canonicalize_step_header`, and every other underscore-prefixed name are private.
- The exact regex patterns used to scrub STEP / BREP headers are private and may change in PATCH bumps.
- The exact zip-entry order inside `.FCStd` files is contractually "alphabetical by entry name" but the alphabetization rules (locale, case sensitivity) are private and may be refined.
- Reading exported files back (`import_step`, etc.) is out of scope for v1.0.
- Compressed variants (`.FCStd.gz`, gzipped STL, etc.) are out of scope for v1.0.
