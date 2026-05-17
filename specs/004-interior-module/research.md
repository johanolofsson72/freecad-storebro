# Research: Interior Module (Phase 0)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-17

Resolves the unknowns identified during planning. Each section uses the `Decision / Rationale / Alternatives` format.

---

## R1. Canonical layout dimensions for Alternativ1-5 (resolves OQ1)

### Decision

Each of the five canonical layouts ships with a fixed compartment set defined in `src/storebro/fixtures/AlternativN.yaml`. The compartment counts and types per layout are estimate-grade against typical RC34 1972 floor-plan cutaways:

| Layout | Compartments (fore → aft) | Notes |
|---|---|---|
| **Alternativ1** | forward_cabin (V-berth), head, galley, salon (combined-aft) | 4 compartments. Most popular "live-aboard" arrangement. |
| **Alternativ2** | forward_cabin (V-berth), galley, head, salon | 4 compartments. Head moved aft for fly-bridge access (era variant). |
| **Alternativ3** | forward_cabin (V-berth), head (port), galley (starboard, side-by-side amidships), salon | 4 compartments. Canonical / default — most-photographed layout. |
| **Alternativ4** | forward_cabin, galley (small-amidships), head, salon (extended) | 4 compartments. Galley simplified; larger salon. |
| **Alternativ5** | forward_cabin, head, salon (galley integrated into salon) | 3 compartments. "Day-cruiser" variant — no separate galley. |

Each compartment has citation-grade `position` (forward-bottom-center per clarify Q3) and `dimensions` (length × width × height) measured from `docs/references/AlternativN.JPG`. The exact numbers are estimate-grade until a primary source surfaces; the cutaway is the visual citation per FR-020's `source` field.

Reference defaults (sampling Alternativ3, the canonical):
- Forward cabin: position `(0.5, 0, 0.6)`, dimensions `2.5 × 2.1 × 1.2`
- Head: position `(3.0, 0, 0.5)`, dimensions `1.2 × 1.0 × 1.4`
- Galley: position `(3.0, 0, 0.5)`, dimensions `1.2 × 1.0 × 1.4` (Y-offset wise, port/starboard side-by-side with head; but YAML position.y is 0 in v1.0 per clarify Q3 — the cabin shells in v1.0 abstract over this asymmetry by widening width)
- Salon: position `(4.2, 0, 0.5)`, dimensions `4.5 × 2.6 × 1.8`

Per-layout values pinned in the YAML fixtures during `/implement`; values are deliberately approximate to keep the v0.4.0-alpha shippable. Refinement to ±1% (matching hull/deck) is a v0.5.0 work item if reference scans become available.

### Rationale

Boating reference resources document the RC34 as a 4-cabin layout pattern with minor variations among the five "Alternativ" options shown in 1970s brochures. Without a primary source we cannot pin exact mm; estimate-grade is honest and sufficient for v0.4.0-alpha.

### Alternatives considered

- **Pin from primary source first**: rejected — there is no primary source in `docs/references/` beyond the cutaway JPGs themselves, and measuring the JPGs to mm precision requires scale calibration we don't have. Estimate is honest.
- **Build 4 layouts, defer one**: rejected — the five-layout offering is the project's identity. Ship all five.

---

## R2. YAML loader + schema validation strategy

### Decision

Use `PyYAML` for YAML parsing (third-party, added to `pyproject.toml` dependencies). Schema validation is done in pure Python — no external schema library (jsonschema, pydantic) for v0.4.0-alpha:

```python
def _load_and_validate_layout(source: str) -> LayoutSpec:
    # 1. Resolve source: canonical name -> importlib.resources fixture;
    #                    filesystem path -> open()
    # 2. yaml.safe_load
    # 3. Validate top-level: schema_version=1, layout_name, source, compartments
    # 4. For each compartment: validate name, type, position {x,y,z}, dimensions {length,width,height}
    # 5. Validate cross-compartment: unique names, position.y == 0
    # 6. Return LayoutSpec dataclass
```

Errors raise `InteriorParameterError` with `source`, `compartment_name`, `field`, and `reason` populated.

`yaml.safe_load` is mandatory — never `yaml.load` (the unsafe loader allows arbitrary Python object instantiation via tag injection).

### Rationale

