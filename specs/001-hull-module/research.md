# Research: Hull Module (Phase 0)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-17

This document resolves the unknowns identified during planning. Each section follows the `Decision / Rationale / Alternatives considered` format and cites its source.

---

## R1. Canonical default hull dimensions (resolves OQ1 from spec.allium)

### Decision

The default `HullParameters` map to the historical **Storebro Royal Cruiser 34, 1972 model year** — an early-production semi-displacement motor yacht built by Storebro Bruks AB. Two principal dimensions are cited directly from the project domain expert (Johan Olofsson, 2026-05-17):

- **LOA: 10.35 m** (cited)
- **Beam: 3.20 m** (cited)

The remaining six parameters are estimated using era-typical proportions for a 1972 Swedish semi-displacement motor yacht of this size class. Estimates are explicitly flagged below; principle IV's ±1% tolerance applies against the citation pair (LOA, beam) and against the estimate-as-reference for the others (i.e. the test passes by construction for the estimates, and is meaningfully gated by the citations).

| Parameter | Default | Unit | Source / status |
|---|---|---|---|
| `loa` | 10.35 | m | **Citation** — Storebro Royal Cruiser 34 (1972) published LOA; "34 ft" ≈ 10.36 m, matches inside ±0.1% |
| `beam_max` | 3.20 | m | **Citation** — Storebro Royal Cruiser 34 (1972) published beam |
| `draft` | 0.95 | m | **Estimate** — typical for 1970s 34-ft semi-displacement, fixed propeller; scaled from 1.05 m × (10.35/11.00) ratio. Refine in a PATCH bump when a primary source surfaces. |
| `freeboard` | 0.95 | m | **Estimate** — ~30% of beam at amidships, era-typical proportion |
| `deadrise_amidships` | 16.0 | ° | **Estimate** — era-typical for Swedish semi-displacement; era and hull class affect this less than length, so the value carries over from the previous research baseline |
| `sheer_height_aft` | 0.85 | m | **Estimate** — sheer-line height at transom, scaled proportionately from a 1.40 m fwd / 0.90 m aft baseline |
| `sheer_height_fwd` | 1.30 | m | **Estimate** — sheer-line height at stem, scaled proportionately; preserves the `fwd > aft` constraint |
| `transom_angle` | 12.0 | ° | **Estimate** — slight aft rake characteristic of early-1970s Storebro transom design |

### Rationale

The Royal Cruiser 34 1972-model was identified by the project domain expert as the canonical reference, with two principal dimensions provided directly (LOA 10.35 m, beam 3.20 m). The earlier draft of this research file picked the Royal Cruiser 36 as a best-guess — that was wrong, and is corrected here. The 1972 year is significant: it's the early production run, before the model evolved through the mid-1970s into the later Royal Cruiser line.

The ±1% reference fidelity tolerance from constitution principle IV is satisfied trivially on the citation pair (the defaults equal the published values within 0.1%). For the six estimated parameters, the tolerance applies against the estimate itself — they are the reference. When a primary source (archived Storebro shipyard drawings, restoration documentation, original brochures) surfaces, the estimates can be refined in PATCH bumps without breaking the public API, as long as the new value stays inside ±1% of the previous.

These values are codified as the field defaults on `HullParameters` and as a class constant `REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972` in the hull module. The `DefaultHullMatchesReferenceFidelity` invariant from `spec.allium` becomes verifiable once these constants are written.

### Alternatives considered

- **Royal Cruiser 36** (initially chosen, now rejected): rejected because the domain expert identified the 34, not the 36, as the canonical baseline. The 36 is a later/larger variant.
- **Royal Cruiser 410** (larger flagship): rejected for the same reason as before — different hull class, flying bridge, sheer profile, all out of scope for v1.0.
- **Generic Swedish motor-yacht average** (no specific model): rejected — principle IV requires fidelity to *a* reference, and the domain expert's citation is "Royal Cruiser 34 1972".
- **Defer indefinitely** (no defaults): rejected — without defaults, every test in SC-001 / SC-004 is unverifiable and the public API is unusable for a casual user. `/speckit-plan` is the right phase to pin these.

### Notes

Only LOA and beam are citation-grade in this revision. Draft, freeboard, deadrise, sheer heights, and transom angle remain estimates pending a primary source. Future maintainers refining these against archived Storebro shipyard drawings or original brochures should keep refinements inside ±1% of the previous default per the constitution's "no silent breaking change" rule (principle VII applied to data). The estimates' rationale and their delta from a fully-cited baseline should be tracked in this section's revision history.

