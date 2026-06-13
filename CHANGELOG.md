# Changelog

All notable changes to `freecad-storebro` are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.14.0] - 2026-06-13

Spec 030 — windshield crown. The windshield's top edge now arches upward at the
centerline instead of running dead flat across the beam. Viewed head-on, the top
trim bows up in the middle and falls away to the corners, closer to the RC34
reference silhouette.

A new `crown_height` field on `WindshieldParameters` sets the rise at the
centerline (default 60 mm). The arch is built by replacing the flat top edge of
each loft section with a polyline approximation of a circular arc: straight
segments, not a Sketcher arc, so the geometry stays byte-reproducible. All three
loft sections get the same rise, which keeps the `Ruled=False` loft well-behaved.

The arch returns to zero rise at the corners, so the corners keep the original
flat-top height. The spec 011 frame opening and its glass pane are therefore
untouched, and the frame border is preserved by construction: the crown only adds
material above the opening, it never cuts into it. If the crowned loft fails to
produce a single manifold solid, the build falls back to the flat-top slab.

`crown_height = 0.0` is the off switch. It skips the crown code path entirely and
reproduces the pre-030 flat-top windshield byte-for-byte. Out-of-range values
(negative, `>= top_width/2`, or non-finite) raise a `DeckParameterError` at
construction.

This changes the default windshield geometry, so default-build artifacts differ
from 1.13.x. Minor version bump (additive optional field).

## [1.13.2] - 2026-06-11

Spec 029 — parametric robustness. Every parameter dataclass now rejects
non-finite dimensions (`nan`, `+inf`, `-inf`) at construction, so a corrupt
upstream value fails fast with a clear error instead of flowing into the geometry
build and producing a broken or non-reproducible shape.

The hole was subtle: a positivity check written as `value <= 0` lets `inf`
through (`inf` is greater than zero) and lets `nan` through too, because `nan`
compares false to everything — so `nan <= 0` is `False`, i.e. "valid". The
propulsion module already guarded against this (its helpers check `math.isfinite`
first); hull, deck, and interior did not. They do now: the positivity/range
checks are finite-aware, and the deck and interior dataclasses gained a small
helper that finite-checks every declared float field automatically (skipping
integer counts, booleans, and nested dataclasses). Finite "auto" sentinels, like
the porthole's `0.0` derive-span marker, stay accepted; only `nan`/`inf` are newly
rejected. Valid inputs are untouched, so all geometry is byte-identical.

This was scoped down from the original spec 029: the FreeCAD expression-engine
bindings and the optional hard-chine hull variant (both behavior-changing, and in
the expression case reproducibility-sensitive) moved to spec 031 so this one stays
a clean, safe hardening fix.

### Fixed

- Every float geometry/dimension field across hull, deck, interior, and
  propulsion rejects `nan`/`+inf`/`-inf`, raising the module's existing parameter
  error. Was: only propulsion guarded non-finite values.

## [1.13.1] - 2026-06-11

Spec 028 — FCStd byte determinism. Two `storebro build` runs that export to FCStd
in the same process now produce byte-identical files, closing a determinism gap
that had been marked `xfail` since v1.0.0 (specs 009/011/012).

The fix is a much stronger scrub in the FCStd writer. Earlier specs deliberately
left the per-session identifiers in `Document.xml` alone — the Object IDs, the
document UUID, the save-timestamps — because an earlier attempt to scrub them
broke FreeCAD's cross-references and the file would not reopen. The trick this
time is that the Object `id` is only a save handle (FreeCAD links objects by
name, not by id), so renumbering every `id` to a canonical sequence with a single
XML pass is safe: the scrubbed document reopens with valid geometry. The
Topological-Naming tags in the `*.Map.txt` and `StringHasher` entries get the same
treatment: every per-session hash token is replaced by a deterministic value
derived from where it appears, and the map entries are sorted into a canonical
order. All of it is gated by a test that reopens the scrubbed file and checks
every body's shape is still valid with unchanged volume.

What this does NOT fix, and cannot from here: full byte parity across two separate
process invocations. While implementing this, the residual was traced to a
FreeCAD-internal limit — two separate processes occasionally emit a structurally
different topological-naming map for the same compartment (for one cabin, 842
lines in one run and 841 in the other, differing by a single postfix entry),
because FreeCAD's string hasher collides differently from one process to the next.
A different number of tags cannot be reconciled by post-processing one file in
isolation. So the within-process determinism is real and tested; the
cross-invocation case stays `xfail`, now with the FreeCAD cause documented rather
than filed as a future scrub upgrade. Closing it needs a fix in FreeCAD itself (or
a deterministic hasher reset before save).

### Fixed