- `PyYAML` is the de-facto Python YAML library; mature, well-maintained, on every supported platform.
- Hand-rolled validation is straightforward for a 14-field schema and avoids the heavyweight pydantic/jsonschema dependency. The trade-off: less expressive validation language, more explicit code. Worth it at this scale.
- `safe_load` is the security baseline — never compromise on this.

### Alternatives considered

- **`ruamel.yaml`**: rejected — preserves comments and ordering, useful for hand-editing but irrelevant for fixtures we only read. Adds dependency for no gain.
- **`pydantic`**: rejected for v0.4.0-alpha — pulls in a multi-MB dependency for one schema. Worth considering in v0.5.0+ if we add more schemas.
- **`jsonschema`**: rejected — JSON Schema is over-specified for our needs; the YAML schema is simple enough to validate inline.
- **`yaml.load(...)` with default loader**: rejected on security grounds — `safe_load` always.

---

## R3. Per-compartment construction strategy

### Decision

Each compartment is built as a single `Part::Feature` whose Shape is a `Part.makeBox(length, width, height)` translated to `(position.x, -width/2, position.z)`. The half-width offset puts the box centered on Y=0 (centerline), matching FR-009 + clarify Q3's "forward-bottom-center" reference.

```python
def _build_compartment(spec: CompartmentSpec, target_doc, added) -> Compartment:
    import FreeCAD, Part
    half_w = spec.dimensions.width / 2.0
    box = Part.makeBox(
        spec.dimensions.length,
        spec.dimensions.width,
        spec.dimensions.height,
    )
    box.translate(FreeCAD.Vector(spec.position.x, -half_w, spec.position.z))

    obj = target_doc.addObject("Part::Feature", _compartment_label(spec, layout_name))
    obj.Shape = box
    added.append(obj)

    # FR-007: expose dimensions as named properties for GUI editing.
    obj.addProperty("App::PropertyLength", "Length", "Compartment", "Compartment length")
    obj.addProperty("App::PropertyLength", "Width", "Compartment", "Compartment width")
    obj.addProperty("App::PropertyLength", "Height", "Compartment", "Compartment height")
    obj.Length = spec.dimensions.length * 1000.0
    obj.Width = spec.dimensions.width * 1000.0
    obj.Height = spec.dimensions.height * 1000.0

    return Compartment(spec=spec, body=obj)
```

### Rationale

Boxes are the simplest parametric form that fits FR-007 (editable in GUI) and FR-009 (centerline-symmetric by construction when Y is centered at 0). They produce closed shells (volume > 0, isClosed() True) suitable for the SC-008 envelope-fit test.

### Alternatives considered

- **Curved bulkheads following the hull**: deferred to v1.1+ (spec assumption). Boxes are visually approximate but geometrically tractable.
- **`PartDesign::Body` per compartment** (matching v0.2.0 upgrade pattern from spec 001): considered for consistency. Stick with `Part::Feature` for v0.4.0-alpha because all four compartment types share the same construction; the PartDesign upgrade is uniform across the project's v0.2.0 milestone.

---

## R4. Envelope validation (FR-010, SC-009)

### Decision

Before any FreeCAD construction, validate each compartment against the hull's parameters:

```python
def _validate_compartment_in_envelope(spec: CompartmentSpec, hull: Hull) -> None:
    hp = hull.parameters
    if spec.position.x < 0:
        raise InteriorParameterError(...)
    if spec.position.x + spec.dimensions.length > hp.loa:
        raise InteriorParameterError(...)
    if spec.dimensions.width > hp.beam_max:
        raise InteriorParameterError(...)
    # Z (vertical) check: floor must be at or above keel (-hp.draft) and
    # ceiling at or below sheer + freeboard (top of cabin trunk if amidships).
    if spec.position.z < -hp.draft:
        raise InteriorParameterError(...)
    if spec.position.z + spec.dimensions.height > hp.sheer_height_fwd + 1.5:  # 1.5 m headroom for cabin trunk
        raise InteriorParameterError(...)
```

Post-FreeCAD verification (SC-009): for each compartment Body in the resulting `Interior`, assert that its `body.Shape.BoundBox` is fully inside the hull's `body.Shape.BoundBox`. This is a geometric check, not just a parameter check; catches drift between YAML and rendered geometry.

### Rationale

