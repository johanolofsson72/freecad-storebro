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


def render(V, out, right, up, vdir, light, size=(18, 6)):
    right, up, vdir = _n(right), _n(up), _n(vdir)
    sx, sy = V @ right, V @ up
    dep = V.mean(axis=1) @ vdir
    e1, e2 = V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]
    nrm = np.cross(e1, e2)
    ln = np.linalg.norm(nrm, axis=1)
    ln[ln == 0] = 1
    nrm /= ln[:, None]
    sh = 0.32 + 0.68 * np.clip(np.abs(nrm @ _n(light)), 0, 1)
    order = np.argsort(dep)
    P = np.stack([sx, sy], axis=-1)
    fig = plt.figure(figsize=size, dpi=110)
    ax = fig.add_subplot(111)
    ax.add_collection(
        PolyCollection(
            [P[i] for i in order],
            facecolors=[(0.55 * s, 0.57 * s, 0.61 * s) for s in sh[order]],
            edgecolors="none",
            antialiased=False,
        )
    )
    a = P.reshape(-1, 2)
    ax.set_xlim(a[:, 0].min(), a[:, 0].max())
    ax.set_ylim(a[:, 1].min(), a[:, 1].max())
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("WROTE", out)


def main() -> None:
    stl, base = sys.argv[1], sys.argv[2]
    V = load_stl(stl)
    print("triangles", len(V))
    render(V, base + "_side.png", (1, 0, 0), (0, 0, 1), (0, 1, 0), (0.3, -0.6, 0.7), (18, 6))
    render(V, base + "_top.png", (1, 0, 0), (0, -1, 0), (0, 0, -1), (0.2, -0.4, 0.9), (18, 6))
    vdir = _n((0.55, 0.6, -0.55))
    right = _n(np.cross(vdir, (0, 0, 1)))
    up2 = np.cross(right, vdir)
    render(V, base + "_iso.png", right, up2, vdir, (0.4, -0.4, 0.8), (16, 11))


main()