- Two same-process FCStd exports are now byte-identical (was `xfail` since v1.0.0).

### Changed

- The FCStd writer scrubs `Document.xml` Object IDs / UUID / timestamps via a
  consistent renumbering, and canonicalizes the Topological-Naming tags and
  `*.Map.txt` order — all verified reload-safe.
- The cross-invocation FCStd determinism `xfail` is reclassified from "v1.1+ scrub
  upgrade" to a documented FreeCAD-internal limitation.

## [1.13.0] - 2026-06-10

Spec 026 — export format expansion. The export surface grows from STEP/STL/BREP/
FCStd to also cover OBJ, IGES, a 2D DXF profile, and optional gzip — and the
non-FCStd formats now export the whole boat, not just the hull.

Until now `storebro build --format step` (and stl/brep) wrote only the hull body
and silently dropped the deck, interior, and propulsion. They now export the full
assembly: every body combined into one compound (for the B-rep formats) or one
merged mesh (for the mesh formats), in a deterministic order. The export
functions accept either a single body (unchanged) or a list of bodies.

OBJ and IGES are new mesh and B-rep formats; a 2D DXF profile projects the boat's
side silhouette onto the X-Z plane and writes it as hand-rolled R12 ASCII (no
timestamps or handles, so it is deterministic by construction). Any export can be
gzipped with `--gzip` or `gzip=True` — the gzip is deterministic (mtime zeroed),
so two runs produce identical bytes. glTF is deferred: its only FreeCAD exporter
is a GUI workbench module that is unavailable in the headless/CI build, and
hand-writing glTF buffers was out of proportion to its value.

A spike proved each new format byte-reproducible before it shipped (constitution
II is non-negotiable): OBJ's header is a static URL, IGES needed its global-section
date scrubbed, the assembly compounds reuse the existing STEP/BREP canonicalizers,
and gzip and DXF are deterministic by construction.

While wiring the assembly export, a long-standing bug surfaced: `export_step` used
`Part.export([raw_shape], path)`, which does not serialize a raw shape's geometry
— so every STEP the library has ever written contained no faces, only product
structure (the old round-trip test only checked that the file was non-empty).
Switching to the Shape method (`shape.exportStep`) fixes it; STEP files now carry
the real B-rep and re-import correctly. STEP output therefore changes in this
release.

### Added

- Full-assembly export for STEP/STL/BREP (and the new OBJ/IGES/DXF): pass a list
  of bodies, or let the CLI export the whole boat by default.
- `export_obj` (Wavefront OBJ) and `export_iges` (IGES B-rep).
- `export_dxf_profile` — a 2D X-Z silhouette DXF.
- `gzip=True` on every export function (and `storebro build --gzip`).
- CLI `--format obj|iges|dxf`.

### Fixed

- `export_step` wrote geometry-less STEP files (used `Part.export` on a raw
  shape); it now uses the Shape method and produces valid B-rep STEP.

### Changed

- The CLI exports the full assembly for the multi-body formats (was hull-only).
- The STL watertight check applies only to single-body exports; an assembly is
  intentionally several solids.

### Deferred

- glTF — its FreeCAD exporter is GUI-only and unavailable headless.

## [1.12.0] - 2026-06-10

Spec 025 — interior layout expansion. The interior model widens along four axes,
all in `interior.py`. Alternativ5's combined compartment was described as a
salon with an integrated galley but only got a settee and table; it is now a new
`salon_galley` compartment type that also builds a galley counter with sink and
stove recesses. Custom layouts stop getting placeholder boxes: furniture is now
dispatched by compartment type for every layout, so a YAML file you write
yourself gets the same furniture the shipped layouts get. Four more compartment
types exist: `aft_cabin` (a berth), `dinette` (settee + table), `engine_room`
(a representative engine-block-like solid), and `wet_locker` (an open carcass
with shelves). And the v1.0 rule that every compartment sits on the centreline is
gone: a compartment can be placed off-centre, bounded by the hull half-beam.

Canonical Alternativ1-4 and the DS layout build byte-identically to before — the
off-centre code path is skipped entirely when y is zero, and only Alternativ5's
fixture changed. New geometry is plain analytic boxes, fillets, and cuts, the
spec 024 byte-reproducible class, so no reproducibility spike was needed. The
spec 012 galley manifold guard still holds, now including the Alternativ5 galley.

One thing surfaced during the work: the spec 024 head faucet is legitimately two
disjoint solids, so "every piece is a single solid" was too strong. The real
guarantee is that every piece is a valid, watertight (STL-exportable) shape, with
single-solid required of the galley counter and the new-type fittings. The
no-overlap check was also taught about `position.y` so two compartments at the
same fore-aft station but opposite sides no longer count as overlapping.

