# Phase 0 Research: Propulsion Fidelity

All "NEEDS CLARIFICATION" were resolved during `/clarify` (spec.md → Clarifications). This document records the geometric/technical decisions that gate implementation.

## R1 — NACA 4-digit symmetric foil section

**Decision**: Use the NACA 4-digit symmetric half-thickness distribution with a **closed trailing edge**:

```
yt(x) = 5·t·( 0.2969·√x − 0.1260·x − 0.3516·x² + 0.2843·x³ − 0.1036·x⁴ )
```

where `x = station/chord ∈ [0,1]`, `t = thickness ratio` (e.g. 0.12 → NACA 0012), `yt` = half-thickness as a fraction of chord. The section outline is the upper surface `+yt(x)` from leading→trailing edge then the lower surface `−yt(x)` back, closed into one loop. Scale by `chord_mm`.

**Rationale**: The last coefficient `−0.1036` (vs the open-TE `−0.1015`) makes `yt(1) = 0` exactly, so the trailing edge closes to a single point — a watertight, manifold section. Pure analytic function of `x` and `t`: identical inputs → identical points → byte-reproducible (constitution II). It is the canonical marine/aero symmetric foil, so the rudder (`t≈0.18`) and propeller sections (`t≈0.12`) read as real foils. Implemented as a pure-Python helper (`_naca_symmetric_half_thickness`, `_naca_section_polyline`) → unit-testable without FreeCAD.

**Alternatives considered**: Open-TE formula (rejected — leaves a finite-thickness TE that either needs an extra closing edge or yields a non-manifold sliver). 5-digit cambered series (rejected — camber deferred per clarify Q2; asymmetric sections raise loft risk). Elliptical section (rejected — not a recognizable foil).

## R2 — Loft reproducibility: the spec 022 wall, and how to avoid it

**Decision**: Build every foil cross-section as a **dense polyline** (`Part.LineSegment` chain through the analytic NACA points — NO `Sketcher.fillet()`, NO `Part.Arc`/`Part.Circle` in the foil outline) and loft with **`Ruled=True`**. The propeller blade is a `PartDesign::AdditiveLoft (Ruled=True)` through ≥2 such polyline sections; the rudder is a straight `PartDesign::Pad` of one polyline section (no loft at all).

**Rationale**: The spec 022 history records that the rubrail *rounded* profile's arc-loft volume **drifted** under cumulative FreeCAD/OCC state (two-open-docs determinism test: 36.4M vs 39.0M mm³), forcing the chamfer to be the byte-reproducible default. The decisive variable was the **Sketcher constraint solver** invoked by the arc/fillet — specs 018 (dense `Ruled=True` hull loft, n=31/81) and 020 (hardtop curl loft, n=3/7/13; swept rail) both used straight-segment sections and were byte-reproducible (`v1==v2` volume, 0% overshoot). A polyline foil contains no arcs and no solver, so it is in the reproducible class. `Ruled=True` (piecewise-linear between sections) is exact (0% overshoot) and manifold; `Ruled=False` (B-spline) is empirically dead for this codebase (spec 018 spike: 12–141% beam overshoot) and is NOT used.

**Verification (the mandated spike, clarify Q5)**: `/tmp/spike_021_*.py` builds each detailed construction ≥3× in fresh documents AND in the two-open-docs scenario (the exact spec 022 failure mode), asserting `Shape.Volume` is **byte-identical** across runs, `len(Solids)==1`, `isValid()`, and STL export succeeds. The spike result is recorded below and decides each construction's default. **A construction that drifts flips its default flag to OFF (opt-in)**, exactly as spec 022 did for `rounded_profile`.

**Spike result (T001, `/tmp/spike_021_repro.py`, FreeCAD 1.1.1, 2026-06-10) — ALL PASS, ALL DEFAULT ON:**

```
[x] rudder NACA-polyline Pad      vol=5468348.515  fresh×3 identical  2-open identical  solids=1 valid stl  -> ON
[x] propeller foil AdditiveLoft   vol=74739.209    fresh×3 identical  2-open identical  solids=1 valid stl  -> ON
[x] shaft coupling+bolts+fairing  vol=1976340.595  fresh×3 identical  2-open identical  solids=1 valid stl  -> ON
[x] strut separate body (barrel+arm) vol=491320.347 fresh×3 identical 2-open identical  solids=1 valid stl  -> ON
[x] detailed engine fused Pads    vol=546832000.0  fresh×3 identical  2-open identical  solids=1 valid stl  -> ON
```

**Conclusion**: the R2 thesis holds empirically — polyline foils (no Sketcher arcs/solver) + `Ruled=True` lofts are byte-reproducible even in the two-open-docs scenario that drifted spec 022's arc-loft rubrail. No construction flips to opt-in; clarify Q1 default-ON stands for all five. (The spike's engine builder validated the fused block/sump/head Pads; the manifold-stub Pads were stubbed in the spike and are validated by the T015 geometry test — they are the same additive-cylinder class as the spike-validated bolt bosses.)

