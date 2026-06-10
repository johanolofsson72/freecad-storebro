# Feature Specification: Export Format Expansion

**Feature Branch**: `026-export-format-expansion`

**Created**: 2026-06-10

**Status**: Draft

**Input**: User description: "Broaden the spec 002 export surface: glTF (web/render), OBJ, IGES, and a 2D DXF profile export; optional gzip; full-assembly export in the non-FCStd formats (currently single-body)."

## User Scenarios & Testing *(mandatory)*

A library consumer (restorer, scale modeler, web developer, CAD user) builds the Storebro model and needs to get it out of FreeCAD in the format their downstream tool wants. Today they have STEP, STL, BREP (single-body each) and FCStd (full document). They want more: a glTF for a web/three.js viewer, an OBJ for a renderer or game engine, an IGES for a legacy CAD package, and a 2D DXF profile for a drawing. They also want the *whole boat* in those formats — today STEP/STL/BREP export only the hull body, silently dropping the deck, interior, and propulsion. And they want to optionally gzip any output to save space. Every export must stay byte-reproducible (constitution II) or, where a format cannot be made byte-identical, that must be explicit and the format gated accordingly.

### User Story 1 - Full-assembly export in mesh + B-rep formats (Priority: P1)

The consumer builds hull + deck + interior + propulsion and exports to STEP/STL/BREP, expecting the *whole boat*. Today these formats export only the hull body — the rest is silently lost. The consumer wants a full-assembly export that includes every body, in a deterministic order.

**Why this priority**: This is a correctness gap, not just a new feature — STEP/STL/BREP exports are silently incomplete today. It also underpins the new formats (they all need the same multi-body assembly). It is the highest-value item.

**Independent Test**: Build the full model, export the assembly to STEP/STL/BREP, and confirm the output contains geometry from every body (hull + deck + interior + propulsion), not just the hull; two exports of the same assembly are byte-identical.

**Acceptance Scenarios**:

1. **Given** a built model with hull + deck + interior + propulsion bodies, **When** the assembly is exported to STEP/STL/BREP, **Then** the output's geometry extent (bounding box / triangle count) reflects all bodies, not just the hull.
2. **Given** the same assembly exported twice, **When** the two outputs are compared, **Then** they are byte-identical (deterministic body + sub-shape ordering).
3. **Given** the existing single-body export functions, **When** a consumer calls them with one body, **Then** they behave exactly as before (back-compatible).

---

### User Story 2 - glTF export (Priority: P1)

The consumer wants a glTF file to drop into a web/three.js viewer or a render pipeline.

**Why this priority**: glTF is the headline "web/render" format the feature is named for; it is the most-requested modern interchange format.

**Independent Test**: Export the model (single body or assembly) to glTF; confirm the file is a valid glTF that loads in a standard glTF validator/viewer and contains the model's mesh; two exports are byte-identical (or, if byte-identity is infeasible for glTF, the format is gated per the reproducibility policy and that is documented).

**Acceptance Scenarios**:

1. **Given** a built body or assembly, **When** exported to glTF, **Then** a valid `.gltf`/`.glb` file is written containing the tessellated mesh.
2. **Given** the same input exported twice, **When** compared, **Then** the outputs are byte-identical, OR the format is explicitly flagged non-deterministic and gated per the reproducibility policy.

---

### User Story 3 - OBJ export (Priority: P2)

The consumer wants a Wavefront OBJ for a renderer or game engine.

**Why this priority**: OBJ is the most ubiquitous mesh interchange format; low-risk (plain text, deterministic vertex/face lists from the canonical mesh).

**Independent Test**: Export to OBJ; confirm a valid OBJ with vertices + faces matching the model's mesh; two exports byte-identical.

**Acceptance Scenarios**:

1. **Given** a built body or assembly, **When** exported to OBJ, **Then** a valid `.obj` with the tessellated mesh (vertices + triangular faces) is written.
2. **Given** the same input exported twice, **When** compared, **Then** the outputs are byte-identical.

---

### User Story 4 - IGES export (Priority: P2)

The consumer wants an IGES file for a legacy CAD package that does not read STEP.

