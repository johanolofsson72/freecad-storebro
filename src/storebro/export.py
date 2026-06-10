"""Deterministic exporters for FreeCAD bodies and documents.

Public surface:
    export_step       — write a Body to an AP214 STEP file
    export_stl        — write a Body to a binary STL file
    export_brep       — write a Body to an OpenCASCADE BREP file
    export_fcstd      — write a Document to a deterministic .FCStd archive
    ExportArtifact    — return-value dataclass
    ExportInputError  — pre-write validation failure
    ExportWriteError  — FreeCAD-side or filesystem failure

Constitutional principle II (Reproducibility, NON-NEGOTIABLE) is the central
invariant: for fixed (source object, target path, kwargs, FreeCAD version) the
output bytes are SHA-256-identical. Validation is documented in
`specs/002-export-module/`.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import math
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

__all__ = [
    "ExportArtifact",
    "ExportInputError",
    "ExportWriteError",
    "export_brep",
    "export_dxf_profile",
    "export_fcstd",
    "export_iges",
    "export_obj",
    "export_step",
    "export_stl",
]


# ---------------------------------------------------------------------------
# Exception classes (FR-007 + data-model §4 / §5)
# ---------------------------------------------------------------------------


class ExportInputError(ValueError):
    """Raised before any FreeCAD or filesystem call when an input is invalid.

    Attributes:
        field: The offending input name (e.g. ``"target_path"``, ``"body"``,
            ``"tessellation_tolerance"``).
        reason: Human-readable reason for the rejection.
        offending_value: ``repr`` of the offending value, or ``None`` when no
            single value can be cited.

    Example:
        >>> err = ExportInputError("target_path", "parent directory does not exist",
        ...                        "/no/such/dir/boat.step")
        >>> err.field
        'target_path'
        >>> isinstance(err, ValueError)
        True
    """

    def __init__(
        self,
        field: str,
        reason: str,
        offending_value: str | None = None,
    ) -> None:
        self.field = field
        self.reason = reason
        self.offending_value = offending_value
        if offending_value is None:
            message = f"ExportInputError: {field} — {reason}"
        else:
            message = f"ExportInputError: {field} — {reason} (got: {offending_value})"
        super().__init__(message)


class ExportWriteError(RuntimeError):
    """Raised when FreeCAD fails mid-write, when filesystem rename fails, or
    when the running FreeCAD version is outside the supported range.

    Attributes:
        target_path: Intended target file path, or ``None`` for version-check
            failures.
        underlying_message: ``str(underlying)`` of the wrapped exception.
        format: One of ``"step"``, ``"stl"``, ``"brep"``, ``"fcstd"`` — or
            ``None`` for version-check failures.
        detected_version: ``(major, minor)`` for version-check failures only.
        supported_range: Human-readable range for version-check failures only.

    Example:
        >>> err = ExportWriteError("disk full",
        ...                        target_path=Path("/tmp/x.step"),
        ...                        format="step")
        >>> err.format
        'step'
        >>> isinstance(err, RuntimeError)
        True
    """

    def __init__(
        self,
        message: str,
        *,
        target_path: Path | None = None,
        underlying: BaseException | None = None,
        format: str | None = None,
        detected_version: tuple[int, int] | None = None,
        supported_range: str | None = None,
    ) -> None:
        self.target_path = target_path
        self.underlying_message = "" if underlying is None else str(underlying)
        self.format = format
        self.detected_version = detected_version
        self.supported_range = supported_range
        super().__init__(f"ExportWriteError: {message}")


# ---------------------------------------------------------------------------
# Return aggregate (data-model §3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportArtifact:
    """Return value of every writer.

    Example:
        >>> # Returned by export_step / export_stl / export_brep / export_fcstd.
        >>> # art = export_step(body, "/tmp/boat.step")
        >>> # art.format, art.byte_count, art.sha256 all populated.
    """

    target_path: Path
    format: str
    byte_count: int
    sha256: str
    build_duration_seconds: float = field(default=0.0)


# ---------------------------------------------------------------------------
# Path / tessellation validation helpers (FR-006 + Edge Cases)
# ---------------------------------------------------------------------------


_KNOWN_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "step": (".step", ".stp"),
    "stl": (".stl",),
    "brep": (".brep", ".brp"),
    "fcstd": (".FCStd", ".fcstd"),
    # spec 026 — new formats (glTF deferred: GUI-only exporter unavailable headless).
    "obj": (".obj",),
    "iges": (".iges", ".igs"),
    "dxf": (".dxf",),
}


def _resolve_target_path(
    path: str | os.PathLike[str],
    format_key: str,
    overwrite: bool,
    gzip_enabled: bool = False,
) -> Path:
    """Validate and resolve the target path for a writer.

    spec 026: when ``gzip_enabled`` the path must end in ``.gz`` and the inner
    extension (before ``.gz``) must match the format; otherwise the path's own
    extension must match.

    Raises:
        ExportInputError: Path is empty, parent dir missing, target is a
            directory, extension does not match the writer's set, ``.gz``
            present/absent mismatching ``gzip_enabled``, or target exists with
            ``overwrite=False``.
    """
    if path is None or str(path) == "":
        raise ExportInputError("target_path", "must not be empty", repr(path))

    resolved = Path(path).expanduser().resolve()
    parent = resolved.parent
    if not parent.exists():
        raise ExportInputError(
            "target_path",
            "parent directory does not exist",
            str(parent),
        )
    if not parent.is_dir():
        raise ExportInputError(
            "target_path",
            "parent path is not a directory",
            str(parent),
        )
    if resolved.is_dir():
        raise ExportInputError(
            "target_path",
            "target is a directory, not a file",
            str(resolved),
        )

    expected = _KNOWN_EXTENSIONS[format_key]
    if gzip_enabled:
        if resolved.suffix != ".gz":
            raise ExportInputError(
                "target_path",
                "gzip=True requires a .gz suffix (e.g. boat.stl.gz)",
                resolved.suffix or "<no extension>",
            )
        inner_suffix = Path(resolved.stem).suffix
        if inner_suffix not in expected:
            raise ExportInputError(
                "target_path",
                f"inner extension must be one of {expected} for {format_key} before .gz",
                inner_suffix or "<no inner extension>",
            )
    else:
        if resolved.suffix == ".gz":
            raise ExportInputError(
                "target_path",
                "a .gz suffix requires gzip=True",
                ".gz",
            )
        if resolved.suffix not in expected:
            raise ExportInputError(
                "target_path",
                f"extension must be one of {expected} for {format_key}",
                resolved.suffix or "<no extension>",
            )

    if not overwrite and resolved.is_file():
        raise ExportInputError(
            "target_path",
            "target exists and overwrite=False",
            str(resolved),
        )

    return resolved


def _maybe_gzip(data: bytes, enabled: bool) -> bytes:
    """Deterministically gzip ``data`` when ``enabled`` (mtime 0, no filename)."""
    if not enabled:
        return data
    import gzip as _gzip

    return _gzip.compress(data, compresslevel=9, mtime=0)


def _as_body_list(body_or_bodies: Any) -> list[Any]:
    """Normalize a single body or an iterable of bodies to a non-empty list."""
    if hasattr(body_or_bodies, "Shape"):
        return [body_or_bodies]
    try:
        bodies = list(body_or_bodies)
    except TypeError as exc:
        raise ExportInputError(
            "body", "must be a body or an iterable of bodies", repr(body_or_bodies)
        ) from exc
    if not bodies:
        raise ExportInputError("body", "must not be an empty iterable", repr(body_or_bodies))
    return bodies


def _combine_bodies(body_or_bodies: Any) -> Any:
    """Combine one body (back-compat: its Shape) or N bodies (a Compound) → Shape.

    A single body returns its ``.Shape`` unchanged so single-body exports stay
    byte-identical to spec 002; multiple bodies form a ``Part.Compound`` (the
    caller applies ``_sorted_subshapes`` for a deterministic order).
    """
    bodies = _as_body_list(body_or_bodies)
    for b in bodies:
        _validate_body(b)
    if len(bodies) == 1:
        return bodies[0].Shape
    import Part

    return Part.Compound([b.Shape for b in bodies])


def _combine_meshes(body_or_bodies: Any, tessellation_tolerance_m: float) -> Any:
    """Merge per-body canonical meshes (sorted order) into one canonical Mesh."""
    import Mesh

    bodies = _as_body_list(body_or_bodies)
    for b in bodies:
        _validate_body(b)
    if len(bodies) == 1:
        return _build_canonical_mesh(bodies[0].Shape, tessellation_tolerance_m)
    # Combine the bodies' shapes into a sorted compound, then mesh the whole —
    # one canonical facet ordering over the merged shape (deterministic).
    combined = _sorted_subshapes(_combine_bodies(bodies))
    merged = _build_canonical_mesh(combined, tessellation_tolerance_m)
    assert isinstance(merged, Mesh.Mesh)
    return merged


def _resolve_tessellation_tolerance(value: float) -> float:
    """Validate the STL tessellation_tolerance kwarg."""
    if not isinstance(value, (int, float)) or math.isnan(float(value)):
        raise ExportInputError(
            "tessellation_tolerance",
            "must be a finite positive float",
            repr(value),
        )
    if value <= 0:
        raise ExportInputError(
            "tessellation_tolerance",
            "must be > 0",
            repr(value),
        )
    return float(value)


# ---------------------------------------------------------------------------
# Atomic write (research.md R7, FR-008)
# ---------------------------------------------------------------------------


def _atomic_write(target_path: Path, body_bytes: bytes) -> None:
    """Write ``body_bytes`` to ``target_path`` via a sibling tmp file + rename.

    Raises:
        ExportWriteError: Any failure during the temp-write, fsync, or rename.
            The temp file is unlinked best-effort before re-raising.
    """
    tmp_fd, tmp_name = tempfile.mkstemp(
        dir=target_path.parent,
        prefix=f".{target_path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(body_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
    except OSError as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise ExportWriteError(
            f"failed to write {target_path} — {type(exc).__name__}: {exc}",
            target_path=target_path,
            underlying=exc,
        ) from exc


def _sha256_of_file(path: Path) -> str:
    """Stream-compute SHA-256 of ``path``. Returns 64 hex chars, lower case."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Subshape ordering (research.md R5, FR-019)
