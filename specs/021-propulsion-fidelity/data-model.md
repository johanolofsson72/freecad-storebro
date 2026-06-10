# Phase 1 Data Model: Propulsion Fidelity

All types live in `src/storebro/propulsion.py`. New fields are **appended** to the existing frozen dataclasses with defaults (back-compat — see §Compatibility). Lengths mm, angles deg, ratios dimensionless.

## Module config constants (constitution I — no magic numbers)

Mirror these as module-level constants used as the dataclass field defaults (one source of truth):

| Constant | Default | Meaning |
|---|---|---|
| `_DEFAULT_PROPELLER_NACA_T` | 0.12 | propeller foil thickness ratio |
| `_DEFAULT_PROPELLER_BLADE_SECTIONS` | 5 | stacked foil sections per blade (loft) |
| `_DEFAULT_PROPELLER_ROOT_PITCH_DEG` | 45.0 | blade pitch at root |
| `_DEFAULT_PROPELLER_TIP_PITCH_DEG` | 20.0 | blade pitch at tip (≠ root ⇒ twist) |
| `_DEFAULT_RUDDER_NACA_T` | 0.18 | rudder foil thickness ratio |
| `_DEFAULT_COUPLING_FLANGE_DIAMETER_MM` | 120.0 | collar disc Ø (> shaft Ø) |
| `_DEFAULT_COUPLING_FLANGE_THICKNESS_MM` | 25.0 | collar disc axial thickness |
| `_DEFAULT_COUPLING_BOLT_COUNT` | 6 | bolt-head bosses in the flange ring |
| `_DEFAULT_STRUT_COUNT` | 1 | struts per shaft |
| `_DEFAULT_STRUT_ARM_WIDTH_MM` | 40.0 | strut arm width |
| `_DEFAULT_SHAFT_LOG_FAIRING_LENGTH_MM` | 160.0 | fairing axial length |
| `_DEFAULT_SHAFT_LOG_FAIRING_DIAMETER_RATIO` | 2.4 | fairing Ø ÷ shaft Ø |
| `_DEFAULT_ENGINE_SUMP_DROP_MM` | 120.0 | sump depth below block bottom (< bed height 200 ⇒ above keel) |
| `_DEFAULT_ENGINE_SUMP_INSET_MM` | 80.0 | sump narrower than block per side |
| `_DEFAULT_ENGINE_HEAD_HEIGHT_MM` | 160.0 | head/valve-cover height above block |
| `_DEFAULT_ENGINE_MANIFOLD_STUB_COUNT` | 4 | exhaust-manifold stubs on one side |
| `_DEFAULT_ENGINE_MANIFOLD_STUB_DIAMETER_MM` | 40.0 | stub Ø |
| `_MIN_BLADE_SECTIONS` | 2 | loft floor |

Detail master defaults (per clarify Q1 — ON, pending spike): `airfoil_blades=True`, `naca_foil=True`, `coupling_flange=True`, `strut_bearing=True`, `shaft_log_fairing=True`, `engine.detailed=True`. (The spike, T001, may flip a specific one to `False`.)

## Parameter dataclasses (frozen) — appended fields

### `EngineParameters` (existing: length/width/height/station_x)
```
detailed: bool = True
sump_drop_mm: float = _DEFAULT_ENGINE_SUMP_DROP_MM
sump_inset_mm: float = _DEFAULT_ENGINE_SUMP_INSET_MM
head_height_mm: float = _DEFAULT_ENGINE_HEAD_HEIGHT_MM
manifold_stub_count: int = _DEFAULT_ENGINE_MANIFOLD_STUB_COUNT
manifold_stub_diameter_mm: float = _DEFAULT_ENGINE_MANIFOLD_STUB_DIAMETER_MM
```
Validation (`__post_init__`, before any FreeCAD call):
- `detailed` ⇒ `sump_drop_mm > 0`, `head_height_mm > 0`, `manifold_stub_diameter_mm > 0` (positive/finite)
- `detailed` ⇒ `2·sump_inset_mm < width_mm` (sump stays inside the block)
- `manifold_stub_count >= 0` (0 ⇒ no stubs)

