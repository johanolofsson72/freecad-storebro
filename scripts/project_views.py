"""Project an STL mesh into clean orthographic PNG views — the reliable render path.

Usage (this machine):
    uv run --with numpy --with matplotlib python scripts/project_views.py <in.stl> <out_prefix>

Writes <out_prefix>_side.png, _top.png, _iso.png. Flat-shaded painter's-algorithm
projection — no OpenGL, so it works headlessly where FreeCAD's offscreen renderer
gives blank or single-angle frames. Pairs with scripts/fc_build_export.py.

This is the render step of the visual-fidelity loop (.claude/rules/visual-fidelity-loop.md):
build (freecadcmd) -> STL -> project here -> compare to docs/references/storo34_side_lines.png.
"""

from __future__ import annotations

import struct
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def load_stl(path: str) -> np.ndarray:
    with open(path, "rb") as fh:
        data = fh.read()
    n = struct.unpack("<I", data[80:84])[0]
    tri = np.frombuffer(data[84 : 84 + 50 * n], dtype=np.uint8).reshape(n, 50)
    return tri[:, :48].copy().view("<f4").reshape(n, 12)[:, 3:12].reshape(n, 3, 3)


def _n(v: object) -> np.ndarray:
    a = np.asarray(v, float)
    return a / np.linalg.norm(a)


def _tris(V, right, up, vdir, light, base_tone):
    """Return (polys, colors, depths) for one mesh shaded at base_tone."""
    sx, sy = V @ right, V @ up
    dep = V.mean(axis=1) @ vdir
    e1, e2 = V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]
    nrm = np.cross(e1, e2)
    ln = np.linalg.norm(nrm, axis=1)
    ln[ln == 0] = 1
    nrm /= ln[:, None]
    sh = 0.32 + 0.68 * np.clip(np.abs(nrm @ light), 0, 1)
    P = np.stack([sx, sy], axis=-1)
    cols = [(base_tone * s, base_tone * s, min(base_tone * s * 1.08, 1.0)) for s in sh]
    return list(P), cols, list(dep)


def render(V, out, right, up, vdir, light, size=(18, 6), glass=None):
    right, up, vdir, light = _n(right), _n(up), _n(vdir), _n(light)
    polys, cols, deps = _tris(V, right, up, vdir, light, 0.86)
    if glass is not None and len(glass):
        # Glass/window bodies render dark so the window band + portholes read.
        gp, gc, gd = _tris(glass, right, up, vdir, light, 0.22)
        polys += gp
        cols += gc
        deps += gd
    order = np.argsort(deps)
    fig = plt.figure(figsize=size, dpi=110)
    ax = fig.add_subplot(111)
    ax.add_collection(
        PolyCollection(
            [polys[i] for i in order],
            facecolors=[cols[i] for i in order],
            edgecolors="none",
            antialiased=False,
        )
    )
    a = np.concatenate(polys)
    ax.set_xlim(a[:, 0].min(), a[:, 0].max())
    ax.set_ylim(a[:, 1].min(), a[:, 1].max())
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("WROTE", out)


def main() -> None:
    stl, base = sys.argv[1], sys.argv[2]
    glass = load_stl(sys.argv[3]) if len(sys.argv) > 3 else None  # optional dark glass STL
    V = load_stl(stl)
    print("triangles", len(V), "glass", 0 if glass is None else len(glass))
    render(V, base + "_side.png", (1, 0, 0), (0, 0, 1), (0, 1, 0), (0.3, -0.6, 0.7), (18, 6), glass)
    render(V, base + "_top.png", (1, 0, 0), (0, -1, 0), (0, 0, -1), (0.2, -0.4, 0.9), (18, 6), glass)
    vdir = _n((0.55, 0.6, -0.55))
    right = _n(np.cross(vdir, (0, 0, 1)))
    up2 = np.cross(right, vdir)
    render(V, base + "_iso.png", right, up2, vdir, (0.4, -0.4, 0.8), (16, 11), glass)


main()
