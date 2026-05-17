"""Geometry test: deck parameter parametricity (T030).

Covers SC-004. For each named parameter, ±10% perturbation moves a
corresponding measurement monotonically.
"""

from __future__ import annotations

import dataclasses

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import DeckParameters, build_deck, build_hull


@pytest.mark.parametrize(
    "field,bbox_ratio",
    [
        ("cabin_trunk_length", 1.10),
        ("hardtop_length", 1.10),
        ("railing_height", 1.10),
    ],
)
def test_perturbation_increases_corresponding_dimension(field: str, bbox_ratio: float) -> None:
    doc_default = FreeCAD.newDocument("ParametricityDefault3")
    doc_perturbed = FreeCAD.newDocument("ParametricityPerturbed3")
    try:
        h_default = build_hull(document=doc_default)
        h_perturbed = build_hull(document=doc_perturbed)

        defaults = DeckParameters()
        new_value = getattr(defaults, field) * bbox_ratio
        perturbed = dataclasses.replace(defaults, **{field: new_value})

        d_default = build_deck(h_default, defaults)
        d_perturbed = build_deck(h_perturbed, perturbed)

        if field == "cabin_trunk_length":
            assert d_perturbed.cabin_trunk.length > d_default.cabin_trunk.length
        elif field == "hardtop_length":
            assert d_perturbed.hardtop.length > d_default.hardtop.length
        elif field == "railing_height":
            assert d_perturbed.railings.height > d_default.railings.height
    finally:
        FreeCAD.closeDocument(doc_default.Name)
        FreeCAD.closeDocument(doc_perturbed.Name)