Parameter-level checks reject 90% of bad layouts before any FreeCAD call. The post-build geometric check catches the remaining 10% (e.g., compartments that fit the bbox but clip a curved hull section). Two-stage validation is robust and well-aligned with FR-004.

### Alternatives considered

- **Skip parameter checks; rely on post-build geometric check only**: rejected — the parameter check is cheaper and gives better error messages (cites the offending compartment + the specific constraint).
- **Use FreeCAD `Shape.common()` to intersect compartment with hull**: rejected for the parameter pass — too expensive to do per compartment before construction. Reserved for the post-build SC-009 verification step.

---

## R5. Overlap detection (FR-012)

### Decision

Pairwise volumetric overlap check between every pair of compartment specs BEFORE any FreeCAD construction:

```python
def _validate_no_overlaps(compartments: list[CompartmentSpec]) -> None:
    for i, c1 in enumerate(compartments):
        for c2 in compartments[i+1:]:
            overlap_vol = _aabb_intersection_volume(c1, c2)
            if overlap_vol > 1e-6:
                raise InteriorParameterError(...)

def _aabb_intersection_volume(c1: CompartmentSpec, c2: CompartmentSpec) -> float:
    # AABB intersection volume for two boxes centered on Y=0.
    # Per axis: max(0, min(c1.max, c2.max) - max(c1.min, c2.min))
    ...
```

Face-touching (intersection volume = 0) is permitted (clarify Q5). Shared bulkheads are the norm.

### Rationale

Both AABB and centered-on-Y=0 mean the check is just three independent axis-aligned interval intersections. O(N²) is fine for ≤ 4 compartments. The `1e-6 m³` threshold matches the spec.allium config `overlap_volume_threshold_m3`.

### Alternatives considered

- **R-tree or BVH for spatial indexing**: rejected — N=4 is too small to benefit.
- **FreeCAD-side `Shape.common()`**: rejected — overlap should be caught BEFORE construction per FR-004; pre-FreeCAD math is more honest.

---

## R6. Cross-module dependency surface (FR-011)

### Decision

`storebro.interior` imports the following:
- From `storebro.hull`: `Hull` (type only, for type hints + attribute access on `hull.parameters.loa`, etc.).
- From `storebro.deck`: `Deck` (type only, same reason).
- From `storebro._freecad_check`: `ensure_supported_freecad` (shared lazy version probe).
- From stdlib: `dataclasses`, `pathlib`, `importlib.resources`, `contextlib`, `time`.
- Third-party: `yaml` (PyYAML).
- FreeCAD: `FreeCAD`, `Part`.