# ---------------------------------------------------------------------------

_SHAPE_TYPE_RANK = {
    "Vertex": 1,
    "Edge": 2,
    "Wire": 3,
    "Face": 4,
    "Shell": 5,
    "Solid": 6,
    "Compound": 7,
}


def _shape_type_rank(shape_type: str) -> int:
    return _SHAPE_TYPE_RANK.get(shape_type, 99)


def _sorted_subshapes(shape: Any) -> Any:
    """Return a Shape with its Compound-level subshapes sorted by centroid.

    Centroid-based sort is invariant under FreeCAD-internal element reshuffling
    and stable across the supported FreeCAD version range (FR-019, OQ3
    resolution: applied recursively into Compound children).

    The implementation builds a sorted Compound from Compound inputs only.
    For Solid / Shell / Face / Edge / Vertex shapes the original is returned
    unchanged — their internal topology is already canonical in OpenCASCADE,
    and CenterOfMass is not defined on Vertex / Edge subshapes so recursing
    deeper would raise AttributeError.
    """
    import Part

    if getattr(shape, "ShapeType", "") != "Compound":
        return shape

    sub_shapes = list(getattr(shape, "SubShapes", []) or [])
    if not sub_shapes:
        return shape

    def _key(s: Any) -> tuple[float, float, float, int]:
        com = s.CenterOfMass if hasattr(s, "CenterOfMass") else None
        if com is None:
            return (0.0, 0.0, 0.0, _shape_type_rank(s.ShapeType))
        return (com.x, com.y, com.z, _shape_type_rank(s.ShapeType))

    sub_shapes.sort(key=_key)
    sorted_children = [_sorted_subshapes(child) for child in sub_shapes]
    return Part.makeCompound(sorted_children)


