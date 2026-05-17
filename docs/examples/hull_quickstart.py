"""Runnable example: storebro.hull quickstart.

Mirrors the first three sections of `specs/001-hull-module/quickstart.md`.
Requires FreeCAD 1.1+ on PATH.

Run with:
    uv run python docs/examples/hull_quickstart.py
"""

from __future__ import annotations

from storebro import HullParameters, build_hull


def main() -> None:
    # 1) Default Storebro Royal Cruiser 34 (1972).
    hull = build_hull()
    print(f"Default hull: {hull.label}")
    print(f"  LOA:      {hull.bbox[0]:.2f} m")
    print(f"  Beam:     {hull.bbox[1]:.2f} m")
    print(f"  Height:   {hull.bbox[2]:.2f} m")
    print(f"  Volume:   {hull.volume:.2f} m^3")
    print(f"  Built in: {hull.build_duration_seconds:.2f} s")

    # 2) Save to .FCStd for FreeCAD GUI inspection.
    out = "/tmp/storebro_default.FCStd"
    hull.document.saveAs(out)
    print(f"\nSaved to {out} — open in FreeCAD to inspect parametric history.")

    # 3) Custom parameters: wider, shorter, deeper.
    custom = HullParameters(
        loa=10.0,
        beam_max=3.5,
        draft=1.10,
        freeboard=1.00,
        deadrise_amidships=20.0,
        sheer_height_aft=0.95,
        sheer_height_fwd=1.45,
        transom_angle=10.0,
    )
    custom_hull = build_hull(custom)
    print(
        f"\nCustom hull: {custom_hull.bbox[0]:.2f} x "
        f"{custom_hull.bbox[1]:.2f} x {custom_hull.bbox[2]:.2f} m"
    )


if __name__ == "__main__":
    main()