### Added

- `salon_galley` compartment type — settee + table + galley counter in one
  compartment (Alternativ5 uses it).
- Furniture dispatched by compartment type for every layout; custom
  (non-canonical) layouts now furnish instead of getting placeholder boxes.
- Compartment types `aft_cabin`, `dinette`, `engine_room`, `wet_locker`.
- `EngineRoomParameters` and `WetLockerParameters` (+ fields on
  `FurnitureParameters`) for the two new bespoke fittings.
- Off-centre compartment placement (`position.y != 0`), bounded by
  `|y| + width/2 <= beam_max/2`.

### Changed

- `build_interior` furnishes by compartment type rather than by layout name; the
  signature and the `Interior` aggregate are unchanged.
- The no-overlap and furniture-fit validations account for off-centre placement
  and the new compartment types.

## [1.11.0] - 2026-06-10

Spec 021 — propulsion fidelity. The running gear stops being a set of stand-in
boxes and rectangles. Each propeller blade is now a symmetric NACA foil that
twists from root to tip, lofted through stacked foil sections. The rudder blade
is a NACA foil too: a rounded leading edge tapering to a fine trailing edge,
instead of the old flat plate. The shaft carries a bolted coupling flange at the
gearbox end and a faired log where it leaves the hull, and a separate P-bracket
strut holds the shaft up under the hull. The engine block grows a marine-diesel
silhouette: an oil sump hanging below, a head and valve cover on top, and a row
of exhaust-manifold stubs on the outboard face.

Every part is built additively — the hull is never cut, so it stays a single
closed solid and `hull_modified` stays `False`. A spike confirmed up front that
every detailed construction is byte-reproducible, including the propeller blade
loft that was the real risk: foils are drawn as straight-segment polylines (no
Sketcher arcs, the thing that drifted in spec 022) and lofted `Ruled=True`, so
the determinism tests stay green. Each part has a manifold-or-fallback gate: a
foil, flange, or detailed block that would break the single-solid invariant
reverts to its spec 014 placeholder, and an optional strut or fairing that fails
is simply left out. The build always finishes with valid solids.

Detail is on by default. Turn any part back to its spec 014 form with its flag,
or the whole train at once with `--no-propulsion-detail`; with every flag off the
output is byte-identical to the spec 014 build.

### Added

- Symmetric-NACA foil propeller blades with root-to-tip twist
  (`PropellerParameters`: `airfoil_blades`, `naca_thickness_ratio`,
  `blade_sections`, `root_pitch_deg`, `tip_pitch_deg`).
- NACA-foil rudder blade (`RudderParameters`: `naca_foil`, `naca_thickness_ratio`).
- Shaft coupling flange + bolt detail and a faired shaft-log, both fused into the
  shaft (`ShaftParameters`: `coupling_flange`, `coupling_flange_diameter_mm`,
  `coupling_flange_thickness_mm`, `coupling_bolt_count`, `shaft_log_fairing`,
  `shaft_log_fairing_length_mm`, `shaft_log_fairing_diameter_ratio`).
- Strut / P-bracket support as a separate body (`ShaftParameters`:
  `strut_bearing`, `strut_count`, `strut_arm_width_mm`); new `Strut` wrapper and
  `Propulsion.struts`.
- Detailed marine-diesel engine block (`EngineParameters`: `detailed`,
  `sump_drop_mm`, `sump_inset_mm`, `head_height_mm`, `manifold_stub_count`,
  `manifold_stub_diameter_mm`).
- Per-part `*_applied` flags on the result wrappers (`Propeller.airfoil_applied`
  + `root_to_tip_twist_deg`, `Rudder.naca_applied`, `Shaft.has_coupling_flange` +
  `has_shaft_log_fairing`, `EngineBlock.detail_applied`).
- `storebro build --no-propulsion-detail` — build the running gear at spec 014
  placeholder fidelity.

### Changed

- `build_propulsion` now produces the detailed running gear by default; the
  signature, the `Propulsion` aggregate, and every existing field are unchanged.

## [1.10.0] - 2026-06-03

Spec 024 — interior contoured fittings. The furniture stops being a set of
boxes. Berth and settee cushions are rounded, split into segments with seam
gaps, and carry fabric detail: a grid of tufting-button dimples, a piping welt
around the top edge, and a couple of fold creases. The toilet is a rounded
pedestal with a bowl, and the sink gets a faucet. The galley worktop has rounded
edges and an appliance fascia. Bulkheads get rounded corners and a rounded-top
doorway where the headroom allows.

