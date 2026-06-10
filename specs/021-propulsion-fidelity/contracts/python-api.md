# Public API Contract Delta: Propulsion Fidelity

This is a library; the contract is the public Python API + the CLI. Spec 021 is **additive only** (MINOR, 1.10.0 → 1.11.0). Nothing existing is removed or re-signatured.

## Unchanged (back-compat guarantee)

- `build_propulsion(hull, deck=None, parameters=None, *, document=None, name="Propulsion", apply_render_attributes=True) -> Propulsion` — **signature unchanged**. Default call now produces the CAD-faithful train (detail on by default).
- `Propulsion`, `EngineBed`, `EngineBlock`, `Shaft`, `Propeller`, `Rudder` — existing fields unchanged (new fields appended).
- `EngineBedParameters`, `EngineParameters`, `ShaftParameters`, `PropellerParameters`, `RudderParameters`, `PropulsionParameters` — existing fields unchanged (new fields appended with defaults).
- `PropulsionParameterError`, `PropulsionConstructionError` — unchanged.
- **SC-006 contract**: `PropulsionParameters` with every detail flag off (`engine.detailed=False`, `shaft.coupling_flange=False`, `shaft.strut_bearing=False`, `shaft.shaft_log_fairing=False`, `propeller.airfoil_blades=False`, `rudder.naca_foil=False`) MUST produce byte-identical geometry to the spec 014 build.

## Added — parameters (all keyword-defaulted; see data-model.md)

- `EngineParameters`: `detailed`, `sump_drop_mm`, `sump_inset_mm`, `head_height_mm`, `manifold_stub_count`, `manifold_stub_diameter_mm`
- `ShaftParameters`: `coupling_flange`, `coupling_flange_diameter_mm`, `coupling_flange_thickness_mm`, `coupling_bolt_count`, `strut_bearing`, `strut_count`, `strut_arm_width_mm`, `shaft_log_fairing`, `shaft_log_fairing_length_mm`, `shaft_log_fairing_diameter_ratio`
- `PropellerParameters`: `airfoil_blades`, `naca_thickness_ratio`, `blade_sections`, `root_pitch_deg`, `tip_pitch_deg`
- `RudderParameters`: `naca_foil`, `naca_thickness_ratio`

**Validation contract**: out-of-range/non-finite values raise `PropulsionParameterError(parameter_name, parameter_value, valid_range)` **before any FreeCAD call** (e.g. `propeller.naca_thickness_ratio = 1.5` → error; `shaft.coupling_flange_diameter_mm <= diameter_mm` → error; `2·sump_inset_mm >= width_mm` → error; `root_pitch_deg == tip_pitch_deg` with `airfoil_blades=True` → error).

## Added — result types

- **NEW** `Strut` dataclass: `body`, `parameters: ShaftParameters`, `is_port: bool`, `top_z_mm: float`, `bottom_z_mm: float`, `volume_mm3: float`. Exported from `storebro`.
- `Propulsion.struts: list[Strut]` — one per `(shaft × strut_count)` when `strut_bearing=True` and the gate passes; empty when off or omitted on gate failure.
- `EngineBlock.detail_requested`, `EngineBlock.detail_applied`
- `Shaft.has_coupling_flange`, `Shaft.has_shaft_log_fairing`
- `Propeller.airfoil_requested`, `Propeller.airfoil_applied`, `Propeller.root_to_tip_twist_deg`
- `Rudder.naca_requested`, `Rudder.naca_applied`

**Applied-flag contract**: `*_applied` is `True` only when the detailed construction was both requested AND passed its manifold gate; `False` means the body fell back to the spec 014 placeholder (still a single valid solid). For optional supports, gate failure means the body is simply absent from `struts` / `has_shaft_log_fairing=False`.

## Added — CLI (optional)

- `storebro build --no-propulsion-detail` — build the propulsion train at spec 014 placeholder fidelity (all detail flags off). Default (flag absent) = detailed train. Composes with `--engine-count`, `--no-propulsion`, `--no-colors`.

## Render roles

- `render._ROLE_RULES` gains `("Propulsion_Strut", "bronze")`. Coupling flange + shaft-log fairing are fused into `Propulsion_Shaft` (role `steel`, unchanged).

## Invariants the contract preserves

- Every produced body: `len(Shape.Solids) == 1 ∧ Shape.isValid()` and STL-exportable (FR-007).
- `Propulsion.hull_modified == False`; the hull `Shape`/volume is unchanged by the build (FR-006/SC-007).
- Identical inputs → byte-identical output (FR-008/SC-002).
