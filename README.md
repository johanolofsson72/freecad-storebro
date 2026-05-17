# freecad-storebro

> Parametric 3D model of a vintage Storebro motor yacht inside FreeCAD.

`freecad-storebro` is an open-source Python library that builds a fully editable parametric model of a classic Storebro Royal Cruiser. Given a small set of hull parameters (LOA, beam, draft, deadrise, sheer, transom angle, freeboard), it produces a `Part::Body` you can compose with your own FreeCAD geometry — and a `.FCStd` document you can open in the FreeCAD GUI and edit dimension-by-dimension.

The canonical default hull matches the **Storebro Royal Cruiser 34, 1972 model year** (LOA 10.35 m, beam 3.20 m) within ±1% on principal dimensions.

## Installation

```bash
uv pip install freecad-storebro
```

FreeCAD 1.1 or later must be installed separately and on `PATH`. See "Supported FreeCAD versions" below.

## Quickstart

```bash
pip install freecad-storebro

# Build the canonical Storebro Royal Cruiser 34 1972:
storebro build --out boat.FCStd

# Inspect what shipped with the package:
storebro list-layouts
storebro info
```

Open `boat.FCStd` in FreeCAD — hull, deck, and the canonical Alternativ3 interior, all parametrically editable.

For the full CLI walkthrough see [`docs/examples/cli_quickstart.sh`](docs/examples/cli_quickstart.sh) or [`specs/005-cli-module/quickstart.md`](specs/005-cli-module/quickstart.md). For non-fcstd formats: `--format step | stl | brep` exports the hull body only (full-assembly STEP/STL/BREP is deferred to v1.1+).

### Python API

For programmatic use (custom parameters, variant studies, error handling), the underlying functions are also public:

```python
from storebro import build_hull, build_deck, build_interior, export_fcstd

hull = build_hull()
deck = build_deck(hull)
build_interior(hull, deck, layout="Alternativ3")
art = export_fcstd(hull.document, "/tmp/boat.FCStd")
print(f"wrote {art.byte_count} bytes, SHA-256 {art.sha256}")
```

See [`docs/examples/`](docs/examples/) and the per-spec `quickstart.md` files for deeper walkthroughs.

## Supported FreeCAD versions

This library is tested and supported on:

- **FreeCAD: `>=1.1, <2.0`** (declared in `pyproject.toml` under `[tool.freecad-storebro] supported_freecad`)
- Python: 3.11, 3.12

The version range is verified at runtime on the first invocation of `build_hull()` (lazy check); running on an unsupported FreeCAD version raises `HullConstructionError` immediately, before any geometry construction.

Per the project constitution (principle VII), the supported range is declared in BOTH `pyproject.toml` and this README. If you find these out of sync, please open an issue — it is a constitutional violation.

## Project status

v1.0.0 — all four library modules plus the CLI. The five specs are tracked in [`specs/INDEX.md`](specs/INDEX.md).

| Module | Spec | Status |
|---|---|---|
| `storebro.hull` | [001](specs/001-hull-module/) | v1.0.0 |
| `storebro.export` | [002](specs/002-export-module/) | v1.0.0 |
| `storebro.deck` | [003](specs/003-deck-module/) | v1.0.0 |
| `storebro.interior` | [004](specs/004-interior-module/) | v1.0.0 |
| `storebro.cli` | [005](specs/005-cli-module/) | v1.0.0 |

## License

MIT. See [LICENSE](LICENSE) if present; otherwise the MIT text applies via the `license` field in `pyproject.toml`.