# ---------------------------------------------------------------------------
# STEP helpers (research.md R1, FR-017, FR-018)
# ---------------------------------------------------------------------------

# FreeCAD's STEP writer emits FILE_NAME and FILE_DESCRIPTION as multi-line
# entries with nested parens (author/organization tuples). The naive
# `[^)]*` pattern stops at the first inner `)`; switch to a non-greedy
# DOTALL match that consumes everything up to the closing `);`.
_STEP_FILE_NAME_RE = re.compile(rb"^FILE_NAME\s*\(.*?\)\s*;", re.MULTILINE | re.DOTALL)
_STEP_FILE_DESCRIPTION_RE = re.compile(
    rb"^FILE_DESCRIPTION\s*\(.*?\)\s*;", re.MULTILINE | re.DOTALL
)
_STEP_FIXED_FILE_NAME = (
    b"FILE_NAME('','1980-01-01T00:00:00',('freecad-storebro'),('freecad-storebro'),"
    b"'freecad-storebro','freecad-storebro','');"
)
_STEP_FIXED_FILE_DESCRIPTION = b"FILE_DESCRIPTION(('freecad-storebro export'),'2;1');"

# OpenCASCADE emits a per-session export counter in the PRODUCT entity
# (`'Open CASCADE STEP translator 7.8 1'`, `'... 2'`, ...). Scrub it to a
# fixed value so two consecutive exports produce byte-identical bytes.
_STEP_PRODUCT_COUNTER_RE = re.compile(rb"'Open CASCADE STEP translator [\d.]+ \d+'")
_STEP_FIXED_PRODUCT_NAME = b"'freecad-storebro'"


def _set_step_schema_to_ap214() -> None:
    """Set FreeCAD's STEP-export schema preference to AP214 in-process.

    Idempotent. Reads/writes the FreeCAD `Preferences` / `ParameterGrp` API;
    the change is process-local and does not persist to the user's config.
    """
    import FreeCAD

    pref = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Import/hSTEP")
    if pref.GetString("Scheme", "") != "AP214CD":
        pref.SetString("Scheme", "AP214CD")


def _canonicalize_step_header(raw_bytes: bytes) -> bytes:
    """Scrub the STEP HEADER section to fix timestamps + originator metadata."""
    body = _STEP_FILE_NAME_RE.sub(_STEP_FIXED_FILE_NAME, raw_bytes, count=1)
    body = _STEP_FILE_DESCRIPTION_RE.sub(_STEP_FIXED_FILE_DESCRIPTION, body, count=1)
    body = _STEP_PRODUCT_COUNTER_RE.sub(_STEP_FIXED_PRODUCT_NAME, body)
    return body.replace(b"\r\n", b"\n")


# ---------------------------------------------------------------------------
# BREP helpers (research.md R3, FR-018)
# ---------------------------------------------------------------------------

_BREP_ORIGINATOR_RE = re.compile(rb"^\s*//.*Originator.*$", re.MULTILINE)


def _canonicalize_brep_header(raw_bytes: bytes) -> bytes:
    """Normalize BREP originator + line endings."""
    body = _BREP_ORIGINATOR_RE.sub(b"// Originator: freecad-storebro", raw_bytes)
    return body.replace(b"\r\n", b"\n")


# ---------------------------------------------------------------------------
# FCStd zip-scrub helpers (research.md R4, FR-020)
# ---------------------------------------------------------------------------