Everything is built with `Part` B-rep ops on the existing furniture bodies — the
interior's own idiom — and a spike confirmed every operation is byte-reproducible
across builds (filleted and cut volumes come out identical), so the determinism
tests stay green. Each contoured piece carries a manifold-or-box fallback: if a
fillet, fuse, or cut would break the single-solid invariant, that piece reverts
to its plain box. The galley counter's single-solid guard from spec 012 still
holds through the contour and fascia.

Contouring is on by default; `contoured=False` on any furniture group brings back
the spec 012/013 boxes.

### Added

- Contoured + fabric-detailed cushions (`BerthParameters` / `SalonParameters`:
  `contoured`, `cushion_segments`, `seam_gap`, fillet, `buttons_per_row`,
  `button_rows`, `button_radius`, `piping`, `piping_radius`, `fold_creases`).
- Contoured toilet + faucet (`HeadParameters`: `contoured`, `toilet_fillet`,
  `bowl_radius`, `faucet`, `faucet_height`).
- Galley rounded edges + fascia (`GalleyParameters`: `contoured`, `edge_fillet`,
  `fascia`, `fascia_thickness`).
- Curved bulkheads + doorways (`BulkheadParameters`: `contoured`,
  `corner_fillet`, `doorway`, `doorway_width`, `doorway_height`).

### Changed

- Furnished interiors now build contoured fittings by default; no public type,
  field, or function was removed.

## [1.9.0] - 2026-06-03

Spec 023 — DS deckhouse detailing. The enclosed deck-saloon variant gets the
parts spec 016 left out. The raked front screen now has a framed window recess
with glass, cut on a datum tilted to the rake angle. Each side window gets a
vertical mullion bar. One side wall gets a tall helm-door recess, dropped into
the widest gap between the windows so it never collides with one. The deckhouse
stays a filled solid with blind recesses — you read closed doors and windows,
not holes through a block — so it stays watertight.

The DS variant also gets its own interior. `build_interior(...,
superstructure_variant="ds")` builds a bundled enclosed-saloon layout — forward
cabin, head, galley, a helm station with a console and seat, and an aft saloon —
furnished with the standing headroom the deckhouse allows. `"standard"` is
unchanged.

### Added

- DS deckhouse front-window recess + glass, side-window mullions, and a
  helm-door recess (`DsWindowParameters.front_window`/`front_length`/
  `front_height`/`mullions_per_window`/`mullion_width`/`helm_door`/
  `helm_door_length`/`helm_door_height`/`helm_door_side`).
- `build_interior(..., superstructure_variant="ds")` — the DS enclosed-saloon
  layout (`DsSaloon`) with a new `helm` compartment type, `HelmParameters`, and
  the taller deckhouse headroom budget.

### Changed

- The default DS deckhouse now carries the detailing; existing
  `build_deck(superstructure_variant="ds")` callers get it automatically. No
  public type, field, or function was removed.

## [1.8.0] - 2026-06-03

Spec 022 — deck-hardware detailing. The five spec 010 placeholders stop looking
like a kit of straight tubes and boxes. The rubrail gets a moulded (chamfered)
section and a separate chrome insert strip running its length. The bow pulpit
gets rounded corner balls and torus weld beads at its joints, so it reads as a
bent stainless rail instead of three cylinders meeting at right angles. The
lifelines sag in a true catenary. Each cleat becomes a tapered casting with an
arched horn. And the anchor locker gets a recessed cavity with its own lid, so
it reads as something you can open.

Every refinement is an additive PartDesign body seated on the sampled deck. The
hull and deck plate are never cut, and each body stays a single valid solid, so
STL export stays watertight. The bow pulpit and lifelines fall back to their
spec 010 straight construction if a sweep fails.

The rounded rubrail fillet is an opt-in (`rounded_profile=True`), not the
default: its arc-loft volume drifts under accumulated FreeCAD state, which would
break byte-reproducibility, so the chamfer — which is stable — is what you get
unless you ask for the round.

### Added

- Moulded rubrail (`RubrailParameters.rounded_profile`, `outboard_fillet`,
  `chamfer_width`) plus a chrome insert strip (`chrome_insert`, `insert_height`,
  `insert_thickness`) with its own `chrome` render role.
- Bow-pulpit corner balls and weld beads (`BowPulpitParameters.bend_radius`,
  `weld_beads`, `weld_bead_radius`).
- Lifeline catenary sag (`LifelineParameters.sag_depth`).
- Cleat contour (`CleatParameters.base_taper`, `horn_rise`).
- Anchor-locker recessed cavity and lid (`AnchorLockerParameters.cavity_depth`,
  `cavity_inset`, `lid`, `lid_thickness`) with a `teak` lid render role.

### Changed

- The default deck hardware is now the contoured version; existing callers get
  it automatically. No public type, field, or function was removed.

