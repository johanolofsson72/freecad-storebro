"""Runnable example: storebro.deck quickstart.

Mirrors the first three sections of `specs/003-deck-module/quickstart.md`.
Requires FreeCAD 1.1+ on PATH.

Run with:
    uv run python docs/examples/deck_quickstart.py
"""

from __future__ import annotations

from storebro import DeckParameters, build_deck, build_hull, export_fcstd


def main() -> None:
    # 1) Default deck on default hull.
    hull = build_hull()
    deck = build_deck(hull)

    print(f"Built {deck.label} on {hull.label}")
    print(f"  Cabin trunk: {deck.cabin_trunk.length:.2f} m x "
          f"{deck.cabin_trunk.width:.2f} m x {deck.cabin_trunk.height:.2f} m")
    print(f"  Hardtop:     {deck.hardtop.length:.2f} m "
          f"(height above cabin: {deck.hardtop.height_above_cabin:.2f} m)")
    print(f"  Railings:    {deck.railings.height * 100:.0f} cm")
    print(f"  Built in:    {deck.build_duration_seconds:.2f} s")

    # 2) Save whole-boat .FCStd via spec 002.
    art = export_fcstd(hull.document, "/tmp/storebro_whole_boat.FCStd")
    print(f"\nSaved {art.byte_count} bytes to {art.target_path}")

    # 3) Custom dimensions.
    custom = DeckParameters(
        cabin_trunk_height=1.00,
        hardtop_height=0.15,
        railing_height=0.80,
        windshield_rake=35.0,
    )
    hull2 = build_hull()
    deck2 = build_deck(hull2, custom)
    print(
        f"\nSportfish silhouette: cabin {deck2.cabin_trunk.height:.2f} m, "
        f"hardtop above cabin {deck2.hardtop.height_above_cabin:.2f} m"
    )


if __name__ == "__main__":
    main()