It does NOT import `storebro.export`, `storebro.cli`. The leaf-module test enforces this via AST scan (matches spec 003's test pattern).

### Rationale

The dependency arrow is: `hull → deck → interior`. Export and CLI sit above interior in the eventual call graph. Importing them downward would create a cycle when CLI eventually imports interior.

### Alternatives considered

- **Generalize the type hints to `Protocol`** (avoid concrete imports): rejected — runtime `isinstance(hull, Hull)` checks need the concrete type; protocols are heavier without gain.

---

## R7. Rollback discipline (FR-018, SC-008)

### Decision

Same pattern as spec 003 R7: maintain an `added: list[FreeCAD.DocumentObject]` accumulator. Each compartment builder appends its created Body. On FreeCAD-side failure mid-build, the outer try/except calls `_rollback(target_doc, added)` which removes objects in reverse order with `contextlib.suppress(Exception)` per remove, then recomputes the document and raises `InteriorConstructionError(layout_name=..., hull=..., deck=..., underlying=exc)`.

### Rationale

Reuses the proven discipline from spec 003. The implementation is small enough to inline rather than extract to a shared helper — extraction risks coupling specs 003 and 004 in a way that breaks their leaf-module independence.

### Alternatives considered

- **Extract `_rollback` to `storebro._rollback` shared helper**: considered but rejected — the rollback closure-style pattern is tiny (~10 lines) and benefits from being inline (clear, no extra import). Future maintenance: if a fourth module needs the same discipline, refactor then.

---

## R8. PyYAML choice + dependency cost

### Decision

Add `PyYAML>=6.0` to `pyproject.toml` `[project.dependencies]`. This is the project's first third-party Python dependency.

### Rationale

- PyYAML is the standard. No realistic alternative.
- Version `>=6.0` because it added safe_load loader subclassing that the validator depends on, and dropped Python <3.6 support, both of which align with our 3.11+ minimum.
- The dependency is well-maintained, security-patched, and ships as wheels for every platform we target.

### Alternatives considered

- **Vendor a minimal YAML parser**: rejected — YAML is harder than it looks; security and edge cases would haunt us.
- **Switch fixtures to JSON to avoid YAML dependency**: rejected — YAML's human-authorability is the point of using it for hand-curated fixtures. JSON is unfriendly for that workflow.
- **Switch fixtures to TOML (stdlib `tomllib` in 3.11+)**: considered seriously. TOML works for flat structures but compartment lists with nested `position`/`dimensions` sub-dicts become awkward. YAML stays. (Hash baselines in spec 002 used TOML for the flat `key → sha256` pattern.)

---

## R9. Testing strategy

### Decision

Two-tier pytest layout matching spec 001/002/003:

- **Unit tier** (`tests/unit/test_interior_*.py`):
  - `test_interior_layout_loader.py`: YAML parse, schema validation, canonical-name resolution via `importlib.resources`, custom-path resolution, error-on-bad-version, error-on-missing-fields. Covers FR-002, FR-020, FR-021.
  - `test_interior_errors.py`: exception hierarchy, attribute shapes, message formats.
  - `test_interior_envelope_validator.py`: out-of-envelope per axis (x < 0, x + length > loa, width > beam, z < -draft, etc.). Covers FR-010 unit-level.
  - `test_interior_overlap_detector.py`: AABB intersection math, face-touching boundary cases. Covers FR-012 unit-level.
  - `test_interior_leaf_dependencies.py`: AST scan of `src/storebro/interior.py`. Covers FR-011.

- **Geometry tier** (`tests/geometry/test_interior_*.py`):
  - `test_interior_default_call.py`: build full whole-boat with `Alternativ3` default, assert four compartment Bodies, document binding correct.
  - `test_interior_all_five_layouts.py` (SC-006): parameterized over all five canonical names, each builds successfully on the default hull + deck. Verifies fixture wellformedness.
  - `test_interior_determinism.py` (SC-003): two back-to-back builds yield per-compartment identical volumes/bboxes.
  - `test_interior_envelope_fit.py` (SC-009): geometric containment — each compartment Body bbox fully inside `hull.body.Shape.BoundBox`.
  - `test_interior_construction_rollback.py` (SC-008): monkeypatch the 3rd-of-4 compartment builder to raise; assert no orphan Bodies after rollback.
  - `test_interior_visual_signoff.py`: build whole-boat with interior, export to `.FCStd` via spec 002's writer; print MANUAL SIGNOFF reminder.

### Rationale

Mirrors the project's two-tier convention; adds new test categories for the YAML loader and envelope/overlap validators (unit-tier because they don't need FreeCAD). Total test count target: ~40-60.

### Alternatives considered

- **Three tiers (unit/integration/geometry)**: rejected — see spec 003 R9; "integration" doesn't add signal here.

---

## Summary of decisions

| ID | Decision | Resolves |
|---|---|---|
| R1 | 5 canonical layouts as YAML fixtures, estimate-grade RC34 1972 dims | OQ1 / SC-001 / FR-003 |
| R2 | PyYAML safe_load + hand-rolled validator (no jsonschema/pydantic) | FR-004, FR-020, FR-021 |
| R3 | Per-compartment `Part.makeBox` translated to forward-bottom-center | FR-006, FR-007, FR-009 |
| R4 | Two-stage envelope validation (parameter pre-check + post-build geometric) | FR-010, SC-009 |
| R5 | Pairwise AABB intersection-volume check with 1e-6 m³ threshold | FR-012, clarify Q5 |
| R6 | Imports hull + deck + _freecad_check only; NOT export/cli | FR-011 |
| R7 | Reverse-order `removeObject` rollback (matches spec 003 R7) | FR-018, SC-008 |
| R8 | PyYAML>=6.0 as the project's first third-party dependency | FR-002, FR-020 |
| R9 | Two-tier pytest with new loader/validator/overlap categories | SC-005/006/007/008/009 |

All NEEDS CLARIFICATION markers resolved. Ready for Phase 1.