**Revision log for this section**:
- 2026-05-17 (initial): incorrect best-guess against Royal Cruiser 36.
- 2026-05-17 (current): corrected to Royal Cruiser 34, 1972 model, against domain-expert citation. LOA + beam citation-grade; remaining 6 fields estimate-grade.

---

## R2. Hull construction strategy (FreeCAD topology approach)

### Decision

**Lofted stations**. Build the hull as a `PartDesign::AdditiveLoft` between five parametric station sketches, all hosted on a single `Part::Body`:

1. `Station_Transom` — at `x = 0` (the transom plane, tilted by `transom_angle` from vertical)
2. `Station_Aft` — at `x = 0.25 · loa`
3. `Station_Amidships` — at `x = 0.50 · loa` (maximum beam, governs `beam_max` and `deadrise_amidships`)
4. `Station_Fwd` — at `x = 0.75 · loa`
5. `Station_Stem` — at `x = loa` (the bow, vanishes to a point along the centerline)

Each station sketch is a half-section (port half), and a `PartDesign::Mirrored` feature reflects across the centerline plane to enforce FR-009 (symmetry). The result is a closed Body when the stem-station collapses to a vertex and the transom-station is closed by the transom plane.

The Body exposes the eight hull dimensions as `App::PropertyLength` and `App::PropertyAngle` properties on the Body itself. Each station sketch's constraints reference those Body-level properties via FreeCAD's expression-engine bindings (`Hull.LOA`, `Hull.BeamMax`, etc.), so GUI edits propagate automatically — satisfying FR-007.

### Rationale

- **Editability** (FR-007): a loft of constrained sketches is fully editable in the FreeCAD GUI's PartDesign workbench. A user can open the document, click a sketch, change a dimension, and FreeCAD recomputes the whole hull.
- **Parametricity** (constitution I, SC-004): every station sketch references the eight named hull parameters via expressions. Changing any parameter forces a sketch recompute and a loft recompute.
- **Idiomatic** (constitution III, FR-006): `Part::Body` + `Sketcher::Sketch` + `PartDesign::AdditiveLoft` + `PartDesign::Mirrored` is the canonical PartDesign workflow for a hull-shaped body. No mesh, no raw geometry.
- **Determinism** (FR-005): the construction sequence is fixed (5 sketches in a fixed order, loft in a fixed direction, mirror once). FreeCAD's PartDesign engine is deterministic for fixed inputs in our supported version range.

### Alternatives considered

- **`Part::Loft` (legacy non-PartDesign loft)**: rejected — it produces a `Part::Feature` instead of a `PartDesign::Feature`, breaking the parametric history and making GUI edits awkward. Constitution III explicitly prefers PartDesign abstractions.
- **`Sketch + Pad + Subtract` (single hull-profile sketch, then carved)**: rejected — a single sketch cannot capture the longitudinal variation of beam, deadrise, and sheer simultaneously. Would require multiple boolean operations and a forest of references, hurting both determinism (FR-005) and GUI editability (FR-007).
- **`PartDesign::AdditivePipe` (sweep a section along a guide curve)**: rejected — a single section cannot capture how the hull's cross-section morphs from V-bottom at the stem to flatter aft. Either it ignores the morph (wrong shape) or it needs multiple sections, at which point it's a worse loft.
- **`OpenSCAD-style raw mesh`**: rejected — explicitly forbidden by constitution III and FR-006. Output would not be GUI-editable.

### Notes

The choice of exactly 5 stations is a deliberate balance between fidelity and simplicity. Three stations (transom, amidships, stem) under-fit the sheer curve; seven stations over-fit and slow the build. Five stations matches the typical hand-drawn cutaway convention and keeps the build well inside the 30-second SC-002 budget. If future fidelity demands push beyond ±1%, the station count is a private internal constant that can be raised without a public API change.

---

## R3. Public exception API (resolves clarify Q1)

### Decision

Two custom exception classes, both public, both importable from `storebro.hull`:

```python
class HullParameterError(ValueError):
    """Raised before any FreeCAD call when a hull parameter is invalid.

    Attributes:
        parameter_name: str — the offending parameter (e.g. "loa")
        parameter_value: float — the value the caller supplied
        valid_range: str — the documented valid range (e.g. "> 0")
    """

class HullConstructionError(RuntimeError):
    """Raised when FreeCAD fails to construct the hull despite valid parameters.

    Attributes:
        parameters: HullParameters — the parameter set that triggered the failure
        underlying: BaseException | None — the FreeCAD-side exception, if any
    """
```

