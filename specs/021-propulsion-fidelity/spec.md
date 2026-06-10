# Feature Specification: Propulsion Fidelity (CAD-faithful machinery)

**Feature Branch**: `021-propulsion-fidelity`

**Created**: 2026-06-10

**Status**: Draft

**Input**: User description: "021-propulsion-fidelity — Promote the spec 014 propulsion bodies from placeholder to CAD-faithful: airfoil/NACA propeller blade sections, NACA rudder foil, shaft coupling flange + strut bearings, detailed diesel engine block, and a manifold-safe additive-boss through-hull shaft-log fairing. Closes the six spec 014 deferrals."

## User Scenarios & Testing *(mandatory)*

A library consumer (restorer, scale modeler, FreeCAD scripter) calls `build_propulsion(hull, deck)` and gets a propulsion train whose parts read as real marine machinery on screen and in exported STEP/STL, not as the spec 014 stylized boxes-and-rectangles placeholder. Every part stays a single closed solid that exports cleanly, every dimension is an editable parameter, and two identical builds produce byte-identical output. The consumer can opt any single part back to its spec 014 placeholder form, or off entirely, without breaking the rest of the train.

### User Story 1 - Airfoil-accurate propeller blades (Priority: P1)

The propeller blades are the most visually scrutinized part of the running gear. Today each blade is a flat radial rectangle that reads as a toy. The consumer wants each blade to present a recognizable foil cross-section that twists from root to tip (pitch distribution), with a rounded hub, so the propeller reads as a real screw in side and aft views.

**Why this priority**: The propeller is the showpiece of the running gear and the single biggest perceptual gap between "placeholder" and "CAD model". It is also the highest-risk geometry (lofted foil sections), so it leads — if its reproducibility/manifold gate fails, the fallback is the existing spec 014 blade and the rest of the spec is unaffected.

**Independent Test**: Build with only the propeller upgraded (other parts left at spec 014 form); confirm each blade body is a single closed valid solid, exports to STL, the blade cross-section near mid-span is a foil (chordwise thickness peaks away from both edges, not a constant-thickness slab), the blade is twisted (root and tip chord lines differ in angle), and two builds are byte-identical.

**Acceptance Scenarios**:

1. **Given** default twin-screw parameters, **When** `build_propulsion(hull, deck)` runs, **Then** each propeller body has exactly one solid, is valid, exports to STL, and contains a rounded hub plus `blade_count` foil-section blades.
2. **Given** a mid-span chordwise section of one blade, **When** its thickness profile is sampled, **Then** the maximum thickness occurs in the interior of the chord (a foil), and the leading/trailing regions are thinner than mid-chord.
3. **Given** the root and tip sections of one blade, **When** their chord-line orientations are compared, **Then** they differ by a non-zero twist (pitch) angle.
4. **Given** `propeller.airfoil_blades=False` (or the equivalent opt-out), **When** the build runs, **Then** the propeller reproduces the spec 014 flat-rectangle blades byte-for-byte.
5. **Given** the airfoil loft fails to produce a single valid solid on this host, **When** the build runs, **Then** the propeller falls back to the spec 014 flat blade for that body, the build still succeeds, and the result is still a single valid solid.

---

### User Story 2 - Detailed diesel engine block (Priority: P2)

The engine block is the largest single mass in the bilge. Today it is a plain rectangular box. The consumer wants a recognizable marine-diesel silhouette — a stepped block with an oil sump at the bottom, a cylinder head + valve cover on top, and exhaust-manifold stubs along one side — so the engine reads as a diesel, not a crate.

