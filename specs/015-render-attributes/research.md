# Research: Render Attributes

Phase 0 — resolve the one load-bearing unknown: how to set color + material so it is headless-safe, persistent, deterministic, GUI-renderable, and FreeCAD-idiomatic. All findings below were verified empirically against the FreeCAD 1.1.1 build on this host (`PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib`, bundled CPython 3.11.14).

## Decision 1 — Color/material carrier: custom App data properties (primary) + ViewObject bridge (best-effort)

**Decision**: Store each body's appearance as custom **App data properties** on the object — an `App::PropertyColor` (RGBA) and an `App::PropertyMaterial` (named FreeCAD material) in a `"Render"` property group. When (and only when) the object exposes a live `ViewObject` (GUI session), additionally mirror to `ViewObject.ShapeAppearance`/`ShapeColor` and derive `ViewObject.Transparency` from the alpha channel.

**Rationale** (empirical):
- In pure console mode, `obj.ViewObject` is `None`. **`FreeCADGui.setupWithoutGUI()` does NOT change this** on this build — `ViewObject` stays `None`, so the ViewObject path cannot even be set headless.
- A headless `saveAs` writes only `Document.xml` + `*.brp` — **no `GuiDocument.xml`** — so any ViewObject color would not persist from a headless build anyway.
- A custom `App::PropertyColor` **does** persist: written into `Document.xml`, round-trips through save/reload, value preserved (modulo deterministic 8-bit-per-channel quantization, e.g. `0.93 → 237/255 = 0.929412`). Same input always quantizes identically → reproducible (constitution II).
- `App::PropertyMaterial` is available and accepted (`addProperty("App::PropertyMaterial", ...)` returns a `<Material object>`), making it the idiomatic named-material carrier (constitution III) and matching the spec's literal "`App::PropertyColor` and `App::PropertyMaterial`".

**Consequence / honest limitation**: A purely headless build carries durable color **data** but the FreeCAD GUI renders objects from view-provider properties (`GuiDocument.xml`), which a headless build on this FreeCAD cannot emit. GUI-visible color therefore appears when the model is built or opened within a GUI-enabled FreeCAD session (where the ViewObject bridge fires) — exactly the FR-005 (data persists) / FR-006 (GUI-visible when GUI present) split the spec already encodes. The data property is the portable, testable source of truth; the maintainer's GUI signoff is where colors are eyeballed.

**Alternatives considered**:
- *ViewObject-only* — rejected: `None` headless, doesn't persist headless, untestable without a GUI, breaks the headless build path.
- *`FreeCADGui.setupWithoutGUI()` to force view providers* — rejected: verified to leave `ViewObject` `None` and still no `GuiDocument.xml` on this build; adds a GUI import dependency for no gain.
- *Bake color into mesh/STEP export* — rejected: STEP/STL/BREP are appearance-free by spec (FR-012); coloring is a `.FCStd` concern only.

## Decision 2 — Application surface: per-`build_*` kwarg delegating to a public applier

**Decision**: One public `apply_render_attributes(objects, *, enabled=True) -> int` in `render.py`. Each public `build_*(... , apply_render_attributes: bool = True)` collects the top-level shape-bearing objects in its aggregate and calls the applier when the kwarg is `True`. The CLI passes `apply_render_attributes=not args.no_colors` to every build.

**Rationale**: Matches the spec-010/011/014 convention of additive optional kwargs on `build_*`; keeps geometry construction and cosmetics separable and individually testable; satisfies FR-007 (public build API default-on) for direct library callers, not just the CLI. Passing explicit object lists (not the whole document) avoids coloring internal construction features (sketches, datum planes, pads, pockets) that share the document.

**Alternatives considered**:
- *Single doc-wide post-build pass only* — rejected as sole mechanism: would color construction features unless filtered, and wouldn't color models built via direct `build_*` calls without an extra step. (The applier still accepts any object iterable, so a doc-wide call remains possible for advanced users.)
- *Mutate each construction site to set color inline* — rejected: violates constitution I (scatters color constants) and DRY.

## Decision 3 — Role resolution: deterministic label-prefix mapping

**Decision**: Resolve each object's role from its stable `Label` via an ordered, deterministic prefix/exact-match table (e.g. `HullBody → hull`; `Deck_Rubrail* → trim`; `Deck_Railings*|Deck_BowPulpit|Deck_Cleat*|Deck_Lifelines|Deck_Pillar* → metal`; `Deck_WindshieldGlass → glass`; `Deck_Windshield → frame`; `Deck_DeckPlate|Deck_CabinTrunk|Deck_Hardtop|Deck_AnchorLocker → superstructure`; interior compartment/furniture labels → `trim`/`bulkhead`; `Propulsion_Propeller → bronze`; `Propulsion_Shaft → steel`; `Propulsion_Rudder → bronze`; `Propulsion_Engine|Propulsion_EngineBed → engine`). Any unmatched label → `DEFAULT` neutral grey (FR-010).

**Rationale**: Labels are already stable and role-encoding (verified across hull.py / deck.py / interior.py / propulsion.py); no renaming needed. A pure-Python resolver is unit-testable without FreeCAD.

**Alternatives considered**: keying on FreeCAD `TypeId` — rejected: too coarse (most bodies are `PartDesign::Body`), can't distinguish rubrail from railing.

## Decision 4 — Glass translucency

**Decision**: The `glass` palette entry stores alpha < 1.0 (e.g. `(0.60, 0.70, 0.80, 0.35)`). The applier persists the RGBA as data; when a ViewObject is present it sets `ViewObject.Transparency = round((1 - alpha) * 100)`. Headless test asserts `PALETTE["glass"].color[3] < 1.0`.

**Rationale**: FR-014; keeps the single source of truth (alpha in the palette) and derives the GUI transparency deterministically.

## Open questions

None. All NEEDS CLARIFICATION resolved (none remained after `/clarify`).
