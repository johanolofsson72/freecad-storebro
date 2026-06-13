"""Render a Storebro model in its real spec-015 colours — the colour render path.

Usage (this machine):
    # 1. export per-colour STLs (FreeCAD):
    OUT=/tmp/x.stl COLOR_DIR=/tmp/cols MODE=silhouette \
        /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd scripts/fc_build_export.py
    # 2. render in colour:
    uv run --with numpy --with matplotlib python scripts/project_color.py /tmp/cols /tmp/boat

Reads the col_RRGGBBAA.stl groups written by fc_build_export.py's COLOR_DIR mode
(one STL per distinct RenderColor) and renders shaded side/iso PNGs with each group
in its own colour — gelcoat-white hull, teak trim, translucent blue glass. This is
the photo-faithful render path (vs project_views.py's flat-grey silhouette); use it
to compare against docs/references/Alternativ*.JPG.
"""

from __future__ import annotations

import glob
import os
import struct
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

_BG = (0.86, 0.90, 0.95)  # pale sky/water


def load_stl(path: str) -> np.ndarray:
    with open(path, "rb") as fh:
        data = fh.read()
    n = struct.unpack("<I", data[80:84])[0]
    tri = np.frombuffer(data[84 : 84 + 50 * n], dtype=np.uint8).reshape(n, 50)
    return tri[:, :48].copy().view("<f4").reshape(n, 12)[:, 3:12].reshape(n, 3, 3)


def _n(v: object) -> np.ndarray:
    a = np.asarray(v, float)
    return a / np.linalg.norm(a)


def render(color_dir, out, right, up, vdir, light, size):
    right, up, vdir, light = _n(right), _n(up), _n(vdir), _n(light)
    polys: list = []
    cols: list = []
    deps: list = []
    for f in sorted(glob.glob(os.path.join(color_dir, "col_*.stl"))):
        hexs = os.path.basename(f)[4:12]
        r, g, b = (int(hexs[i : i + 2], 16) / 255 for i in (0, 2, 4))
        V = load_stl(f)
        if not len(V):
            continue
        sx, sy = V @ right, V @ up
        dep = V.mean(axis=1) @ vdir
        e1, e2 = V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]
        nrm = np.cross(e1, e2)
        ln = np.linalg.norm(nrm, axis=1)
        ln[ln == 0] = 1
        nrm /= ln[:, None]
        sh = 0.45 + 0.55 * np.clip(np.abs(nrm @ light), 0, 1)
        P = np.stack([sx, sy], axis=-1)
        polys += list(P)
        cols += [(r * s, g * s, b * s) for s in sh]
        deps += list(dep)
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
    fig.savefig(out, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    print("WROTE", out)


def main() -> None:
    color_dir, base = sys.argv[1], sys.argv[2]
    render(color_dir, base + "_side.png", (1, 0, 0), (0, 0, 1), (0, 1, 0), (0.3, -0.6, 0.7), (18, 6))
    vdir = _n((0.55, 0.6, -0.55))
    right = _n(np.cross(vdir, (0, 0, 1)))
    up2 = np.cross(right, vdir)
    render(color_dir, base + "_iso.png", right, up2, vdir, (0.4, -0.4, 0.85), (16, 11))


main()