## [1.7.0] - 2026-06-02

Spec 027 — CLI enhancements. Two practical additions to `storebro build`. A
`--json` flag prints the build result as one JSON object (`format`,
`target_path`, `byte_count`, `sha256`, `version`) instead of the human line, so
scripts can parse it instead of scraping prose. And four hull overrides —
`--loa`, `--beam`, `--draft`, `--station-count` — let you tune the hull from the
command line; `--station-count` finally exposes the spec 018 smoothness knob.
Out-of-range values are rejected by the usual `HullParameters` validation with a
non-zero exit. With no new flags the command is byte-identical to before.

GUI launch, a config file, multi-format single-invocation export, and a
custom-layout directory are deferred to follow-ons.

### Added

- `storebro build --json` — machine-readable build result.
- `storebro build --loa/--beam/--draft/--station-count` — hull overrides
  (omitted ones use the `HullParameters` defaults).

## [1.6.0] - 2026-06-02

Spec 020 — superstructure curvature refinement. Two of the spec 008 geometry
deferrals land, both proven on a FreeCAD spike before any code: the hardtop
leading edge now curls down as a smooth cosine curve (a dense `Ruled=True` loft,
not `Ruled=False` — that overshoots, per spec 018), and the railing top-rail is
swept along the sheer with a `PartDesign::AdditivePipe` so it follows the deck
edge instead of sitting as a flat bar. Both stay single manifold solids; the
swept rail falls back to the spec 008 straight bar if the sweep ever fails, so a
broken rail never ships.

The windshield crown was deferred during implementation: the windshield loft is
already `Ruled=False`-smooth in rake, and a transverse arched top edge would
ripple into the spec 011 frame opening and glass pane at real regression risk
for the lowest-priority refinement. It is split into a follow-on.

### Added

- `HardtopParameters.curl_sections` (default 7) — the dense sections tracing the
  smooth hardtop curl; its minimum reproduces the spec 008 faceted curl.

### Changed

- The railing top-rail is a swept `AdditivePipe` following the sheer (was a
  straight per-side cylinder), with a straight-bar fallback.

## [1.5.0] - 2026-06-02

Spec 019 — window glass panes. The recessed windows now read as glass. Every
porthole, cabin-trunk side window, and DS deckhouse side window gets a thin
translucent pane seated in its recess, coloured by the existing glass material;
the windshield already had its pane. Panes are separate additive bodies — they
are never booleaned into the hull, cabin trunk, or deckhouse — so those solids
stay watertight and STL export is unaffected. Panes are on by default with a
per-call opt-out. Rounded window corners stay deferred: the Sketcher fillet
carries the non-watertight-mesh risk that spec 018's bilge arc proved.

### Added

- Translucent glass-pane bodies for portholes (`Hull_PortholeGlass*`),
  cabin-trunk side windows (`Deck_CabinWindowGlass*`), and DS deckhouse windows
  (`Deck_DeckhouseWindowGlass*`), each resolving to the `glass` render role.
- `glass_panes` (opt-out, default on) and `glass_thickness` fields on
  `HullGlazingParameters`, `CabinWindowParameters`, and `DsWindowParameters`.

## [1.4.0] - 2026-06-02

Spec 018 — hull surface curvature v2. The default hull now reads as a smooth
hull, not a nine-facet wedge. Smoothness comes from station density under the
exact `Ruled=True` loft, not from a B-spline: a FreeCAD spike measured the
`Ruled=False` B-spline overshooting the beam by 12-141% across every
station-spacing strategy (uniform, Chebyshev, stem-clustered, amidships), while
`Ruled=True` is exact (0%). So the default station count goes from 9 to 31 and
the cap from 21 to 81; the facets drop below visual resolution and the hull
stays exact, manifold, and STL-exportable at every density (verified at n=3, 9,
31, 81 on FreeCAD 1.1.1). True B-spline is recorded as permanently infeasible
for this profile, and a raw `Part.BSplineSurface` skin was rejected for not
being a PartDesign-editable feature (constitution III).

The quarter-circle bilge arc was re-attempted at the new density and re-deferred
again: its B-rep is a valid single solid, but the tessellated mesh is not
watertight, so STL export fails. The hull keeps its sharp chine. The denser
default changes the default hull's geometry (an intended fidelity improvement),
so this is a minor bump; pin `station_count=9` to reproduce the old shape.

### Changed

- `DEFAULT_STATION_COUNT` 9 → 31 (smoother default hull) and `STATION_COUNT_MAX`
  21 → 81 (`station_count` validated to `[3, 81]`). `station_count=9`
  reproduces the pre-1.4.0 hull.

