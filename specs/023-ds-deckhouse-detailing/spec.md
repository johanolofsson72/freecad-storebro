# Feature Specification: DS Deckhouse Detailing

**Feature Branch**: `023-ds-deckhouse-detailing`

**Created**: 2026-06-03

**Status**: Draft

**Input**: User description: "Finish the spec 016 DS deckhouse: the deferred front-window recess frame on the raked screen, window mullions, a helm-door opening, and a DS-specific interior refit that uses the enclosed-saloon headroom."

## Clarifications

### Session 2026-06-03

- Q: How is the front-window recess cut into the raked screen? → A: A blind `PartDesign::Pocket` on a datum **rotated to match the front rake angle**, cutting backward into the filled loft (depth < the solid's front thickness), with a translucent glass pane seated on the raked face — mirroring the spec 016 side-window recesses but on a tilted datum. Manifold-or-skip gate: if the rotated-datum cut fails to leave a single valid solid, the front recess is skipped (the side windows + raked screen still build).
- Q: What are the mullions? → A: Thin **raised vertical strips** (additive `PartDesign::Pad` bosses on the deckhouse body, fusing to stay one solid) crossing each side-window opening — the divider bars a real window frame has. Count per window is a parameter.
- Q: Is the helm door an opening or a recess? → A: A **blind door-shaped recess** (a tall `PartDesign::Pocket`, floor-to-near-roof) in one side wall at the helm position — NOT a through-cut (the deckhouse is a filled solid; a through-hole would read as a tunnel and risks non-manifold). It reads as a closed helm door. Side + position are parameters.
- Q: What does the DS interior refit change? → A: `build_interior` gains a `superstructure_variant` flag. In `"ds"` mode it builds a **full bespoke DS enclosed-saloon layout** (a new bundled `DsSaloon.yaml` fixture — enclosed helm saloon + galley + head + forward cabin) furnished by the spec 012/013 type-keyed builders, using the taller DS deckhouse headroom for the ceiling check, and adds a new **`helm` furniture type** (console + seat) in the saloon. `"standard"` (default) is byte-identical to the pre-spec-023 behaviour. **(2026-06-03 register rewrite: the user absorbed the full DS layout into spec 023; spec 025 no longer owns it. The deckhouse openings stay blind recesses — the user reversed the cut-through option, so the deckhouse remains a filled solid.)**
- Q: Do the mullions and helm door get render roles? → A: The mullions are part of the deckhouse body (white/gelcoat, via the existing `Deck_Deckhouse` role). The helm door is a recess in the deckhouse (same role). The front glass pane resolves to the existing `Deck_DeckhouseWindowGlass` → glass role. The helm console (interior) uses the existing interior `trim` role. No new render roles.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Front-window recess on the raked screen (Priority: P1)

A builder of the DS variant wants the raked windscreen to read as a framed front window, not a blank raked panel — closing the most visible spec 016 deferral.

**Why this priority**: The front screen is the defining face of the DS deckhouse; a blank raked panel is the most obvious "unfinished" tell. Highest perceptual return.

**Independent Test**: Build a DS deck; the deckhouse has a blind recess on its raked front face with a glass pane seated in it; the deckhouse stays a single valid solid; if the rotated-datum cut fails, the front recess is skipped and the rest still builds.

**Acceptance Scenarios**:

1. **Given** a DS deck with default deckhouse params, **When** built, **Then** the deckhouse carries a blind front-window recess on the raked face and a `Deck_DeckhouseWindowGlass` pane is seated in it, and `deckhouse.body.Shape` has `Solids == 1` and `isValid()`.
2. **Given** the front window disabled (`front_window=False`), **When** built, **Then** no front recess or front glass is produced; the side windows still build.
3. **Given** a rotated-datum cut that fails to leave a single valid solid, **When** built, **Then** the front recess is skipped (manifold-or-skip gate) and the deckhouse still builds valid.

---

### User Story 2 - Window mullions (Priority: P2)

The DS side windows should read as framed glazing with divider bars, not single blank openings.

**Why this priority**: Mullions add realism to the side glazing; moderate perceptual return, low risk (additive bosses).

**Independent Test**: Build a DS deck with `mullions_per_window > 0`; thin raised vertical strips cross each side-window opening; the deckhouse stays a single valid solid.

**Acceptance Scenarios**:

1. **Given** `mullions_per_window = 1`, **When** the deckhouse is built, **Then** one raised vertical strip crosses each side window and the deckhouse `Shape.Solids == 1` and `isValid()`.
2. **Given** `mullions_per_window = 0`, **When** built, **Then** no mullion strips are produced (spec 016 parity).

---

### User Story 3 - Helm-door opening (Priority: P2)

The DS deckhouse should have a recognizable helm door on one side.

**Why this priority**: A door completes the enclosed-saloon reading; self-contained blind recess.

**Independent Test**: Build a DS deck with the helm door enabled; a tall door-shaped blind recess sits in the chosen side wall; the deckhouse stays a single valid solid.

**Acceptance Scenarios**:

1. **Given** the helm door enabled (default), **When** the deckhouse is built, **Then** a tall door-shaped blind recess sits in the helm-side wall and the deckhouse `Shape.Solids == 1` and `isValid()`.
2. **Given** the helm door disabled (`helm_door=False`), **When** built, **Then** no door recess is produced.

---

### User Story 4 - Full DS enclosed-saloon interior layout (Priority: P2)

A DS build should get a bespoke enclosed-saloon interior — a helm saloon with a console and seat, galley, head, and forward cabin — using the deckhouse's standing headroom, not the open-flybridge arrangement.

**Why this priority**: Ties the interior to the DS topsides and gives the enclosed saloon a real fit-out; touches the interior module and ships a new layout.

**Independent Test**: Call `build_interior(layout=..., superstructure_variant="ds")`; a bundled DS layout is built and furnished (including a `helm` console + seat in the saloon) using the taller deckhouse headroom; `"standard"` mode is byte-identical to before.

**Acceptance Scenarios**:

1. **Given** `build_interior(..., superstructure_variant="ds")`, **When** built, **Then** the DS enclosed-saloon layout is built and furnished — including a `helm`-type console + seat in the saloon — and the build succeeds with the taller deckhouse headroom allowance.
2. **Given** `superstructure_variant="standard"` (default), **When** built, **Then** the interior is byte-identical to the pre-spec-023 build (original layout, no helm furniture, original headroom limit).
3. **Given** the DS layout, **When** furnished, **Then** every furnished compartment body is a valid solid/compound (the spec 012 manifold furniture discipline) and nests within the deckhouse envelope.

---

### Edge Cases

- What happens when the rotated front-recess datum produces a degenerate/non-manifold cut? → manifold-or-skip gate drops the front recess; the deckhouse still builds (reproducible — the skip is deterministic from the geometry, not random).
- What if a mullion strip is wider than the window opening? → validation rejects (`mullion_width` < window length / (mullions+1)), or the strip is clamped; reject is preferred (fail-fast).
- What if the helm door is taller than the deckhouse wall? → validation rejects (door height < deckhouse height).
- What if `superstructure_variant="ds"` is passed but the layout has no saloon/cabin compartment? → the helm console is skipped (no forward compartment to host it); the build still succeeds.
- What happens to STL manifold-ness with all the recesses + bosses? → every deckhouse build asserts `Solids == 1 && isValid()`; the front recess is skipped if it would break that.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deckhouse MUST gain a blind front-window recess on the raked front face, cut with a `PartDesign::Pocket` on a datum rotated to the front rake angle, with a translucent glass pane seated on the face; guarded by a manifold-or-skip gate (skip the front recess if it would not leave a single valid solid).
- **FR-002**: The deckhouse side windows MUST gain raised vertical mullion strips (`mullions_per_window`, additive bosses), keeping the deckhouse a single valid solid; `mullions_per_window = 0` reproduces spec 016.
- **FR-003**: The deckhouse MUST gain a tall door-shaped blind recess (the helm door) in a parameterized side wall, NOT a through-cut, keeping the deckhouse a single valid solid; the door MUST be omittable.
- **FR-004**: `build_interior` MUST gain a `superstructure_variant: Literal["standard","ds"] = "standard"` parameter. In `"ds"` mode it MUST build a bundled DS enclosed-saloon layout (`DsSaloon.yaml`: enclosed helm saloon + galley + head + forward cabin), furnish it with the spec 012/013 type-keyed builders plus a new `helm` furniture type (console + seat), and use the DS deckhouse headroom for the ceiling check. `"standard"` MUST be byte-identical to the pre-spec-023 behaviour.
- **FR-005** (MANIFOLD): Every deckhouse build (with any combination of front recess, mullions, helm door, side windows) MUST satisfy `Shape.Solids == 1 && isValid()` so STL stays watertight (specs 009/011/016 discipline).
- **FR-006** (NOBOOL): No refinement may boolean the hull or deck plate. All cuts/bosses act on the deckhouse body only; the helm-console acts on the interior only.
- **FR-007**: All new shape-controlling fields MUST be added additively + defaulted + validated to `DsWindowParameters`/`DeckhouseParameters` (and a small interior parameter for the helm console), each raising the module's parameter error on invalid input.
- **FR-008**: No public API may be removed; all spec 016/019 DS types, fields, and the `build_deck(superstructure_variant="ds", ...)` entry point keep working unchanged.

### Key Entities

- **DeckhouseParameters / DsWindowParameters**: gain `front_window` (+ front recess/glass controls), `mullions_per_window` (+ `mullion_width`), and helm-door controls (`helm_door`, side, position, door height/width, recess depth).
- **Front glass pane**: a translucent pane body on the raked face, render role glass.
- **Mullion strips**: raised bosses on the deckhouse body (deckhouse render role).
- **Helm door recess**: a blind pocket in the deckhouse body.
- **Helm console (interior)**: a furniture body added in DS mode; interior trim role.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A default DS deck build produces a deckhouse with `Solids == 1` and `isValid()` carrying the front recess (or a deterministic skip), mullions, helm door, and side windows.
- **SC-002**: STL export of the DS deckhouse succeeds and is watertight (no naked edges).
- **SC-003**: The hull and deck-plate shapes are identical whether the DS detailing runs or not (NOBOOL).
- **SC-004**: `build_interior(..., superstructure_variant="standard")` is byte-identical to the pre-spec-023 build; `"ds"` adds exactly one helm-console body to the forward compartment.
- **SC-005**: Every spec 016/019 DS test continues to pass unchanged (100% back-compatibility).

## Assumptions

- FreeCAD 1.1.1; rotated datums + `PartDesign::Pocket`/`Pad` behave as in specs 011/016/020/022.
- "Detailing" means a recognizable framed-window / door reading at model-viewing distance, within constitution principle IV's ±1% on principal dimensions; fine frame profile is visual-only.
- The deckhouse is a filled solid (spec 016), so all openings are blind recesses; through-openings are out of scope (they would read as tunnels and risk non-manifold).
- The DS interior refit is a light addition (a flag + one console piece + a headroom allowance), not a full bespoke DS layout (that lives in the spec 025 interior-layout-expansion).
- Light track: single synchronous build, no new state machine — `/tla` is expected to be skipped per the triviality gate.