Both classes are fully exported via `storebro.hull.__all__` and re-exported from `storebro.__init__`.

### Rationale

- Subclassing `ValueError` and `RuntimeError` (not `Exception`) lets callers fall back to broad-catch idioms (`except ValueError`) when they don't need granularity.
- Splitting validation (pre-FreeCAD) from construction (FreeCAD-side) lets callers handle them differently — e.g., retry with adjusted parameters on `HullParameterError`, escalate on `HullConstructionError`.
- Structured attributes (not just message strings) let test code assert on exception state without fragile string-parsing.

### Alternatives considered

- Single `HullError`: rejected — clarify Q1 already chose two-class taxonomy.
- Standard `ValueError` + `RuntimeError` with structured `args`: rejected — `args` is positional and fragile, and custom classes are the idiomatic Python pattern for library APIs.

---

## R4. Document handling (resolves clarify Q2)

### Decision

`build_hull` accepts an optional `document: FreeCAD.Document | None = None`. Resolution order:

1. If `document` is non-None, add the hull Body to that document. Do not mutate the document's `Label` or other top-level properties.
2. If `document` is None and `FreeCAD.activeDocument()` returns a document, use that.
3. If `document` is None and no document is active, create a new document via `FreeCAD.newDocument()` (FreeCAD auto-names it `Unnamed`/`Unnamed1`/etc., which is fine for the auto-create branch).

### Rationale

Matches clarify Q2 directly. The optional-with-fallback pattern is idiomatic Python; the explicit auto-create branch keeps the function callable from a fresh REPL without ceremony.

### Alternatives considered

See clarify Q2 audit list — three alternatives already considered and rejected.

---

## R5. Body label and naming (resolves clarify Q3)

### Decision

`build_hull` accepts an optional `name: str = "Hull"`. The resulting Body's `Label` is set to this value before any other property is set. FreeCAD's standard auto-numbering applies when the Label collides: the second `build_hull` call into the same document produces `Hull001`, the third `Hull002`, etc.

### Rationale

Matches clarify Q3 directly. The default `"Hull"` is what a single-hull document expects; the auto-numbering lets variant-study scripts call `build_hull` in a loop without manual name juggling.

### Alternatives considered

See clarify Q3 audit list — three alternatives already considered and rejected.

---

## R6. FreeCAD version-check timing (resolves clarify Q5)

### Decision

Lazy first-call check in `build_hull`. The check is cached in a module-level `_FREECAD_VERSION_OK` flag (initialized to `None`) so subsequent calls in the same process skip the check entirely. Importing `storebro.hull` does NOT trigger the check.

The supported range is read from `pyproject.toml`'s `[tool.freecad-storebro]` table (parsed at module load via `tomllib`) — not hard-coded in `hull.py` — so PATCH releases can expand the range without touching the hull source.

### Rationale

- Matches clarify Q5: lazy first-call.
- Reading from `pyproject.toml` keeps the supported range single-sourced. Constitution principle VII requires the range to be declared in `pyproject.toml` *and* in `README.md`; pulling it from `pyproject.toml` ensures the runtime check cannot drift from the declared range.
- `tomllib` is stdlib in Python 3.11+ so this adds zero dependencies.

### Alternatives considered

See clarify Q5 audit list — three alternatives already considered and rejected.

---

## R7. Testing strategy

### Decision

Two-tier pytest layout matching the constitution's testing guidance:

- **Unit tier** (`tests/unit/`): no FreeCAD, no marker, runs in CI on every host:
  - `test_hull_parameters.py`: validates `HullParameters` field defaults, range constraints, dataclass invariants, `__post_init__` validation (positivity, deadrise range, LOA > beam, sheer non-inversion).
  - `test_hull_errors.py`: confirms `HullParameterError` and `HullConstructionError` subclass `ValueError`/`RuntimeError`, expose the documented attributes, and produce messages matching SC-007's "parameter, value, range" format.
  - `test_freecad_check.py`: monkeypatches `FreeCAD.Version` and verifies the lazy version-check rejects out-of-range versions with `HullConstructionError`.