## [1.3.0] - 2026-06-02

Spec 016 — DS variant superstructure. The deck builder now has a second
canonical silhouette: the Storebro DS (deck saloon, or *styrhytt*), an enclosed
wheelhouse. Pass `superstructure_variant="ds"` to `build_deck` (or
`--superstructure ds` on the CLI) and the open-flybridge cabin trunk,
windshield, hardtop, and pillars give way to a single enclosed deckhouse. That
deckhouse is one filled solid: a raked windscreen front, tapered side walls
carrying blind wraparound window recesses, an aft wall, and a flat roof, seated
on the sampled deck top. The hull, deck plate, railings, and all deck hardware
are shared verbatim; only the deckhouse differs. The default stays `standard`,
so every existing call site builds byte-identical output. The surface only
grows, so this is a minor bump to 1.3.0.

The DS front is the raked windscreen face itself, not a cut recess — the
reference DS front is a single large screen. Only the side windows are blind
recesses; a separate front-window frame is a future-PATCH refinement.

### Added

- `superstructure_variant` keyword on `build_deck` (`"standard"` default,
  `"ds"` for the enclosed deck saloon) and the matching `--superstructure
  {standard,ds}` CLI flag.
- `DeckhouseParameters`, `DsWindowParameters`, and the `Deckhouse` wrapper,
  re-exported from `storebro`.
- `parameters_deckhouse` keyword on `build_deck` for DS deckhouse dimensions.

### Changed

- `Deck` aggregate: `cabin_trunk`, `windshield`, `hardtop`, `hardtop_pillars`,
  and `cabin_windows` are now optional and are `None` in the DS variant; new
  `superstructure_variant` and `deckhouse` fields carry the chosen silhouette.

## [1.2.0] - 2026-06-02