**Alternatives considered**: `Ruled=False` AdditiveLoft (rejected — overshoot, spec 018 evidence). `Part.makeLoft` on raw wires wrapped as `Part::Feature` (rejected — would make the propeller a Part::Feature, breaking the `is_partdesign_body` contract + the existing PartDesign-body tests; the polyline+Ruled=True path keeps it PartDesign and reproducible). Raw `Part.BSplineSurface` skin (rejected — constitution III, recorded infeasible in spec 018).

## R3 — Propeller blade twist (pitch distribution)

**Decision**: Stack `blade_sections` NACA polyline sections along the blade radial axis from `hub_r·0.8` to `prop_r`. Each section `i` (at radius fraction `f = i/(n−1)`) is:
- **scaled** by a chord-taper factor (wider near the root, tapering toward the tip), and
- **rotated** in its own plane by `pitch(f) = root_pitch_deg·(1−f) + tip_pitch_deg·f` (linear blend; `root_pitch ≠ tip_pitch` ⇒ non-zero root-to-tip twist).

Loft the rotated/scaled sections `Ruled=True`, fuse with the hub cylinder.

**Rationale**: A real propeller blade twists (high pitch at the root, lower at the tip) — the single most recognizable "it's a screw" cue (SC-003). A linear pitch blend is the simplest law that produces measurable, reproducible twist (`root_to_tip_twist_deg = root_pitch − tip_pitch`), with both endpoints as named parameters (constitution I). Chord taper keeps the planform leaf-shaped rather than a constant-width paddle.

**Alternatives considered**: Constant pitch (rejected — no twist, fails SC-003). Cosine/elliptic pitch law (deferred — linear is sufficient for the perceptual goal and easier to reason about for reproducibility). Per-section explicit pitch list (rejected — over-parameterized for v1).

## R4 — Fused vs separate body topology (clarify Q3)

**Decision**:
- **Coupling flange** (collar disc + bolt-head bosses) and **shaft-log fairing** (coaxial faired boss) → additive Pads in the **existing shaft `PartDesign::Body`**. Sequential PartDesign features fuse automatically; the shaft stays `Solids==1`.
- **Engine sump + head/valve-cover + manifold stubs** → additive Pads in the **existing engine body**; stays `Solids==1`.
- **Strut / P-bracket** → a **separate new `PartDesign::Body`** (`Propulsion_Strut`), exposed via a new `Strut` wrapper + `Propulsion.struts`.

**Rationale**: Coaxial/overlapping additive features fuse cleanly within one PartDesign body (the spec 014 stern-tube boss already proves this for the shaft). The strut bridges the *tilted* shaft axis to the *horizontal* hull bottom — it cannot be expressed as an overlapping coaxial Pad of the shaft body without contortion, and a thin connecting feature risks a non-fusing gap (the exact spec 023 "thin boss won't fuse into a recessed wall" lesson → separate mullion bodies). A separate body is the proven pattern (spec 019 glass panes, spec 022 anchor-locker lid, spec 023 mullions).

**Alternatives considered**: Strut fused into the shaft (rejected — topology/fuse risk above). Coupling/fairing as separate bodies (rejected — they ARE coaxial with the shaft and fuse trivially; separate bodies would needlessly grow the aggregate).

## R5 — Manifold-or-fallback gate granularity (clarify Q4)

**Decision**: A per-body `_detail_or_fallback` wrapper validates each produced body (`Solids==1 ∧ isValid()`). On failure:
- **Core part** (propeller, rudder, engine) → rebuild the spec 014 placeholder for that body (the build still yields a valid solid).
- **Optional support** (strut, fairing) → omit the body entirely (the build still succeeds; the shaft keeps its spec 014 stern-tube boss).

**Rationale**: Mirrors spec 022's manifold-or-fallback gate and spec 014's per-body rollback. Core parts must exist (a propeller-less train is wrong), so they degrade to the placeholder; optional supports are cosmetic, so absence is acceptable. Both paths guarantee FR-007 (every produced body valid) and keep the overall build succeeding (FR-010).

**Alternatives considered**: Whole-train fallback on any failure (rejected — over-broad; one bad blade shouldn't drop the engine). Hard failure on any non-manifold (rejected — violates FR-010's "build still succeeds").

## R6 — Backward compatibility & versioning

**Decision**: All new parameters are appended as keyword-defaulted fields on the existing frozen dataclasses; the new `Strut` wrapper + `Propulsion.struts` use `field(default_factory=list)`; the new applied-flags on `Propeller`/`Rudder`/`Shaft`/`EngineBlock` get defaults. `build_propulsion`'s signature is unchanged. With all detail flags off the output is byte-identical to spec 014 (SC-006). → additive public surface → **MINOR** bump 1.10.0 → **1.11.0**.

**Rationale**: Constitution VI semver. Existing callers (incl. `cli.py`) keep working; detail is on by default so the default model gains the fidelity automatically (FR-012).

**Alternatives considered**: New top-level `PropulsionDetailParameters` composite (rejected — the detail naturally belongs to each component's params; flat fields match the spec 014 shape and the `.allium` model). Detail off by default (rejected — clarify Q1 chose on-by-default, gated).