_FCSTD_FIXED_DATE = "1980-01-01T00:00:00Z"
_FCSTD_FIXED_USER = "freecad-storebro"
_FCSTD_FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)
_FCSTD_FIXED_UUID = "00000000-0000-0000-0000-000000000000"
_FCSTD_FIXED_TRANSIENT_PATH = "freecad-storebro.FCStd"
_FCSTD_METADATA_FIELDS = frozenset(
    {"CreationDate", "LastModifiedDate", "CreatedBy", "LastModifiedBy"}
)
# Regex over the .FCStd Document.xml text catches:
#   • Random temp filenames FreeCAD records as String values during saveAs
#     (e.g. ".boat.FCStd.g651pps0" — the .tmp middle-suffix path).
#   • Per-process Object ID counters (FreeCAD increments across documents,
#     not per-document, so two consecutive exports produce different IDs).
_FCSTD_TRANSIENT_PATH_RE = re.compile(r'(<String\s+value=")\.[^"]+?\.FCStd\.[^"]+(")')
_FCSTD_OBJECT_ID_RE = re.compile(r'(\sid=")(\d+)(")')
# ISO 8601 timestamp String values (e.g. `<String value="2026-05-17T18:15:01+02:00" />`)
# leaked into Document.xml by various FreeCAD Property writers.
_FCSTD_ISO_TIMESTAMP_RE = re.compile(
    r'(<String\s+value=")\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2}(")'
)
# Per-session hex tag counters inside Shape.Map.txt / StringHasher.Table.txt
# entries (`:H57c:7,E`, `:H1310,V`, `1 0 159 3068`). FreeCAD increments
# these globally across the process. Normalize by remapping each unique
# tag to a stable sequential index in document order. Two forms appear:
#   `:H<hex>` followed by `,` or `:` — the topo-naming tag in element refs
#   ` <decimal> ` mid-line in StringHasher rows — the session counter (skip;
#     handled by HashRow normalization below)
# Match `:H<hex>` optionally followed by `:<hex>` (subdiv suffix), bounded by
# `,` or `;` (element-type or tag-separator). Both parts derive from
# session-global counters; scrub the composite token together.
_FCSTD_HEX_TAG_RE = re.compile(rb":H([0-9a-fA-F]+(?::[0-9a-fA-F]+)?)(?=[,;])")
# StringHasher rows have a decimal counter at column 4 that increments per
# session — `1 0 159 3068 1 ;:Hbfb,E;:H5:8,E 0` vs `1 0 159 857 1 ...`.
# Normalize the counter column to 0 to make exports deterministic.
_FCSTD_HASH_ROW_COUNTER_RE = re.compile(
    rb"^(\d+\s+\d+\s+\d+\s+)(\d+)(\s+\d+\s+;:H)",
    re.MULTILINE,
)


def _canonical_xml_serialize(root: ET.Element) -> bytes:
    """Serialize an XML tree with sorted attribute order, fixed indent, LF endings."""

    def _sort_attrs(elem: ET.Element) -> None:
        attribs = sorted(elem.attrib.items())
        elem.attrib.clear()
        for k, v in attribs:
            elem.set(k, v)
        for child in elem:
            _sort_attrs(child)

    _sort_attrs(root)
    ET.indent(root, space="  ")
    body: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return body.replace(b"\r\n", b"\n")


def _scrub_document_xml(xml_bytes: bytes) -> bytes:
    """Scrub timestamps + user metadata from an FCStd Document.xml entry.

    Spec 006 attempted to also scrub UUIDs, transient FCStd save paths,
    Object IDs, ISO 8601 timestamps, and Topological-Naming hex tags
    inside Map.txt / StringHasher entries. Every one of those broke
    FreeCAD's cross-references: the file became technically still a zip
    but the PartDesign Body's Shape recompute produced "shape is invalid"
    or the GUI loader crashed with "Error reading compression file" /
    SIGABRT. Cross-session byte determinism for the full hull+deck+interior
    FCStd is therefore deferred to a future spec (see
    deferred Fcstd.cross_session_byte_determinism in spec.allium). Within
    a single FreeCAD process, the existing well-known metadata scrub
    already produces byte-identical output for two consecutive exports.
    """
    text = xml_bytes.decode("utf-8")
    root = ET.fromstring(text)

    for elem in root.iter():
        if elem.tag in _FCSTD_METADATA_FIELDS:
            if "Date" in elem.tag:
                elem.text = _FCSTD_FIXED_DATE
            else:
                elem.text = _FCSTD_FIXED_USER
        for attr_name in list(elem.attrib):
            if attr_name in _FCSTD_METADATA_FIELDS:
                if "Date" in attr_name:
                    elem.set(attr_name, _FCSTD_FIXED_DATE)
                else:
                    elem.set(attr_name, _FCSTD_FIXED_USER)

    serialized = _canonical_xml_serialize(root)
    text = serialized.decode("utf-8")
    # Scrub the transient FCStd save-path String value (mkstemp's random
    # middle name leaks into a property). This is a property VALUE, not a
    # cross-reference; rewriting it is safe and is the only diff between
    # two consecutive exports of the same document in a single process.
    text = _FCSTD_TRANSIENT_PATH_RE.sub(
        rf"\g<1>{_FCSTD_FIXED_TRANSIENT_PATH}\g<2>", text
    )
    return text.encode("utf-8")


def _scrub_hex_tags(content: bytes) -> bytes:
    """Normalize per-session hex tag counters in Shape.Map.txt / StringHasher
    files. The Topological Naming hex tags (`:H<hex>:`, `:H<hex>,V`) derive
    from a FreeCAD process-global counter; without normalization two
    consecutive exports of the same hull produce different Map.txt bytes
    even though the geometry is identical. Renumber each unique tag to a
    stable sequential index in document order.

    Note: this scrub does NOT touch Document.xml — only the auxiliary
    .Map.txt / StringHasher.Table.txt entries that don't participate in
    FreeCAD's cross-reference graph for shape reconstruction.
    """
    seen: dict[bytes, bytes] = {}

    def _renumber(match: re.Match[bytes]) -> bytes:
        tag = match.group(1)
        if tag not in seen:
            seen[tag] = f"{len(seen):x}".encode()
        return b":H" + seen[tag]

    content = _FCSTD_HEX_TAG_RE.sub(_renumber, content)
    content = _FCSTD_HASH_ROW_COUNTER_RE.sub(rb"\g<1>0\g<3>", content)
    return content


