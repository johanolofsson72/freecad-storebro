# Data Model — Spec 016 DS-Variant Superstructure

All lengths in **millimeters**, angles in **degrees** (matching the spec 008/010/011 dataclasses). New public types are additive; the `Deck` aggregate change is backward-compatible (frozen, built only inside `build_deck`).

## §1 New parameter dataclasses (`deck.py`)

### 1.1 `DsWindowParameters` (frozen)

DS deckhouse side/front window blind-recess geometry. Mirrors `CabinWindowParameters` but without rounded corners (out of scope).

| Field | Type | Default | Constraint |
|---|---|---|---|
| `count_per_side` | int | 3 | `>= 0` |
| `length` | float | 1000.0 | `> 0` |
| `height` | float | 500.0 | `> 0` |
| `recess_depth` | float | 15.0 | `> 0` |

`__post_init__` raises `DeckParameterError(name, value, range)` per field.

### 1.2 `DeckhouseParameters` (frozen)

The enclosed DS deckhouse shape.

| Field | Type | Default | Constraint |
|---|---|---|---|
| `length` | float | 6200.0 | `> 0` |
| `forward_width` | float | 2000.0 | `> 0` |
| `aft_width` | float | 2200.0 | `> 0` |
| `height_above_deck` | float | 1500.0 | `> 0` |
| `front_rake_angle` | float | 30.0 | `[0, 60]` deg |
| `roof_thickness` | float | 60.0 | `> 0` |
| `wall_inset` | float | 250.0 | `>= 0` |
| `fwd_offset` | float | 2200.0 | `>= 0` |
| `windows` | `DsWindowParameters` | `DsWindowParameters()` | nested validation |

Cross-field invariants in `__post_init__`:
- **TaperedSilhouette**: `forward_width <= aft_width` (matches the cabin-trunk rule) → `DeckParameterError("deckhouse_forward_width<>aft_width", None, "forward_width must be <= aft_width ...")`.
- **RecessShallowerThanWall**: `windows.recess_depth < wall_inset` → recesses cannot pierce the solid (spec 009 guard). When `wall_inset == 0`, any positive recess depth is rejected.

Reference register: a `REFERENCE_STOREBRO_DECKHOUSE_DS` ClassVar dict (parallel to `DeckParameters.REFERENCE_STOREBRO_DECK_RC34_1972`) recording the storo34_side_lines.png-derived defaults.

## §2 New sub-Body wrapper (`deck.py`)

### 2.1 `Deckhouse` (frozen)

Wrapper around the FreeCAD `PartDesign::Body` for the enclosed deckhouse. Length fields in **meters** at the wrapper boundary (matching the spec 003/008 wrappers; geometry built in mm).

| Field | Type | Meaning |
|---|---|---|
| `body` | Any | The deckhouse `PartDesign::Body` (windows are Pocket features on it). |
| `length` | float | Deckhouse length (m). |
| `forward_width` | float | Forward width (m). |
| `aft_width` | float | Aft width (m). |
| `height` | float | Height above deck (m). |
| `window_count` | int | Total blind window recesses (`count_per_side * 2`). |

## §3 Modified return aggregate (`deck.py`)

### 3.1 `Deck` deltas

```diff
  deck_plate: DeckPlate
- cabin_trunk: CabinTrunk
- windshield: Windshield
- hardtop: Hardtop
- hardtop_pillars: HardtopPillars
+ cabin_trunk: CabinTrunk | None
+ windshield: Windshield | None
+ hardtop: Hardtop | None
+ hardtop_pillars: HardtopPillars | None
  railings: Railings
  ... (hardware, glazing unchanged) ...
+ superstructure_variant: str        # "standard" | "ds"
+ deckhouse: Deckhouse | None         # populated iff variant == "ds"
```

Population matrix:

| Field | standard | ds |
|---|---|---|
| `deck_plate` | populated | populated |
| `cabin_trunk` / `windshield` / `hardtop` / `hardtop_pillars` | populated | **None** |
| `deckhouse` | **None** | populated |
| `railings`, `rubrail`, `bow_pulpit`, `lifelines`, `anchor_locker`, `cleats` | populated | populated |
| `cabin_windows` | populated | **None** (no cabin trunk to cut) |
| `superstructure_variant` | `"standard"` | `"ds"` |

`cabin_windows` becomes `CabinWindows | None` as well (it is a cut on the cabin trunk, which is absent in DS mode).

## §4 Modified function surface

### 4.1 `build_deck` signature delta

```python
def build_deck(
    hull: Hull,
    parameters: DeckParameters | None = None,
    *,
    superstructure_variant: Literal["standard", "ds"] = "standard",   # NEW
    parameters_superstructure: DeckSuperstructureParameters | None = None,
    parameters_deckhouse: DeckhouseParameters | None = None,           # NEW
    parameters_hardware: DeckHardwareParameters | None = None,
    parameters_glazing: DeckGlazingParameters | None = None,
    document: Any = None,
    name: str = "Deck",
    apply_render_attributes: bool = True,
) -> Deck: ...
```

Validation order (all before FreeCAD calls):
1. `superstructure_variant not in {"standard","ds"}` → `DeckParameterError("superstructure_variant", value, "one of {standard, ds}")`. (Belt-and-suspenders; the CLI's argparse `choices` also guards.)
2. `variant == "ds"` and `parameters_superstructure is not None` → `DeckParameterError("superstructure_variant<>parameters_superstructure", None, "the ds variant has no open-flybridge superstructure ...")` (FR-014).
3. `parameters is not None and parameters_superstructure is not None` → existing mutual-exclusivity error (unchanged).
4. DS branch: resolve `dh = parameters_deckhouse or DeckhouseParameters()`; `_validate_cross_hull_deckhouse(hull, dh)`.

### 4.2 New internal helpers (`_`-prefixed)

- `_validate_cross_hull_deckhouse(hull, dh)` — `dh.fwd_offset + dh.length <= hull.parameters.loa` and `dh.aft_width + 2*dh.wall_inset <= hull.parameters.beam_max`, else `DeckParameterError` (FR-012).
- `_build_deckhouse(hull, parameters, deck_plate, dh, target_doc, added)` → `Deckhouse`. Two-trapezoid `AdditiveLoft` (Ruled=True) seated on `_resolve_deck_top_z_at`; front rake via upper-edge aft shift; back-compat named props on the Body; manifold guard.
- `_cut_deckhouse_windows(deckhouse, win, target_doc, added)` → cut `count_per_side` blind `PartDesign::Pocket` recesses per side; return updated `Deckhouse` with `window_count`.

### 4.3 CLI (`cli.py`)

`build` subparser gains:
```python
build_p.add_argument("--superstructure", choices=["standard", "ds"], default="standard",
                     help="Superstructure variant: standard (open flybridge) or ds (enclosed deck saloon). Default: standard.")
```
`_run_build` threads `superstructure_variant=args.superstructure` into `build_deck`.

### 4.4 `__init__.py`

Re-export `DeckhouseParameters`, `DsWindowParameters`, `Deckhouse` (additive public surface, MINOR bump).

## §5 Version

`storebro.__version__`: `1.2.1` → **`1.3.0`** (MINOR — additive public API: new variant keyword, new dataclasses, new wrapper). `test_version_consistency` updated.
