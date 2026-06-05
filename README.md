# freecad-storebro

A Python library that builds a parametric 3D model of a vintage Storebro motor yacht inside FreeCAD. Give it hull dimensions and an interior layout, and it produces an editable `.FCStd` document plus STEP, STL, and BREP exports. The default hull matches the Storebro Royal Cruiser 34, 1972 model year (LOA 10.35 m, beam 3.20 m), within ±1% on the principal dimensions. The geometry stays editable in the FreeCAD GUI — it is built from `PartDesign` and `Part` features, not baked into a mesh.

The package is published on PyPI as `freecad-storebro` and imported as `storebro`.

## What's in the repo

The source lives under `src/storebro/`, one module per part of the boat:

- `hull.py` — the parametric hull (LOA, beam, draft, deadrise, sheer line, transom angle, stem rake). A dense `Ruled=True` `PartDesign::AdditiveLoft` mirrored to a full hull.
- `deck.py` — deck plate, cabin trunk, windshield, hardtop, pillars, railings, plus the deck hardware (rubrail, bow pulpit, lifelines, anchor locker, cleats). Also the DS deck-saloon (`styrhytt`) variant — an enclosed wheelhouse that replaces the open flybridge.
- `interior.py` — cabins, galley, head, salon, bulkheads, and contoured furniture, driven by five canonical layouts (Alternativ1–5) loaded from YAML.
- `propulsion.py` — engine bed, engine block, propeller shaft, propeller, and rudder. Twin-screw by default; single-screw on request.
- `export.py` — the `.FCStd`, STEP, STL, and BREP writers. Same parameters give byte-identical output.
- `render.py` — role-keyed colors and materials (gelcoat-white hull, teak trim, chrome hardware, glass windows, bronze running gear), stored as data properties on each body.
- `cli.py` — the `storebro` command.

The five interior layouts are YAML fixtures in `src/storebro/fixtures/` (`Alternativ1.yaml` through `Alternativ5.yaml`, plus `DsSaloon.yaml` for the deck-saloon variant). Each one describes its compartments — name, type, position, dimensions — so you can write your own layout file without touching the code.

`docs/references/` holds the side-profile drawings (`Alternativ1.JPG`–`Alternativ5.JPG`) and the GRP hull-construction and lines drawings the geometry was derived from. `docs/examples/` has runnable quickstarts for the hull, deck, export, and CLI.

The model is parameter-driven throughout — no hard-coded dimensions — and reproducible: the same inputs produce the same bytes, with hash-based regression tests in `tests/geometry/` and pure-Python parameter tests in `tests/unit/`.

## Installing

```bash
uv pip install freecad-storebro
# or: pip install freecad-storebro
```

FreeCAD 1.1 or later must be installed separately and importable. The supported range (`>=1.1,<2.0`) is declared in `pyproject.toml` under `[tool.freecad-storebro]` and checked at runtime on the first `build_hull()` call — an unsupported FreeCAD version raises `HullConstructionError` before any geometry is built. Python 3.11 and 3.12 are supported.

## Using it

From the command line:

```bash
# Build the default Storebro Royal Cruiser 34, 1972, with the Alternativ3 interior:
storebro build --out boat.FCStd

# Other formats export the hull body only:
storebro build --out hull.step --format step   # also: stl, brep

# The DS deck-saloon variant, single screw, no colors:
storebro build --out ds.FCStd --superstructure ds --engine-count 1 --no-colors

# Machine-readable result (format, target_path, byte_count, sha256, version):
storebro build --out boat.FCStd --json

storebro list-layouts   # the five canonical interior layouts
storebro info           # package, Python, FreeCAD, and platform metadata
```

`storebro build` also takes hull overrides — `--loa`, `--beam`, `--draft`, `--station-count` (3–81, higher is smoother) — and `--no-propulsion` for hull + deck + interior only. See `docs/examples/cli_quickstart.sh` for the full walkthrough.

From Python, the build functions and parameter classes are public:

```python
from storebro import build_hull, build_deck, build_interior, export_fcstd

hull = build_hull()
deck = build_deck(hull)
build_interior(hull, deck, layout="Alternativ3")
art = export_fcstd(hull.document, "/tmp/boat.FCStd")
print(f"wrote {art.byte_count} bytes, SHA-256 {art.sha256}")
```

`build_propulsion` and `apply_render_attributes` are public too, along with the per-part parameter dataclasses. See `docs/examples/` for hull, deck, and export examples.

## Status

Current version is 1.10.0. The hull, deck, interior, propulsion, export, render, and CLI modules all work end-to-end, and the model is recognizable as an RC34 in the FreeCAD GUI. The geometry tier runs on FreeCAD 1.1.1.

Known limits, all tracked in the specs:

- The hull is a dense `Ruled=True` loft, not a B-spline surface. A FreeCAD spike showed `Ruled=False` overshooting the beam by 12–141% on this profile, so smoothness comes from station density (31 by default) rather than interpolation. The quarter-circle bilge arc is deferred for the same reason — its tessellated mesh is not watertight — so the hull keeps a sharp chine.
- Propulsion geometry is representative, not CAD-faithful: the engine is a block, the propeller blades are flat plates, the rudder is a foil plate.
- Cross-invocation `.FCStd` byte determinism is still being worked (`storebro build` is byte-stable within a process, and STEP/STL/BREP are byte-stable across invocations).

The full per-spec history is in `specs/INDEX.md` and `CHANGELOG.md`. The reference drawings are artistic side profiles, not engineering drawings, so dimensions are inferred to a ±1% tolerance rather than measured.

## License

MIT. The `license` field in `pyproject.toml` carries the MIT declaration; there is no separate `LICENSE` file in the repo yet.

Author: Johan Olofsson.
