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

```python
from storebro import build_hull

hull = build_hull()
hull.document.saveAs("/tmp/storebro_default.FCStd")
print(f"LOA={hull.bbox[0]:.2f} m, beam={hull.bbox[1]:.2f} m")
```

For more examples — custom parameters, multi-hull variant studies, error handling — see [`docs/examples/`](docs/examples/) and [`specs/001-hull-module/quickstart.md`](specs/001-hull-module/quickstart.md).

## Supported FreeCAD versions

This library is tested and supported on:

- **FreeCAD: `>=1.1, <2.0`** (declared in `pyproject.toml` under `[tool.freecad-storebro] supported_freecad`)
- Python: 3.11, 3.12

The version range is verified at runtime on the first invocation of `build_hull()` (lazy check); running on an unsupported FreeCAD version raises `HullConstructionError` immediately, before any geometry construction.

Per the project constitution (principle VII), the supported range is declared in BOTH `pyproject.toml` and this README. If you find these out of sync, please open an issue — it is a constitutional violation.

## Project status

This is alpha software. The hull module (spec 001) is the first deliverable. Subsequent modules (export, deck, interior, CLI) are tracked in [`specs/INDEX.md`](specs/INDEX.md).

| Module | Spec | Status |
|---|---|---|
| `storebro.hull` | [001](specs/001-hull-module/) | v0.1.0-alpha (in progress) |
| `storebro.export` | [002](specs/002-export-module/) | v0.2.0-alpha (implemented; geometry tests pending FreeCAD host) |
| `storebro.deck` | [003](specs/003-deck-module/) | v0.3.0-alpha (implemented; geometry tests pending FreeCAD host) |
| `storebro.interior` | [004](specs/004-interior-module/) | v0.4.0-alpha (implemented; geometry tests pending FreeCAD host) |
| `storebro.cli` | [005](specs/INDEX.md) | not started |

## License

MIT. See [LICENSE](LICENSE) if present; otherwise the MIT text applies via the `license` field in `pyproject.toml`.