def _scrub_fcstd_zip(raw_zip_bytes: bytes) -> bytes:
    """Re-pack an FCStd zip with deterministic timestamps, metadata, order."""
    entries: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(raw_zip_bytes), "r") as zin:
        for info in zin.infolist():
            name = info.filename
            data = zin.read(info)
            if name == "Document.xml":
                data = _scrub_document_xml(data)
            elif name.endswith(".Map.txt") or name == "StringHasher.Table.txt":
                data = _scrub_hex_tags(data)
            entries.append((name, data))

    # PRESERVE the original FreeCAD-written entry order. Spec 002's FR-020
    # originally required alphabetical sort for determinism, but the
    # PartDesign Body's Shape rebuild depends on the load order of the
    # .brp / .Map.txt entries — sorting breaks "shape is invalid" or
    # "Error reading compression file" depending on where Document.xml
    # ends up. FreeCAD's own writer produces a stable order within a
    # process; the in-process byte-determinism guarantee carries through.

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as zout:
        for name, data in entries:
            info = zipfile.ZipInfo(filename=name, date_time=_FCSTD_FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            zout.writestr(info, data)

    return out.getvalue()


# ---------------------------------------------------------------------------
# Mesh helpers (research.md R2, FR-010/011/012)
# ---------------------------------------------------------------------------


def _build_canonical_mesh(body_shape: Any, tessellation_tolerance_m: float) -> Any:
    """Tessellate the source Shape into a Mesh.Mesh with canonical facet order."""
    import Mesh
    import MeshPart

    deflection_mm = tessellation_tolerance_m * 1000.0
    mesh = MeshPart.meshFromShape(
        Shape=body_shape,
        LinearDeflection=deflection_mm,
        AngularDeflection=0.5,
    )

    # FR-019 applied to mesh facets: centroid-sort the triangles so the
    # writer's output ordering is deterministic across FreeCAD-internal
    # facet reshuffling.
    topology = mesh.Topology
    points = list(topology[0])
    facets = list(topology[1])

    def _facet_centroid(triangle: tuple[int, int, int]) -> tuple[float, float, float]:
        p0 = points[triangle[0]]
        p1 = points[triangle[1]]
        p2 = points[triangle[2]]
        return (
            (p0[0] + p1[0] + p2[0]) / 3.0,
            (p0[1] + p1[1] + p2[1]) / 3.0,
            (p0[2] + p1[2] + p2[2]) / 3.0,
        )

    facets.sort(key=_facet_centroid)

    canonical = Mesh.Mesh()
    for triangle in facets:
        p0 = points[triangle[0]]
        p1 = points[triangle[1]]
        p2 = points[triangle[2]]
        canonical.addFacet(p0, p1, p2)
    return canonical


def _check_watertight(mesh: Any, format_label: str, target_path: Path) -> None:
    """Raise ExportWriteError if the mesh fails the SC-008 watertight check."""
    is_solid = bool(mesh.isSolid())
    non_manifolds = bool(getattr(mesh, "hasNonManifolds", lambda: False)())
    self_intersects = bool(getattr(mesh, "hasSelfIntersections", lambda: False)())
    if (not is_solid) or non_manifolds or self_intersects:
        raise ExportWriteError(
            "mesh is not watertight — "
            f"is_solid={is_solid}, non_manifolds={non_manifolds}, "
            f"self_intersects={self_intersects}",
            target_path=target_path,
            format=format_label,
        )


# ---------------------------------------------------------------------------
# Public writers
# ---------------------------------------------------------------------------


def _ensure_freecad_supported(format_label: str) -> None:
    """Wrap the shared lazy version check (storebro._freecad_check) to use
    export-flavoured exceptions on failure (matches FR-014).

    Imports only the underscore-prefixed shared helper module, NOT
    storebro.hull, to preserve FR-013 (export is a leaf module against the
    public storebro.* surface). The HullConstructionError raised by the
    helper is caught by duck-typing on its attributes rather than by
    importing the class name.
    """
    from storebro import _freecad_check

    try:
        _freecad_check.ensure_supported_freecad()
    except Exception as exc:
        detected = getattr(exc, "detected_version", None)
        supported = getattr(exc, "supported_range", None)
        raise ExportWriteError(
            f"unsupported FreeCAD version while preparing {format_label} export",
            format=format_label,
            detected_version=detected,
            supported_range=supported,
            underlying=exc,
        ) from exc


def _read_bytes(path: Path) -> bytes:
    with path.open("rb") as f:
        return f.read()


def _validate_body(body: Any, *, required: bool = True) -> None:
    """Ensure ``body`` carries a non-empty Shape (raise ExportInputError otherwise)."""
    if body is None:
        raise ExportInputError("body", "must not be None")
    shape = getattr(body, "Shape", None)
    if shape is None:
        raise ExportInputError(
            "body",
            "object has no `.Shape` attribute — pass a Body or Shape-bearing object",
            type(body).__name__,
        )
    if required and getattr(shape, "isNull", lambda: True)():
        raise ExportInputError(
            "body",
            "shape is null/empty — recompute the source document first",
        )


def export_step(
    body: Any,
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
    gzip: bool = False,
) -> ExportArtifact:
    """Write a FreeCAD Body (or assembly of bodies) to an AP214 STEP file.

    Args:
        body: A FreeCAD object with a non-empty ``.Shape``, OR (spec 026) an
            iterable of such bodies combined into one deterministic compound.
        target_path: Destination file path. Must end in ``.step``/``.stp``
            (or that + ``.gz`` when ``gzip=True``).
        overwrite: If False, raises :class:`ExportInputError` when target exists.
        gzip: If True, deterministically gzip the output (path must end ``.gz``).

    Returns:
        :class:`ExportArtifact` with the SHA-256 of the produced bytes.

    Raises:
        ExportInputError: Invalid path, wrong extension, parent dir missing,
            empty body, or target exists with ``overwrite=False``.
        ExportWriteError: Unsupported FreeCAD version, FreeCAD-side write
            failure, or atomic rename failure.

    Example:
        >>> # from storebro import build_hull, export_step
        >>> # art = export_step(build_hull().body, "/tmp/boat.step")
        >>> # art.format
        >>> # 'step'
    """
    _ensure_freecad_supported("step")
    resolved = _resolve_target_path(target_path, "step", overwrite, gzip)

    _set_step_schema_to_ap214()
    started = time.perf_counter()
    tmp_fd, tmp_name = tempfile.mkstemp(
        dir=resolved.parent,
        prefix=f".{resolved.name}.",
        suffix=".step",
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)
    try:
        canonical = _sorted_subshapes(_combine_bodies(body))
        # spec 026 fix: `Part.export([raw_shape], path)` does NOT serialize a raw
        # Part.Shape's geometry (it expects document objects) — every STEP was
        # geometry-less. The Shape method writes the real B-rep (matches the
        # exportBrep/exportIges idiom).
        canonical.exportStep(str(tmp_path))
        raw = _read_bytes(tmp_path)
        scrubbed = _maybe_gzip(_canonicalize_step_header(raw), gzip)
    except ExportInputError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    except BaseException as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise ExportWriteError(
            f"FreeCAD failed while writing STEP — {type(exc).__name__}: {exc}",
            target_path=resolved,
            underlying=exc,
            format="step",
        ) from exc
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)

    _atomic_write(resolved, scrubbed)
    duration = time.perf_counter() - started
    return ExportArtifact(
        target_path=resolved,
        format="step",
        byte_count=len(scrubbed),
        sha256=_sha256_of_file(resolved),
        build_duration_seconds=duration,
    )