### `ShaftParameters` (existing: diameter/angle/exit_x)
```
coupling_flange: bool = True
coupling_flange_diameter_mm: float = _DEFAULT_COUPLING_FLANGE_DIAMETER_MM
coupling_flange_thickness_mm: float = _DEFAULT_COUPLING_FLANGE_THICKNESS_MM
coupling_bolt_count: int = _DEFAULT_COUPLING_BOLT_COUNT
strut_bearing: bool = True
strut_count: int = _DEFAULT_STRUT_COUNT
strut_arm_width_mm: float = _DEFAULT_STRUT_ARM_WIDTH_MM
shaft_log_fairing: bool = True
shaft_log_fairing_length_mm: float = _DEFAULT_SHAFT_LOG_FAIRING_LENGTH_MM
shaft_log_fairing_diameter_ratio: float = _DEFAULT_SHAFT_LOG_FAIRING_DIAMETER_RATIO
```
Validation:
- `coupling_flange` ⇒ `coupling_flange_diameter_mm > diameter_mm`, `coupling_flange_thickness_mm > 0`, `coupling_bolt_count >= 0`
- `strut_bearing` ⇒ `strut_count >= 1`, `strut_arm_width_mm > 0`
- `shaft_log_fairing` ⇒ `shaft_log_fairing_diameter_ratio > 1.0`, `shaft_log_fairing_length_mm > 0`

### `PropellerParameters` (existing: diameter/hub_diameter/blade_count)
```
airfoil_blades: bool = True
naca_thickness_ratio: float = _DEFAULT_PROPELLER_NACA_T
blade_sections: int = _DEFAULT_PROPELLER_BLADE_SECTIONS
root_pitch_deg: float = _DEFAULT_PROPELLER_ROOT_PITCH_DEG
tip_pitch_deg: float = _DEFAULT_PROPELLER_TIP_PITCH_DEG
```
Validation:
- `airfoil_blades` ⇒ `0 < naca_thickness_ratio < 1`
- `airfoil_blades` ⇒ `blade_sections >= _MIN_BLADE_SECTIONS`
- `airfoil_blades` ⇒ `root_pitch_deg != tip_pitch_deg` (non-zero twist)

### `RudderParameters` (existing: chord/span/thickness/stock_diameter)
```
naca_foil: bool = True
naca_thickness_ratio: float = _DEFAULT_RUDDER_NACA_T
```
Validation:
- `naca_foil` ⇒ `0 < naca_thickness_ratio < 1`

All raise the existing `PropulsionParameterError(name, value, valid_range)`. `PropulsionParameters` composite is unchanged in shape (it already nests the four above).

## Result wrappers — appended fields

| Wrapper | New fields (defaults) |
|---|---|
| `EngineBlock` | `detail_requested: bool = False`, `detail_applied: bool = False` |
| `Shaft` | `has_coupling_flange: bool = False`, `has_shaft_log_fairing: bool = False` |
| `Propeller` | `airfoil_requested: bool = False`, `airfoil_applied: bool = False`, `root_to_tip_twist_deg: float = 0.0` |
| `Rudder` | `naca_requested: bool = False`, `naca_applied: bool = False` |

### NEW wrapper `Strut`
```
@dataclass
class Strut:
    body: Any
    parameters: ShaftParameters
    is_port: bool
    top_z_mm: float
    bottom_z_mm: float
    volume_mm3: float
```
`supports_shaft` is implied (`top_z_mm > bottom_z_mm`); the geometry test asserts the strut top reaches up toward the hull bottom.

### `Propulsion` aggregate — appended field
```
struts: list[Strut] = field(default_factory=list)
```
(after `rudders`, before `hull_modified`/`build_duration_seconds` — appended with a default so construction stays back-compat).

## State / control flow (no entity state machine)

There is no persistent state machine — `build_propulsion` is a single synchronous transaction (spec 014 triviality gate applies; `/tla` will confirm). The only "transition" is the per-body **manifold-or-fallback** decision:

```
detailed builder → produce body
    ├─ Solids==1 ∧ isValid()  → keep (applied=True)
    └─ else                    → CORE: rebuild spec 014 placeholder (applied=False)
                                 OPTIONAL (strut/fairing): omit body
```
Rollback on any uncaught FreeCAD failure removes every added object (spec 014 `_rollback`, unchanged).

## Compatibility

- **Frozen dataclass field order**: new fields are appended AFTER all existing fields, each with a default. Existing keyword construction (`EngineParameters(length_mm=..., width_mm=..., height_mm=..., station_x_mm=...)`) is unaffected; existing positional construction up to the last pre-existing field is unaffected. mypy --strict clean (all fields typed).
- **`Propulsion` construction**: only `build_propulsion` constructs it; `struts` has a default factory so no call site breaks.
- **`__all__`**: add `"Strut"`. Re-export from `storebro/__init__.py`.
- **`render._ROLE_RULES`**: add `("Propulsion_Strut", "bronze")`. The fairing is fused into `Propulsion_Shaft` (role `steel`, unchanged); coupling fused into the shaft likewise.