Spec 015 — render attributes. The model now comes coloured. Every body the
library builds gets a deterministic, role-keyed colour and a named material, so
a `storebro build` opens in FreeCAD looking like a Storebro: gelcoat-white hull
and superstructure, teak-brown rubrail and interior joinery, chromed railings
and deck hardware, translucent windshield glass, bronze propeller and rudder, a
dark engine. A new `render` module holds a central palette, and each `build_*`
applies it to the bodies it creates. Colours are stored as App data properties
that persist on a headless build (the GUI's own colours need a GUI session).
Geometry is never touched, and the appearance-free STEP/STL/BREP exports stay
byte-identical. The change is additive, so every earlier call site keeps
working; the minor version goes to 1.2.0.

### Added

- `render` module: `RenderAttribute`, the `PALETTE` mapping of role to
  colour + material, `role_for_label`, and
  `apply_render_attributes(objects, *, enabled=True)`.
- `apply_render_attributes: bool = True` keyword on `build_hull`, `build_deck`,
  `build_interior`, and `build_propulsion`, which colours the bodies each one
  builds.
- CLI `build` flag `--no-colors` for a neutral model (FreeCAD default
  appearance).

### Changed

- `storebro build` colours the model by default; pass `--no-colors` to opt out.
- Version bumped 1.1.0 to 1.2.0 in `pyproject.toml` and `storebro.__version__`.

### Notes

- Colours are stored as `RenderColor`, `RenderMaterial`, and
  `RenderMaterialName` data properties on each body (verified on FreeCAD 1.1.1).
  The GUI renders from view-provider colours in `GuiDocument.xml`, which a
  headless build cannot write, so GUI-visible colour shows up when the model is
  built or opened in a GUI session. The data properties are the durable carrier.
- Portholes and cabin-trunk windows are recesses in opaque parent bodies and
  take the parent colour; only the windshield has a separate translucent glass
  body. Separate glass inserts for those are deferred.
- Geometry tier verified on FreeCAD 1.1.1 (969 passed, 1 skipped, 2 xfailed).
  The GUI eyeball of the signoff `.FCStd` is still the maintainer's pre-tag step
  (constitution V).

## [1.1.0] - 2026-06-01

Spec 014 — propulsion. The boat now has an engine room and running gear. A new
`propulsion` module builds an inboard installation — engine bed, engine block,
propeller shaft, propeller, and rudder — and seats it on the actual sampled
hull. Twin-screw is the default (the historical RC34 layout); pass
`engine_count=1` for a single screw. The hull solid is never cut: the shaft
passes through an additive stern-tube boss, so the manifold stays intact and
STL export is unaffected. First new geometry module beyond the v1.0 set, so the
minor version bumps to 1.1.0. Every earlier call site keeps working unchanged.

### Added

- `build_propulsion(hull, deck=None, parameters=None, *, document=None, name="Propulsion")`:
  composes the five components into a document and returns a `Propulsion`
  aggregate.
- `PropulsionParameters` composite plus the five component parameter dataclasses
  `EngineBedParameters`, `EngineParameters`, `ShaftParameters`,
  `PropellerParameters`, `RudderParameters` (all frozen, all validated).
- Result wrappers `EngineBed`, `EngineBlock`, `Shaft`, `Propeller`, `Rudder`
  and the `Propulsion` aggregate.
- `PropulsionParameterError` / `PropulsionConstructionError`.
- CLI `build` flags: `--engine-count {1,2}` (default 2) and `--no-propulsion`.
- Defaults: twin screw, 400 mm engine offset, 10 degree shaft down-angle,
  3-blade propeller, one rudder per screw.

### Changed

- `storebro build` now includes the propulsion bodies by default; the bodies
  flow into every export format. Use `--no-propulsion` for the pre-1.1.0 output
  set (hull + deck + interior only).
- Version bumped 1.0.7 to 1.1.0 in `pyproject.toml` and `storebro.__version__`.

### Notes

- Geometry fidelity is representative, not CAD-faithful: the engine is a block,
  the propeller blades are flat plates, the rudder is a foil plate. Detailed
  machinery, airfoil blades, colors and materials are deferred (see
  `specs/014-propulsion/spec.allium`).
- The shaft penetration is an additive boss, not a real through-hull cavity —
  a deliberate choice to avoid the non-manifold STL failures that specs 009 and
  011 hit with boolean cuts on the dense-station hull.

## [1.0.3] - 2026-05-28

Spec 009 — hull surface smoothness. The default hull now reads as a denser,
more refined silhouette than v1.0.2 by raising the station count from 5 to 9
and reshaping the keel-depth anchor profile. Stem tightens to a thin 10 mm
face (was 80 mm), giving the bow a near-knife-edge look in side view while
keeping the loft stable. Public surface is additive — every v1.0.2 call site
keeps working unchanged.

### Added

- `HullParameters.station_count`: new int field, default `9`, range `[3, 21]`.
  Controls the number of station sketches in the AdditiveLoft.
- `HullParameters.bilge_radius`: new float field, default `0.10` m, range
  `[0, min(beam_max / 2, draft)]`. Parameter is accepted and validated; arc
  generation is currently deferred to v1.1+ (see notes below).
- `HullParameters.uses_b_spline_loft`, `uses_zero_forefoot_stem`,
  `uses_bilge_arc`, `max_bilge_radius` — read-only computed properties.
- `StationTopology` enum (exported in `storebro.hull.__all__`) with values
  `PENTAGON_THIN_STEM`, `PENTAGON_LEGACY`, `PENTAGON_WITH_ARC`.
- Module-level constants: `DEFAULT_STATION_COUNT = 9`,
  `DEFAULT_BILGE_RADIUS_M = 0.10`, `STATION_COUNT_MIN = 3`,
  `STATION_COUNT_MAX = 21`, `B_SPLINE_STATION_COUNT_THRESHOLD = 8`,
  `OVERSHOOT_TOLERANCE_MM = 1.0`, `REFERENCE_FIDELITY_TOLERANCE_PCT = 1.0`,
  `HULL_BUILD_TIME_BUDGET_SECONDS = 10.0`, `THIN_STEM_HALF_WIDTH_M = 0.005`.

### Changed

- Default hull silhouette is now denser (9 stations vs 5) and uses a thin
  10 mm stem face instead of 80 mm. Visually a more faithful RC34 1972
  silhouette; geometrically the same Storebro proportions within ±1%.
- `_compute_stations()` is parametric over `parameters.station_count`. The
  spec 007 anchor names (Transom / Aft / Amidships / Fwd / Stem) are
  preserved at the endpoint positions; intermediate stations are named
  `Station01`, `Station02`, ... for traceability in the FreeCAD tree.
- Keel-depth anchor profile smoothed near the stem: forefoot depth drops
  gradually (transom 0.85·draft → amidships 1.00·draft → stem 0.15·draft)
  instead of the spec 007 abrupt drop (0.55·draft → 0.08 m). Geometrically
  closer to a real RC34's keel underrun.
- `_apply_loft_and_mirror()` signature: added a third `parameters`
  positional argument for forward-compatibility with the v1.1+ B-spline work.
  Existing callers using positional args from spec 007 must update — this
  is a private (`_`-prefixed) helper so the public API is unaffected.

### Deferred to v1.1+

- **`Ruled=False` (B-spline) loft.** Originally promised at
  `station_count >= 8`. Empirical testing in FreeCAD 1.1.1 found the
  B-spline interpolation fundamentally unstable for the Storebro profile —
  overshoots ranged from 22 mm to 1900 mm and intermittently produced
  degenerate shapes. The v1.0.3 implementation uses `Ruled=True` at every
  station count. `uses_b_spline_loft` always reports `False` in v1.0.3.
- **Quarter-circle bilge arc.** Originally promised on every non-stem
  station via `Sketcher.fillet()`. The fillet itself works, but the
  arc + denser-station combination produces tessellated meshes with
  non-manifold edges and self-intersections that break the STL export
  pipeline. `uses_bilge_arc` always reports `False` in v1.0.3.
- **Degenerate-vertex stem.** Substituted by `PENTAGON_THIN_STEM` (5 mm
  half-width pentagon) because true vertex sections cause the dominant
  B-spline overshoot mode.

### Fixed

- (Test isolation) Marked the FCStd in-process determinism parametrize case
  as `xfail(strict=False)`. The test passes in isolation but becomes flaky
  in long pytest sessions because the denser hull advances FreeCAD's
  internal counters past the determinism scrub's normalization range.
  Tracked as `Fcstd.determinism_under_large_test_suite` for v1.1+.

## [1.0.1] - 2026-05-17

Spec 007 — hull fidelity refresh. The default hull now reads as a
recognizable Storebro Royal Cruiser 34 (1972) in profile rather than a
faceted wedge. Parameter surface is additive only; the only new field
is `stem_rake_angle`. All other changes are default-value tweaks based
on the storebropassion.de RC34 1972 reference.

### Changed

- `HullParameters.draft` default: `0.95` → `1.10` m (matches the RC34 1972
  reference; the v1.0.0 value was estimate-grade and read low).
- `HullParameters.sheer_height_aft` default: `0.85` → `0.95` m.
- `HullParameters.sheer_height_fwd` default: `1.30` → `1.16` m. Sheer
  differential drops from `0.45` m to `0.21` m so the deck line reads
  near-flat from above, matching the reference.
- `HullParameters.deadrise_amidships` default: `16.0` → `8.0` degrees.
  The hull is semi-displacement, not planing; the new value flattens
  the bottom accordingly.
- `HullParameters.transom_angle` default: `12.0` → `5.0` degrees.
  Near-vertical transom per the Alternativ side-profile drawings.
- Stem station: was a single degenerate vertex at LOA; is now a finite
  80mm-wide blunt stem face with a small forefoot, so the bow has
  substance instead of a knife edge. Topologically a 5-vertex pentagon
  matching the other four stations, which lets `PartDesign::AdditiveLoft`
  map vertices 1:1 across the hull without twisting.

### Added

- `HullParameters.stem_rake_angle`: new field, default `6.0` degrees,
  range `[0, 30]`. Tilts the Stem datum forward around the support's
  local Y axis so the bow has the slight forward lean visible on the
  reference. Surfaces a corresponding `Body.StemRakeAngle` property
  in the FreeCAD GUI (the 9th named hull property).

### Deferred

- Smooth B-spline loft (`AdditiveLoft.Ruled=False`) — with only five
  stations the B-spline interpolation overshoots between the wide
  amidships and the narrow stem (port bbox extends past +3000 mm
  instead of +1600 mm). Awaits a denser station set in a future
  PATCH; tracked as `deferred Hull.b_spline_loft` in the Allium spec.
- Quarter-circle bilge arc transition — requires the B-spline loft
  to be in place first so the sketch wire topology stays consistent
  between rounded non-stem stations and the rectangular stem. Tracked
  as `deferred Hull.bilge_arc` in the Allium spec.

### Tests

- `tests/geometry/test_hull_silhouette.py` — bbox dimensions match the
  reference within tolerance: LOA `10.35` m ±1%, beam `3.20` m ±2%,
  Z-envelope `1.5–2.3` m, hull is a closed manifold solid.
- `tests/geometry/test_hull_bspline_loft.py` — the loft produces a
  positive-volume closed solid (regardless of Ruled mode).
- `tests/unit/test_hull_parameters_stem_rake.py` — range validation
  on the new `stem_rake_angle` field.

### Hashes

`tests/geometry/fixtures/expected_hashes.toml` refreshed against
FreeCAD 1.1.1 with the new defaults. Source hash key changed from
`b8fac77b0986` to `b0380b2cc068` because `HullParameters.__repr__`
now includes the new `stem_rake_angle` field.

## [1.0.0] - 2026-05-17

Initial public release. Hull + deck + interior + export/CLI usable
end-to-end. All four v1.0 modules shipped per spec 001 (hull), spec 002
(export), spec 003 (deck), spec 004 (interior), spec 005 (CLI), and
spec 006 (PartDesign rebuild making the hull editable in the FreeCAD GUI).