def export_brep(
    body: Any,
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
    gzip: bool = False,
) -> ExportArtifact:
    """Write a FreeCAD Body (or assembly of bodies) to an OpenCASCADE BREP file.

    Args:
        body: A FreeCAD object with a non-empty ``.Shape``, OR (spec 026) an
            iterable of such bodies combined into one deterministic compound.
        target_path: Destination file path. Must end in ``.brep``/``.brp``
            (or that + ``.gz`` when ``gzip=True``).
        overwrite: If False, raises :class:`ExportInputError` when target exists.
        gzip: If True, deterministically gzip the output (path must end ``.gz``).

    Returns:
        :class:`ExportArtifact` with the SHA-256 of the produced bytes.

    Example:
        >>> # art = export_brep(hull.body, "/tmp/boat.brep")
        >>> # art.format
        >>> # 'brep'
    """
    _ensure_freecad_supported("brep")
    resolved = _resolve_target_path(target_path, "brep", overwrite, gzip)

    started = time.perf_counter()
    tmp_fd, tmp_name = tempfile.mkstemp(
        dir=resolved.parent,
        prefix=f".{resolved.name}.",
        suffix=".brep.tmp",
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)
    try:
        canonical = _sorted_subshapes(_combine_bodies(body))
        canonical.exportBrep(str(tmp_path))
        raw = _read_bytes(tmp_path)
        scrubbed = _maybe_gzip(_canonicalize_brep_header(raw), gzip)
    except ExportInputError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    except BaseException as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise ExportWriteError(
            f"FreeCAD failed while writing BREP — {type(exc).__name__}: {exc}",
            target_path=resolved,
            underlying=exc,
            format="brep",
        ) from exc
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)

    _atomic_write(resolved, scrubbed)
    duration = time.perf_counter() - started
    return ExportArtifact(
        target_path=resolved,
        format="brep",
        byte_count=len(scrubbed),
        sha256=_sha256_of_file(resolved),
        build_duration_seconds=duration,
    )


def export_stl(
    body: Any,
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
    tessellation_tolerance: float = 0.001,
    gzip: bool = False,
) -> ExportArtifact:
    """Write a FreeCAD Body (or assembly of bodies) to a binary STL file.

    Args:
        body: A FreeCAD object with a non-empty ``.Shape``, OR (spec 026) an
            iterable of such bodies merged into one canonical mesh.
        target_path: Destination file path. Must end in ``.stl`` (or that +
            ``.gz`` when ``gzip=True``).
        overwrite: If False, raises :class:`ExportInputError` when target exists.
        tessellation_tolerance: Absolute linear chord deviation, in meters.
            Default 0.001 (1 mm). Must be > 0.
        gzip: If True, deterministically gzip the output (path must end ``.gz``).

    Returns:
        :class:`ExportArtifact` with the SHA-256 of the produced bytes.

    Example:
        >>> # art = export_stl(hull.body, "/tmp/boat.stl", tessellation_tolerance=0.0005)
        >>> # art.format
        >>> # 'stl'
    """
    _ensure_freecad_supported("stl")
    resolved = _resolve_target_path(target_path, "stl", overwrite, gzip)
    tolerance = _resolve_tessellation_tolerance(tessellation_tolerance)

    started = time.perf_counter()
    tmp_fd, tmp_name = tempfile.mkstemp(
        dir=resolved.parent,
        prefix=f".{resolved.name}.",
        suffix=".stl",
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)
    try:
        mesh = _combine_meshes(body, tolerance)
        # The watertight check is a single-body invariant; an assembly is
        # intentionally several solids whose merged mesh may self-intersect where
        # bodies touch, so apply the check only to a single body (spec 026).
        if len(_as_body_list(body)) == 1:
            _check_watertight(mesh, "stl", resolved)
        mesh.write(str(tmp_path), "STLB")
        raw = _maybe_gzip(_read_bytes(tmp_path), gzip)
    except (ExportInputError, ExportWriteError):
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    except BaseException as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise ExportWriteError(
            f"FreeCAD failed while writing STL — {type(exc).__name__}: {exc}",
            target_path=resolved,
            underlying=exc,
            format="stl",
        ) from exc
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)

    _atomic_write(resolved, raw)
    duration = time.perf_counter() - started
    return ExportArtifact(
        target_path=resolved,
        format="stl",
        byte_count=len(raw),
        sha256=_sha256_of_file(resolved),
        build_duration_seconds=duration,
    )


