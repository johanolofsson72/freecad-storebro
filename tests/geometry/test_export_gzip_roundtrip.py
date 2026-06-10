"""Geometry test: gzip composes with every shipped format (spec 026 US6, T018).

Covers FR-006, SC-004. A gzipped export decompresses to the un-gzipped one and
two gzipped exports are byte-identical.
"""

from __future__ import annotations

import gzip

import pytest

from storebro import build_deck, build_hull, export_iges, export_obj, export_stl


@pytest.mark.requires_freecad
@pytest.mark.parametrize(
    ("fn", "ext"),
    [(export_stl, "stl"), (export_obj, "obj"), (export_iges, "iges")],
)
def test_gzip_roundtrips_and_is_deterministic(freecad_doc, tmp_path, fn, ext) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    bodies = [hull.body, deck.deck_plate.body]
    plain = fn(bodies, tmp_path / f"b.{ext}")
    gz1 = fn(bodies, tmp_path / f"b.{ext}.gz", gzip=True)
    gz2 = fn(bodies, tmp_path / f"c.{ext}.gz", gzip=True)
    # Decompressed gzip equals the un-gzipped export.
    raw = (tmp_path / f"b.{ext}").read_bytes()
    assert gzip.decompress((tmp_path / f"b.{ext}.gz").read_bytes()) == raw
    # Two gzipped exports are byte-identical (mtime zeroed).
    assert gz1.sha256 == gz2.sha256
    assert plain.byte_count > 0