**Why this priority**: IGES is a B-rep interchange like STEP; medium risk (IGES global section carries a timestamp that must be scrubbed, like the STEP header).

**Independent Test**: Export to IGES; confirm a valid `.iges` B-rep that re-imports with the model's solids; two exports byte-identical.

**Acceptance Scenarios**:

1. **Given** a built body or assembly, **When** exported to IGES, **Then** a valid `.iges`/`.igs` B-rep file is written.
2. **Given** the same input exported twice, **When** compared, **Then** the outputs are byte-identical (timestamp / header scrubbed).

---

### User Story 5 - 2D DXF profile export (Priority: P3)

The consumer wants a 2D DXF profile (the boat's silhouette) for a drawing or laser/plasma workflow.

**Why this priority**: A different paradigm (2D projection, not 3D geometry), useful but the lowest-priority and highest-novelty item.

**Independent Test**: Export a 2D DXF profile of the model projected onto a plane; confirm a valid `.dxf` containing the projected outline edges; two exports byte-identical (or gated per the reproducibility policy if DXF byte-identity is infeasible).

**Acceptance Scenarios**:

1. **Given** a built model, **When** a 2D profile DXF is exported, **Then** a valid `.dxf` with the projected silhouette (edges/polylines on a single plane) is written.
2. **Given** the same input exported twice, **When** compared, **Then** the outputs are byte-identical, OR the format is gated per the reproducibility policy and documented.

---

### User Story 6 - Optional gzip compression (Priority: P3)

The consumer wants to gzip any export to save space (e.g. a large STL or glTF).

**Why this priority**: Orthogonal convenience that applies to every format; low risk (deterministic gzip with a zeroed mtime).

**Independent Test**: Export any format with gzip enabled; confirm the output is a valid gzip whose decompressed bytes equal the un-gzipped export; two gzipped exports byte-identical.

**Acceptance Scenarios**:

1. **Given** any export format, **When** gzip is enabled, **Then** the output is a valid `.gz` whose decompressed content equals the corresponding un-gzipped export.
2. **Given** the same input gzipped twice, **When** compared, **Then** the two `.gz` files are byte-identical (gzip mtime zeroed, no embedded filename).

---

### Edge Cases

- **Reproducibility (constitution II)**: every new format MUST be byte-reproducible across identical exports, OR — if a format genuinely cannot be made byte-identical (generator strings, embedded UUIDs, etc.) — it MUST be explicitly flagged and handled per the reproducibility policy (gated / documented), never silently nondeterministic. A pre-implementation spike determines per-format byte-determinism.
- **Empty / invalid input**: exporting an empty body, a body with no shape, or an unsupported extension raises a clear `ExportInputError` (the spec 002 idiom).
- **Extension / format mismatch**: each format validates its target extension (`.gltf`/`.glb`, `.obj`, `.iges`/`.igs`, `.dxf`, `.gz`), reusing the spec 002 `_KNOWN_EXTENSIONS` mechanism.
- **Assembly ordering**: the multi-body assembly export orders bodies and sub-shapes deterministically (the spec 002 `_sorted_subshapes` discipline) so the output is byte-stable regardless of body-construction order.
- **Overwrite**: each new export respects the spec 002 `overwrite` flag and atomic-write behavior.
- **gzip composition**: gzip composes with every format (mesh, B-rep, DXF) and with both single-body and assembly export.
- **Back-compatibility**: the existing `export_step/stl/brep/fcstd` single-body/document signatures are unchanged; new capability is additive.
- **DXF projection plane / empty projection**: the 2D profile projects onto a defined plane (default: the boat's profile/side view); a degenerate projection (no edges) raises a clear error rather than writing an empty file.

## Clarifications

### Session 2026-06-10

- Q: Reproducibility policy for a format that cannot be made byte-identical? → A: Ship-if-reproducible, else DEFER. Constitution II is non-negotiable, so a new format ships (on by default) ONLY if the pre-implementation spike proves it byte-identical after scrubbing generator strings / timestamps / handles. Any format that cannot be made byte-reproducible (most likely glTF or DXF) is DEFERRED to a future spec — never shipped in a silently-nondeterministic state. The spike's per-format result decides what ships.
- Q: Assembly API shape? → A: Each per-format export function accepts EITHER a single body OR an iterable of bodies (the assembly); a single body combines to itself (byte-identical to the pre-026 single-body export), an iterable combines into one compound (B-rep formats) or one merged canonical mesh (mesh formats), ordered deterministically by the spec 002 sub-shape sort.
- Q: CLI default for the multi-body formats? → A: Full assembly by default. The CLI build export writes the whole boat (hull + deck + interior + propulsion) for the multi-body formats, fixing today's silent hull-only drop. The single-body export FUNCTIONS remain available for one-body use.
- Q: DXF 2D-profile projection plane default? → A: The X-Z side/profile view (the boat's silhouette as the reference photos show it), exposed as a named projection-plane parameter with that default.
- Q: gzip API? → A: A `gzip: bool = False` keyword on each export function; when true the export's bytes are deterministically gzipped (mtime zeroed, no embedded filename) and the target path carries a `.gz` suffix.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a full-assembly export for the mesh (STL) and B-rep (STEP, BREP) formats that includes every body of the built model (hull + deck + interior + propulsion), in a deterministic order, not just the hull body. Each per-format export function MUST accept EITHER a single body (byte-identical to the pre-026 single-body export) OR an iterable of bodies combined into one compound (B-rep) / merged canonical mesh (mesh), ordered by the spec 002 sub-shape sort.
- **FR-002**: The system MUST provide a glTF export of a body or assembly (tessellated mesh), writing a valid glTF file — **provided the spike proves glTF byte-reproducible; otherwise glTF is deferred (FR-007)** (glTF embeds generator metadata, so it is the highest determinism risk).
- **FR-003**: The system MUST provide a Wavefront OBJ export of a body or assembly (tessellated mesh), writing a valid OBJ file.
- **FR-004**: The system MUST provide an IGES export of a body or assembly (B-rep), writing a valid IGES file.
- **FR-005**: The system MUST provide a 2D DXF profile export that projects the model onto the X-Z side/profile plane (a named projection-plane parameter defaulting to X-Z) and writes the silhouette outline as a valid DXF — **provided the spike proves DXF byte-reproducible; otherwise DXF is deferred (FR-007)**.
- **FR-006**: The system MUST provide optional gzip compression for any export format via a `gzip: bool = False` keyword, producing a deterministic gzip (mtime zeroed, no embedded filename) whose decompressed bytes equal the corresponding un-gzipped export; the target path carries a `.gz` suffix when gzipped.
- **FR-007**: Every export that SHIPS MUST be byte-reproducible across two identical exports (constitution II, non-negotiable). A pre-implementation spike MUST prove each new format byte-identical after scrubbing generator strings / timestamps / handles. A format that CANNOT be made byte-reproducible MUST be DEFERRED to a future spec — it MUST NOT ship in a silently-nondeterministic state. The spike's per-format result decides what ships (deterministic formats on by default; non-reproducible ones deferred).
- **FR-008**: Each new format MUST validate its target-path extension (`.gltf`/`.glb`, `.obj`, `.iges`/`.igs`, `.dxf`; `.gz` suffix when gzipped) and raise `ExportInputError` on mismatch, reusing the spec 002 extension-validation mechanism.
- **FR-009**: Each new export MUST return the spec 002 `ExportArtifact` (format, target_path, byte_count, sha256) and respect the `overwrite` flag + atomic-write behavior.
- **FR-010**: The existing `export_step`, `export_stl`, `export_brep`, `export_fcstd` signatures MUST stay backward-compatible; new formats/assembly/gzip are additive (new functions or additive keyword parameters with defaults).
- **FR-011**: Construction MUST stay FreeCAD-idiomatic and reuse the spec 002 machinery (canonical mesh facet ordering for mesh formats, sorted sub-shapes for B-rep, header/timestamp scrubbing, atomic write, SHA-256). Mesh generation stays inside the export adapters (constitution III).
- **FR-012**: The CLI MUST expose the shipped new formats and a gzip flag, and MUST export the full assembly (hull + deck + interior + propulsion) BY DEFAULT for the multi-body formats — fixing today's silent hull-only drop. Existing flags keep parsing; the single-body export functions remain available for one-body use.
- **FR-013**: Every new dimension/parameter (tessellation tolerance for the new mesh formats, the DXF projection plane, the gzip toggle) MUST be a named parameter with a default (constitution I).

### Key Entities

- **Assembly**: an ordered collection of the model's bodies (hull + deck + interior + propulsion) exported as one combined output; ordering is deterministic.
- **Export format**: an output kind (existing: step/stl/brep/fcstd; new: gltf/obj/iges/dxf), each with allowed extensions, a writer, and a determinism marker.
- **Determinism marker**: a per-format result from the spike recording whether the format is byte-reproducible; governs whether the format ships at all (byte-reproducible → ships on by default; not reproducible → deferred to a future spec, per FR-007).
- **2D profile**: the model's silhouette projected onto a plane, written as DXF outline edges.
- **gzip wrapper**: an optional deterministic compression applied to any export's bytes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A full-assembly STEP/STL/BREP export contains geometry from every body (bounding box / triangle count reflects hull + deck + interior + propulsion), not just the hull.
- **SC-002**: glTF, OBJ, IGES, and 2D DXF exports each produce a valid file that re-imports (or validates) with the expected content (mesh for gltf/obj, B-rep for iges, outline edges for dxf).
- **SC-003**: Two identical exports of any format are byte-identical (equal SHA-256); any format flagged non-deterministic by the spike is gated/documented and not silently shipped.
- **SC-004**: A gzipped export's decompressed bytes equal the corresponding un-gzipped export, and two gzipped exports are byte-identical.
- **SC-005**: The existing STL/BREP/FCStd single-body exports are unchanged (byte-identical to pre-026 for the same single body/document). STEP single-body output legitimately CHANGES this release: a pre-existing spec 002 bug (`export_step` used `Part.export` on a raw shape and wrote geometry-less STEP) is fixed to the Shape method, so STEP now carries real B-rep — single-body STEP stays deterministic and now re-imports with full geometry.
- **SC-006**: The CLI can write every format (existing + new), gzip any of them, and export the full assembly for multi-body formats.
- **SC-007**: An invalid extension, empty body, or degenerate DXF projection raises a clear `ExportInputError`/`ExportWriteError` rather than writing a corrupt or empty file.
- **SC-008**: Export time stays at human-scale (seconds), consistent with the existing export suite budget.

## Assumptions

- **Reproducibility policy (gate, spike-driven)**: every new format is on by default ONLY if the pre-implementation spike proves it byte-reproducible (after scrubbing generator strings / timestamps / handles). A format that cannot be made byte-identical (most likely glTF or DXF, which embed generator metadata) is either (a) shipped with a documented determinism caveat behind an explicit opt-in, or (b) deferred — `/clarify` will fix the policy. The deterministic formats (OBJ text, IGES with a scrubbed global section, gzip with zeroed mtime) are expected to pass.
- **Assembly definition**: the assembly is the set of top-level bodies in the build document (hull + deck superstructure + interior compartments + propulsion), combined into one compound (B-rep) or one merged mesh (mesh formats), ordered deterministically by the spec 002 sub-shape sort. The single-body export functions stay as-is; assembly export is a new function or an additive parameter.
- **DXF projection**: the 2D profile defaults to the boat's side (profile) view — projection onto the X-Z plane (the silhouette the reference photos show). The projection plane is a parameter with that default.
- **Format library support**: glTF/OBJ/IGES/DXF use FreeCAD's native exporters (Mesh/Part/Draft/import* modules); no new third-party dependency. Mesh formats reuse the spec 002 `_build_canonical_mesh` for deterministic facet ordering.
- **gzip**: deterministic gzip via a zeroed mtime and no embedded filename; composes with any format by wrapping the final bytes before the atomic write.
- **Scope boundary**: this spec broadens export only; it does not change hull/deck/interior/propulsion geometry. Full-assembly applies to the non-FCStd formats (FCStd already carries the whole document).
- **Verification host**: geometry/export tests require FreeCAD 1.1+ (bundled-Python `PYTHONPATH`); unit-only validation (extension checks, gzip determinism, parameter validation) runs without FreeCAD where possible.