def export_fcstd(
    document: Any,
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
    gzip: bool = False,
) -> ExportArtifact:
    """Write a FreeCAD Document to a deterministic .FCStd archive.

    Args:
        document: An open FreeCAD Document. Will be recomputed before save.
        target_path: Destination file path. Must end in ``.FCStd`` or ``.fcstd``.
        overwrite: If False, raises :class:`ExportInputError` when target exists.

    Returns:
        :class:`ExportArtifact` with the SHA-256 of the produced bytes.

    Example:
        >>> # art = export_fcstd(hull.document, "/tmp/boat.FCStd")
        >>> # art.format
        >>> # 'fcstd'
    """
    _ensure_freecad_supported("fcstd")
    resolved = _resolve_target_path(target_path, "fcstd", overwrite, gzip)
    if document is None:
        raise ExportInputError("document", "must not be None")
    if not hasattr(document, "saveAs"):
        raise ExportInputError(
            "document",
            "object does not look like a FreeCAD Document (missing saveAs)",
            type(document).__name__,
        )

    started = time.perf_counter()
    tmp_fd, tmp_name = tempfile.mkstemp(
        dir=resolved.parent,
        prefix=f".{resolved.name}.",
        suffix=".FCStd",
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)
    try:
        document.recompute()
        document.saveAs(str(tmp_path))
        raw_zip = _read_bytes(tmp_path)
        scrubbed = _maybe_gzip(_scrub_fcstd_zip(raw_zip), gzip)
    except ExportInputError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    except BaseException as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise ExportWriteError(
            f"FreeCAD failed while writing FCStd — {type(exc).__name__}: {exc}",
            target_path=resolved,
            underlying=exc,
            format="fcstd",
        ) from exc
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)

    _atomic_write(resolved, scrubbed)
    duration = time.perf_counter() - started
    return ExportArtifact(
        target_path=resolved,
        format="fcstd",
        byte_count=len(scrubbed),
        sha256=_sha256_of_file(resolved),
        build_duration_seconds=duration,
    )


# ---------------------------------------------------------------------------
# spec 026 — new format writers (OBJ, IGES, DXF profile)
# ---------------------------------------------------------------------------

# IGES global section carries a creation date token YYYYMMDD.HHMMSS (e.g.
# 20260610.204357); zero it so two exports at different times are byte-identical.
_IGES_DATE_RE = re.compile(rb"\d{8}\.\d{6}")
_IGES_FIXED_DATE = b"00000000.000000"


def _canonicalize_iges_header(raw_bytes: bytes) -> bytes:
    """Scrub the IGES global-section creation date for byte determinism."""
    return _IGES_DATE_RE.sub(_IGES_FIXED_DATE, raw_bytes).replace(b"\r\n", b"\n")


def export_obj(
    body: Any,
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
    tessellation_tolerance: float = 0.001,
    gzip: bool = False,
) -> ExportArtifact:
    """Write a FreeCAD Body (or assembly of bodies) to a Wavefront OBJ file.

    Args:
        body: A body with a non-empty ``.Shape``, OR an iterable of bodies merged
            into one canonical mesh.
        target_path: Destination path. Must end ``.obj`` (or ``.obj.gz``).
        overwrite: If False, raises :class:`ExportInputError` when target exists.
        tessellation_tolerance: Chord deviation in meters (> 0, default 1 mm).
        gzip: If True, deterministically gzip the output (path must end ``.gz``).

    Returns:
        :class:`ExportArtifact` with the SHA-256 of the produced bytes.

    Example:
        >>> # from storebro import build_hull, export_obj
        >>> # art = export_obj(build_hull().body, "/tmp/boat.obj")
        >>> # art.format
        >>> # 'obj'
    """
    _ensure_freecad_supported("obj")
    resolved = _resolve_target_path(target_path, "obj", overwrite, gzip)
    tolerance = _resolve_tessellation_tolerance(tessellation_tolerance)

    started = time.perf_counter()
    tmp_fd, tmp_name = tempfile.mkstemp(
        dir=resolved.parent, prefix=f".{resolved.name}.", suffix=".obj"
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)
    try:
        mesh = _combine_meshes(body, tolerance)
        mesh.write(str(tmp_path))  # extension → OBJ
        # The FreeCAD OBJ header is a static URL comment (no version/timestamp),
        # so the raw bytes are already reproducible; normalize line endings only.
        raw = _maybe_gzip(_read_bytes(tmp_path).replace(b"\r\n", b"\n"), gzip)
    except (ExportInputError, ExportWriteError):
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    except BaseException as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise ExportWriteError(
            f"FreeCAD failed while writing OBJ — {type(exc).__name__}: {exc}",
            target_path=resolved,
            underlying=exc,
            format="obj",
        ) from exc
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)

    _atomic_write(resolved, raw)
    duration = time.perf_counter() - started
    return ExportArtifact(
        target_path=resolved,
        format="obj",
        byte_count=len(raw),
        sha256=_sha256_of_file(resolved),
        build_duration_seconds=duration,
    )