**Why this priority**: Large visual mass, second-biggest perceptual win after the propeller, and lower geometric risk (additive boxes/cylinders fused onto the existing block, all analytic primitives like spec 024's contoured fittings, so reproducibility is not at risk).

**Independent Test**: Build with only the engine upgraded; confirm the engine body is a single closed valid solid with a distinct sump (narrower lower section), a raised head/valve-cover feature on top, and `manifold_stub_count` cylindrical stubs on one side; confirm two builds are byte-identical.

**Acceptance Scenarios**:

1. **Given** default parameters, **When** the build runs, **Then** the engine body is a single valid solid whose silhouette is more articulated than the plain spec 014 box (sump below the main block, head/valve cover above it).
2. **Given** the engine detail, **When** the side with manifold stubs is inspected, **Then** `manifold_stub_count` cylindrical stubs protrude from that face and fuse into the block as one solid.
3. **Given** `engine.detailed=False`, **When** the build runs, **Then** the engine reproduces the spec 014 plain box byte-for-byte.
4. **Given** the detailed engine, **When** its envelope is checked against the hull, **Then** the existing spec 014 within-hull-envelope guard still holds (the added detail does not push the engine through the topsides or above the clearance ceiling).

---

### User Story 3 - NACA rudder foil (Priority: P2)

Today the rudder blade is a flat plate with square edges. The consumer wants the blade to be a symmetric NACA foil section (rounded leading edge, tapering to a fine trailing edge) extruded over the span, so the rudder reads as a hydrodynamic foil.

**Why this priority**: High perceptual return for low geometric risk — a single symmetric foil section extruded straight along the span (no twist, no loft between differing sections), so it is far less reproducibility-sensitive than the propeller blade loft.

**Independent Test**: Build with only the rudder upgraded; confirm the rudder body is a single closed valid solid, the blade cross-section is a symmetric foil (rounded leading edge, thin trailing edge, max thickness in the forward third), and two builds are byte-identical.

**Acceptance Scenarios**:

1. **Given** default parameters, **When** the build runs, **Then** the rudder body is a single valid solid combining a NACA-foil blade and a vertical stock.
2. **Given** a chordwise section of the rudder blade, **When** its thickness profile is sampled, **Then** the leading edge is rounded, the trailing edge is much thinner than the maximum thickness, and the maximum thickness is in the forward portion of the chord (a symmetric NACA section).
3. **Given** `rudder.naca_foil=False`, **When** the build runs, **Then** the rudder reproduces the spec 014 flat plate byte-for-byte.

---

### User Story 4 - Shaft coupling flange + strut bearings (Priority: P3)

Today the shaft is a bare tilted cylinder with a fat stern-tube boss. The consumer wants a bolted coupling flange at the forward (engine) end where the shaft meets the gearbox, and a P-bracket / strut bearing partway along the exposed shaft run that visually supports the shaft below the hull, so the running gear reads as a real installation.

**Why this priority**: Adds realism and "reads as a real installation" detail, but the coupling and strut are small relative to the propeller and engine; low geometric risk (analytic discs/cylinders fused onto or seated near the shaft).

**Independent Test**: Build with only the shaft assembly upgraded; confirm a coupling-flange feature (a disc larger than the shaft diameter, with bolt-hole or bolt-boss detail) exists at the forward shaft end, a strut/P-bracket body supports the shaft mid-run, both are single valid solids, and two builds are byte-identical.

**Acceptance Scenarios**:

1. **Given** default parameters, **When** the build runs, **Then** the shaft body carries a coupling flange (a coaxial disc of diameter > shaft diameter) at its forward end, and the shaft remains a single valid solid.
2. **Given** default parameters, **When** the build runs, **Then** a strut/P-bracket body is present along the exposed shaft run, is a single valid solid, and its top reaches up toward the hull bottom (it visually supports the shaft).
3. **Given** `shaft.coupling_flange=False` and `shaft.strut_bearing=False`, **When** the build runs, **Then** the shaft reproduces the spec 014 cylinder + stern-tube boss byte-for-byte and no strut body is produced.

---

### User Story 5 - Through-hull shaft-log fairing (Priority: P3)

Where the shaft exits the hull bottom, today there is only the fat stern-tube boss on the shaft. The consumer wants a faired shaft-log — a smooth additive fairing around the shaft exit that blends the shaft into the hull bottom — so the exit reads as a real through-hull, **without ever cutting the hull** (the hull stays a single closed solid; the literal hull cavity remains out of scope per the manifold discipline).

**Why this priority**: Small geometric addition, completes the running-gear story, lowest perceptual return of the five, so it is last.

**Independent Test**: Build with only the fairing added; confirm a fairing body exists around the shaft-exit station, it is a single valid solid, it is additive (the hull body's shape/volume is unchanged — `hull_modified` stays `False`), and two builds are byte-identical.

**Acceptance Scenarios**:

1. **Given** default parameters, **When** the build runs, **Then** a faired shaft-log body surrounds the shaft near its hull-exit station and is a single valid solid.
2. **Given** the build with the fairing, **When** the hull body is inspected, **Then** its shape and volume are unchanged from a build without propulsion (the hull is never booleaned; `Propulsion.hull_modified == False`).
3. **Given** `shaft.shaft_log_fairing=False`, **When** the build runs, **Then** no fairing body is produced and the shaft reproduces the spec 014 form byte-for-byte.

---

### Edge Cases

- **Reproducibility regression (the spec 022 wall)**: a lofted foil blade whose volume drifts under cumulative FreeCAD/OCC process state would break byte-determinism (constitution II). The detailed geometry MUST be empirically proven byte-reproducible across repeated builds before it ships; if a construction cannot be made reproducible, it is gated behind a flag whose default preserves determinism.
- **Non-manifold loft**: a foil-section loft that produces zero or multiple solids, or an invalid shape, MUST fall back to the spec 014 placeholder for that component rather than failing the whole build or shipping a broken solid.
- **STL export**: every produced body MUST remain STL-exportable (a watertight mesh) — the spec 009/018 bilge-arc non-watertight-mesh failure mode must not recur.
- **Single vs twin screw**: detailed parts apply identically to both trains; the twin layout mirrors port/starboard as in spec 014.
- **Backward compatibility**: existing callers of `build_propulsion` and existing consumers of the `Propulsion` aggregate and its component wrappers continue to work; new parameters are additive with defaults, and every detailed part can be switched back to its spec 014 form.
- **Engine envelope**: the detailed engine block must not push the engine through the hull topsides or above the clearance ceiling that the spec 014 within-hull-envelope guard checks.
- **Tiny/degenerate parameters**: foil thickness, flange diameter, strut dimensions etc. that are non-positive or non-finite are rejected with a parameter error before any FreeCAD call (spec 014 validation idiom).

## Clarifications

### Session 2026-06-10

- Q: Default for the detailed geometry — on by default, or opt-in per part? → A: ON by default; each detailed part has a per-part flag; a manifold-or-fallback gate (FR-010) guards every construction; a specific construction flips to opt-in (default off) only if its pre-implementation reproducibility spike fails.
- Q: Propeller blade foil section type — symmetric NACA or cambered? → A: Symmetric NACA sections stacked with a radial pitch/twist and chord-taper distribution; true camber is deferred (asymmetric-section loft adds reproducibility risk for marginal perceptual gain).
- Q: How do the new detail parts attach (body topology / aggregate shape)? → A: The coupling flange and the shaft-log fairing fuse into the existing shaft body as coaxial bosses; the engine sump, head/valve-cover, and manifold stubs fuse into the existing engine body; the strut / P-bracket is a SEPARATE new top-level body (new `Strut` wrapper + `struts` list on the `Propulsion` aggregate), because it bridges the tilted shaft to the hull bottom and cannot fuse cleanly (the spec 022/023 separate-body precedent).
- Q: Gate-failure behavior — what happens when a detailed construction fails its manifold gate? → A: Core parts (propeller, rudder, engine) fall back to their spec 014 placeholder form; optional support bodies (strut, fairing) are omitted entirely (the build still succeeds); in all cases every produced body is a single valid solid.
- Q: Reproducibility verification gate? → A: A pre-implementation FreeCAD spike MUST prove each detailed construction byte-reproducible — identical volume across ≥3 repeated builds, mirroring the spec 022/024 spike discipline — before that construction ships on-by-default; any construction that fails becomes opt-in (default off).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST replace the spec 014 flat radial propeller blade with a blade presenting a **symmetric NACA foil** cross-section that varies in pitch/twist from root to tip (radial pitch/twist + chord-taper distribution), retaining the parametric `blade_count` and the existing hub. (Cambered sections are out of scope — see Clarifications Q2.)
- **FR-002**: The system MUST replace the spec 014 flat rudder plate with a symmetric NACA foil section (rounded leading edge, fine trailing edge, max thickness forward of mid-chord) extruded over the rudder span, retaining the vertical stock.
- **FR-003**: The system MUST add a coupling flange (a coaxial disc larger than the shaft diameter, with bolt detail) at the forward end of the shaft, **fused into the existing shaft body** as a coaxial boss (the shaft stays one solid).
- **FR-004**: The system MUST add a strut / P-bracket bearing as a **separate new top-level body** along the exposed shaft run that visually supports the shaft toward the hull bottom; it is exposed via a new `Strut` wrapper and a `struts` list on the `Propulsion` aggregate (additive — see Clarifications Q3).
- **FR-005**: The system MUST replace the spec 014 plain engine box with a detailed marine-diesel block: an oil sump (narrower lower section), a cylinder head + valve cover (raised top feature), and a parametric number of exhaust-manifold stubs on one side, all fused into one solid.
- **FR-006**: The system MUST add an additive faired shaft-log around the shaft's hull-exit station, **fused into the existing shaft body** as a coaxial boss; the hull body MUST NOT be booleaned and `Propulsion.hull_modified` MUST remain `False`.
- **FR-007**: Every produced body MUST be a single closed valid solid (`len(Shape.Solids) == 1` and `Shape.isValid()`) and MUST be STL-exportable, exactly as the spec 014 manifold guard requires.
- **FR-008**: Two builds with identical inputs MUST produce byte-identical geometry (constitution II). Before any detailed construction ships on-by-default, a pre-implementation FreeCAD spike MUST prove it byte-reproducible (identical volume across ≥3 repeated builds, per the spec 022/024 spike discipline — see Clarifications Q5). Any construction that fails the spike MUST default to OFF (opt-in), preserving byte-determinism for the default build.
- **FR-009**: Each detailed part MUST be independently switchable back to its spec 014 placeholder form (per-part opt-out flags) and the whole propulsion train MUST remain opt-out-able as in spec 014; with all detail flags off, the output MUST be byte-identical to the spec 014 build.
- **FR-010**: If a detailed construction fails to yield a single valid solid on the host, the manifold-or-fallback gate MUST keep the overall build succeeding with valid solids: a **core part** (propeller, rudder, engine) falls back to its spec 014 placeholder form; an **optional support body** (strut, fairing) is omitted entirely (see Clarifications Q4).
- **FR-011**: Every new dimension MUST be a named parameter with a default (constitution I); no magic numbers in function bodies. New parameters MUST be validated (positive/finite/in-range) before any FreeCAD call, raising the spec 014 `PropulsionParameterError`.
- **FR-012**: The public `build_propulsion` signature and the `Propulsion` aggregate MUST stay backward-compatible; new public parameter types/fields are additive only. The CLI build path MUST continue to work unchanged (detailed geometry on by the chosen default).
- **FR-013**: Construction MUST stay FreeCAD-idiomatic (PartDesign / Part / Sketch features; no raw mesh generation outside the export adapters), consistent with constitution III and the spec 014 idiom.
- **FR-014**: The detailed parts MUST apply identically to single-screw and twin-screw layouts; the twin layout mirrors port/starboard as in spec 014.
- **FR-015**: The literal through-hull *cavity* (a boolean recess into the hull) remains OUT OF SCOPE and stays deferred; FR-006's additive fairing is its manifold-safe substitute. Colors/materials remain owned by spec 015 (already applied via render roles) and are OUT OF SCOPE here except for assigning render roles to any newly created top-level bodies (e.g. the strut and fairing) consistent with the existing propulsion palette.

### Key Entities

- **Propeller blade (foil)**: a blade whose cross-sections are symmetric NACA foil profiles stacked along the radius with a pitch/twist distribution and chord taper, replacing the flat rectangle; bounded by `blade_count`, hub diameter, and disc diameter. Fused into the propeller body.
- **Rudder foil**: a symmetric NACA section (defined by a thickness ratio) extruded over the rudder span, plus the existing stock. Fused into the rudder body.
- **Coupling flange**: a coaxial disc at the forward shaft end with bolt detail, larger than the shaft diameter. Fused into the shaft body.
- **Strut / P-bracket bearing (NEW BODY)**: a separate top-level support body bridging the shaft to the hull bottom along the exposed run; exposed via a new `Strut` wrapper and a `struts` list on the `Propulsion` aggregate.
- **Diesel engine detail**: sump + head/valve-cover + manifold stubs fused into the existing engine block body.
- **Shaft-log fairing**: an additive faired boss around the shaft-exit station, fused into the shaft body; never a hull cut.
- **Detail toggles**: per-part flags on the existing propulsion parameter dataclasses controlling detailed-vs-placeholder construction (default ON, gated).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With default parameters, 100% of produced propulsion bodies are single closed valid solids and the full assembly exports to STL without error (no regression vs spec 014).
- **SC-002**: Two consecutive default builds produce byte-identical geometry (volume and exported-shape hash equal) for every detailed component.
- **SC-003**: A mid-span propeller-blade chordwise section is a foil (max thickness occurs in the chord interior, both edges thinner) and the root-to-tip twist angle is non-zero — verifiable from the exported shape without inspecting source.
- **SC-004**: A rudder-blade chordwise section is a symmetric NACA foil (rounded leading edge, trailing edge thinner than 30% of max thickness, max thickness forward of mid-chord).
- **SC-005**: The detailed engine body's articulation is measurable (sump section narrower than the main block; head/valve-cover feature raises the top; `manifold_stub_count` stubs present) versus the plain spec 014 box.
- **SC-006**: With every detail flag off, the build output is byte-identical to the spec 014 build (the placeholder is exactly preserved).
- **SC-007**: The hull body's shape and volume are identical between a build with propulsion and one without (the hull is never booleaned); `hull_modified == False`.
- **SC-008**: Build time stays at human-scale (seconds-to-low-minutes, consistent with the existing geometry suite budget); no detailed part introduces a non-watertight mesh.

## Assumptions

- **Default-on, gated**: detailed geometry is ON by default (the CLI and default `build_propulsion` produce the CAD-faithful train), each detailed construction guarded by a manifold-or-fallback gate (FR-010) and proven byte-reproducible before shipping (FR-008). If the pre-implementation reproducibility spike shows a specific construction (most likely the lofted propeller blade) cannot be made byte-reproducible, that construction's default flips to OFF (opt-in), mirroring the spec 022 rubrail-rounded-profile precedent — the per-part flag exists either way. (`/clarify` will confirm the default direction.)
- **Foil math**: symmetric foils use the NACA 4-digit symmetric half-thickness formula; the propeller blade uses foil sections (symmetric or lightly cambered) stacked with a pitch/twist and chord-taper distribution. Exact NACA series numbers and twist law are parameters with sensible marine defaults (e.g. rudder ≈ NACA 0018-class thickness), not hard-coded magic.
- **Dense Ruled=True lofts, not Ruled=False**: per the spec 018/020 empirical wall (Ruled=False AdditiveLoft overshoots), lofted blades use dense `Ruled=True` sections so the part reads smooth while staying exact and manifold; true B-spline skinning stays out of scope (constitution III + the recorded infeasibility).
- **Additive only**: every detail is additive (fused onto existing bodies or seated as new bodies); the hull is never booleaned (FR-006), consistent with specs 009/011/014/018.
- **Render roles**: any newly created top-level body (strut, fairing) is assigned a spec 015 render role consistent with the existing engine/shaft/propeller/rudder palette; no new material work.
- **Reuse**: the spec 014 `build_propulsion` orchestration, train resolution, validation idiom, rollback, and manifold guard are reused; this spec changes the per-component builders and adds parameters, not the public entry point.
- **Verification host**: geometry tests require FreeCAD 1.1+ (run via the bundled-Python `PYTHONPATH` as in prior specs); unit-only validation (parameter dataclasses, foil-math helpers) runs without FreeCAD.