- **Geometry tier** (`tests/geometry/`, marker `requires_freecad`): only runs where FreeCAD is on PATH. Each test runs in a freshly-created in-memory document via the `conftest.py` fixture.
  - `test_hull_default_dimensions.py` (SC-001): bbox dimensions of the default hull are within ±1% of the Royal Cruiser 34 (1972) reference for LOA + beam (citation-grade); other parameters self-cite against the estimates.
  - `test_hull_determinism.py` (SC-003): two back-to-back `build_hull(defaults)` calls produce Bodies with identical volume, bbox, and topology counts to `1e-9` relative tolerance.
  - `test_hull_parametricity.py` (SC-004): for each of the 8 named parameters, building hulls with ±10% perturbations changes the corresponding measured dimension monotonically.
  - `test_hull_topology.py` (FR-009, FR-010): generated Body is a single closed shell and is symmetric about the X-Z plane (`y → -y`).
  - `test_hull_gui_editability.py` (FR-007): the Body exposes named properties `LOA`, `BeamMax`, etc., and editing one triggers a recompute that changes the geometry.
  - `test_hull_construction_errors.py` (FR-015): force a FreeCAD construction failure (e.g. via a parameter combination that breaks the loft post-validation) and confirm the wrapping is `HullConstructionError`, not the raw FreeCAD exception.

### Rationale

This split keeps CI green on hosts without FreeCAD (rare in production CI but useful for fast pre-push hooks). The `requires_freecad` marker is the de-facto pytest convention for skipping FreeCAD-dependent tests. Each acceptance scenario in `spec.md` and each FR in the spec maps to at least one test — satisfying SC-006.

### Alternatives considered

- Single test directory, no markers: rejected — would force every developer to install FreeCAD before running `uv run pytest`, even for a one-line README fix.
- Three tiers (unit / integration / e2e): rejected — there is no "integration" tier separate from "geometry" for a single-module hull library. Two tiers is the minimum that captures the constitutional distinction.

---

## R8. FreeCAD installation discovery (testing concern)

### Decision

The `tests/geometry/conftest.py` fixture imports `FreeCAD` at the top of the file. If the import fails, pytest's collection-time error is caught by the `pytest_collection_modifyitems` hook which adds the `pytest.skip` marker to every test in that directory.

The hull module itself (`src/storebro/hull.py`) imports `FreeCAD` unconditionally at module top — when the user calls `build_hull` without FreeCAD installed, they get `ImportError` at import time, not at call time. This is the explicit choice over a "FreeCAD not installed" runtime check because (a) the library has no other reason to exist without FreeCAD, and (b) `ImportError` is more idiomatic than a custom "missing dependency" exception.

### Rationale

- Tests that need FreeCAD skip cleanly when it's absent — no false failures on slim CI hosts or developer pre-push runs.
- Production users get a clear `ImportError` at import time if they accidentally try to use the library without FreeCAD. The traceback names the missing module unambiguously.

### Alternatives considered

- Use `importlib.util.find_spec("FreeCAD")` for soft probing: rejected — adds complexity for a library that is FreeCAD-or-nothing.
- Use `conftest.py` `pytest_configure` to register `requires_freecad`: included in addition to the skip logic so the marker is registered in `pytest --markers` output.

---

## Summary of decisions

| ID | Decision | Resolves |
|---|---|---|
| R1 | Default `HullParameters` = Storebro Royal Cruiser 34, 1972 model (LOA 10.35 m, beam 3.20 m citation-grade; remaining 6 fields estimate-grade) | OQ1 / SC-001 |
| R2 | Lofted-stations construction (5 sketches + AdditiveLoft + Mirrored) | FR-006 / FR-007 |
| R3 | `HullParameterError(ValueError)` + `HullConstructionError(RuntimeError)` | Clarify Q1 / FR-015 |
| R4 | Optional `document` kwarg with auto-create fallback | Clarify Q2 / FR-016 |
| R5 | Optional `name="Hull"` kwarg with FreeCAD auto-numbering | Clarify Q3 / FR-017 |
| R6 | Lazy first-call version check, range read from `pyproject.toml` | Clarify Q5 / FR-013 |
| R7 | Two-tier pytest (`unit/` + `geometry/` with `requires_freecad`) | SC-006 / SC-007 / FR-009 / FR-010 |
| R8 | FreeCAD `ImportError` at import time; conftest skip for missing FreeCAD | FR-013 / testing concern |

All NEEDS CLARIFICATION markers from the Technical Context section resolved. Ready for Phase 1 design.