def export_iges(
    body: Any,
    target_path: str | os.PathLike[str],
    *,
    overwrite: bool = True,
    gzip: bool = False,
) -> ExportArtifact:
    """Write a FreeCAD Body (or assembly of bodies) to an IGES B-rep file.

    Args:
        body: A body with a non-empty ``.Shape``, OR an iterable of bodies
            combined into one deterministic compound.
        target_path: Destination path. Must end ``.iges``/``.igs`` (or + ``.gz``).
        overwrite: If False, raises :class:`ExportInputError` when target exists.
        gzip: If True, deterministically gzip the output (path must end ``.gz``).

    Returns:
        :class:`ExportArtifact` with the SHA-256 of the produced bytes.

    Example:
        >>> # from storebro import build_hull, export_iges
        >>> # art = export_iges(build_hull().body, "/tmp/boat.iges")
        >>> # art.format
        >>> # 'iges'
    """
    _ensure_freecad_supported("iges")
    resolved = _resolve_target_path(target_path, "iges", overwrite, gzip)

    started = time.perf_counter()
    tmp_fd, tmp_name = tempfile.mkstemp(
        dir=resolved.parent, prefix=f".{resolved.name}.", suffix=".iges"
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)
    try:
        canonical = _sorted_subshapes(_combine_bodies(body))
        canonical.exportIges(str(tmp_path))
        raw = _maybe_gzip(_canonicalize_iges_header(_read_bytes(tmp_path)), gzip)
    except ExportInputError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    except BaseException as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise ExportWriteError(
            f"FreeCAD failed while writing IGES — {type(exc).__name__}: {exc}",
            target_path=resolved,
            underlying=exc,
            format="iges",
        ) from exc
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)

    _atomic_write(resolved, raw)
    duration = time.perf_counter() - started
    return ExportArtifact(
        target_path=resolved,
        format="iges",
        byte_count=len(raw),
        sha256=_sha256_of_file(resolved),
        build_duration_seconds=duration,
    )


def _project_edges_xz(shape: Any) -> list[tuple[float, float, float, float]]:
    """Project a shape's edges onto the X-Z plane (drop Y) → sorted segments.

    Each edge becomes one (x1, z1, x2, z2) segment using its endpoints; segments
    are rounded (6 dp), de-duplicated, and sorted for deterministic output.
    """
    segs: set[tuple[float, float, float, float]] = set()
    for edge in shape.Edges:
        verts = edge.Vertexes
        if len(verts) < 2:
            continue
        p, q = verts[0].Point, verts[-1].Point
        segs.add((round(p.x, 6), round(p.z, 6), round(q.x, 6), round(q.z, 6)))
    return sorted(segs)


def _write_r12_dxf(segments: list[tuple[float, float, float, float]]) -> bytes:
    """Hand-write a minimal AutoCAD R12 ASCII DXF (LINE entities, no handles).

    R12 ASCII needs no timestamps or handles, so the output is deterministic by
    construction given a sorted segment list.
    """
    lines = ["0", "SECTION", "2", "ENTITIES"]
    for (x1, z1, x2, z2) in segments:
        lines += [
            "0", "LINE", "8", "0",
            "10", f"{x1:.6f}", "20", f"{z1:.6f}", "30", "0.0",
            "11", f"{x2:.6f}", "21", f"{z2:.6f}", "31", "0.0",
        ]
    lines += ["0", "ENDSEC", "0", "EOF"]
    return ("\n".join(lines) + "\n").encode("ascii")


def export_dxf_profile(
    body: Any,
    target_path: str | os.PathLike[str],
    *,
    plane: str = "xz",
    overwrite: bool = True,
    gzip: bool = False,
) -> ExportArtifact:
    """Write a 2D profile DXF — the model's silhouette projected onto a plane.

    Args:
        body: A body with a non-empty ``.Shape``, OR an iterable of bodies.
        target_path: Destination path. Must end ``.dxf`` (or ``.dxf.gz``).
        plane: Projection plane. Only ``"xz"`` (side/profile view) is supported.
        overwrite: If False, raises :class:`ExportInputError` when target exists.
        gzip: If True, deterministically gzip the output (path must end ``.gz``).

    Returns:
        :class:`ExportArtifact` with the SHA-256 of the produced bytes.

    Raises:
        ExportInputError: Unsupported plane, or a degenerate (no-edge) projection.

    Example:
        >>> # from storebro import build_hull, export_dxf_profile
        >>> # art = export_dxf_profile(build_hull().body, "/tmp/boat.dxf")
        >>> # art.format
        >>> # 'dxf'
    """
    _ensure_freecad_supported("dxf")
    if plane != "xz":
        raise ExportInputError("plane", "only 'xz' (side profile) is supported", repr(plane))
    resolved = _resolve_target_path(target_path, "dxf", overwrite, gzip)

    started = time.perf_counter()
    shape = _sorted_subshapes(_combine_bodies(body))
    segments = _project_edges_xz(shape)
    if not segments:
        raise ExportInputError(
            "body", "projection has no edges (degenerate profile)", repr(target_path)
        )
    raw = _maybe_gzip(_write_r12_dxf(segments), gzip)
    _atomic_write(resolved, raw)
    duration = time.perf_counter() - started
    return ExportArtifact(
        target_path=resolved,
        format="dxf",
        byte_count=len(raw),
        sha256=_sha256_of_file(resolved),
        build_duration_seconds=duration,
    )
