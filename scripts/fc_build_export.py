"""Build a Storebro model and export it to STL — run under FreeCAD's bundled Python.

Usage (this machine):
    OUT=/tmp/sil.stl MODE=silhouette VARIANT=standard LAYOUT=Alternativ3 \
        /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd scripts/fc_build_export.py

Env vars:
    OUT      output .stl path (required)
    MODE     "silhouette" (hull + cabin, no railings — fast, for elevation views)
             | "exterior" (hull + deck, incl. hardware) | "hull" (hull only)
             | "full" (hull + deck + interior)          [default: silhouette]
    VARIANT  hull_variant: standard | hard_chine        [default: standard]
    LAYOUT   interior layout for MODE=full              [default: Alternativ3]

freecadcmd does not forward argv reliably, so everything is passed via env.
Pairs with scripts/project_views.py (run under `uv run --with numpy --with matplotlib`),
which projects the STL into clean orthographic side/top/iso PNGs — the reliable render
path for the visual-fidelity loop (FreeCAD's offscreen GL only renders one angle here).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

import FreeCAD  # type: ignore[import-not-found]
import Mesh  # type: ignore[import-not-found]

from storebro.deck import build_deck
from storebro.hull import build_hull

_SOLID = ("PartDesign::Body", "Part::Feature", "Part::Compound")
# Excluded from the silhouette: high-triangle-count hardware that clutters an
# elevation and slows the projector without changing the read of the boat.
_SILHOUETTE_EXCLUDE = (
    "Railing", "Lifeline", "Pulpit", "Stanchion", "Cleat", "Anchor", "Rubrail", "Interior",
)


def main() -> None:
    out = os.environ["OUT"]
    mode = os.environ.get("MODE", "silhouette")
    variant = os.environ.get("VARIANT", "standard")
    deck_variant = os.environ.get("DECK", "standard")  # standard | ds
    layout = os.environ.get("LAYOUT", "Alternativ3")

    doc = FreeCAD.newDocument("export")
    hull = build_hull(document=doc, hull_variant=variant)
    if mode != "hull":
        deck = build_deck(hull, superstructure_variant=deck_variant)
        if mode == "full":
            from storebro.interior import build_interior

            build_interior(hull, deck, layout=layout)
    doc.recompute()

    objs = [
        o
        for o in doc.Objects
        if o.TypeId in _SOLID
        and getattr(o, "Shape", None) is not None
        and len(o.Shape.Solids) >= 1
    ]
    if mode == "hull":
        objs = [o for o in objs if (o.Label or "").startswith("Hull")]
    elif mode == "silhouette":
        objs = [o for o in objs if not any(k in (o.Label or "") for k in _SILHOUETTE_EXCLUDE)]

    # Optional: COLOR_DIR mode — group bodies by their spec-015 RenderColor and
    # export one STL per colour (named col_RRGGBBAA.stl), so the projector can render
    # the boat in its real colours (gelcoat-white hull, teak trim, translucent glass)
    # instead of flat grey — a big jump toward matching the reference photos.
    color_dir = os.environ.get("COLOR_DIR")
    if color_dir:
        groups: dict[tuple[int, ...], list[object]] = {}
        for o in objs:
            rc = getattr(o, "RenderColor", None) or (0.8, 0.8, 0.8, 1.0)
            key = tuple(round(c * 255) for c in rc)
            groups.setdefault(key, []).append(o)
        for key, members in groups.items():
            name = "col_{:02x}{:02x}{:02x}{:02x}.stl".format(*key)
            Mesh.export(members, os.path.join(color_dir, name))
        print(f"exported {len(objs)} bodies in {len(groups)} colour groups -> {color_dir}")
        return

    # Optional: split glass/window bodies into a separate STL (env GLASS) so the
    # projector can render them dark — makes the window band + portholes read.
    glass_out = os.environ.get("GLASS")
    if glass_out:
        glass = [o for o in objs if "Glass" in (o.Label or "") or "Window" in (o.Label or "")]
        objs = [o for o in objs if o not in glass]
        Mesh.export(glass, glass_out)
        print(f"exported {len(glass)} glass bodies -> {glass_out}")

    Mesh.export(objs, out)
    print(f"exported {len(objs)} bodies (mode={mode}) -> {out}")


main()
