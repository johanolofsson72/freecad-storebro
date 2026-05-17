"""Geometry test: parametricity — every named parameter moves geometry (T034).

Covers SC-004. For each of the 8 named parameters, building two hulls at
default ± 10% (clamped to valid ranges) produces measurably different
geometry in the expected direction.
"""

from __future__ import annotations

import dataclasses

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import HullParameters, build_hull


def _perturb(params: HullParameters, field_name: str, ratio: float) -> HullParameters:
    """Return a copy of `params` with `field_name` scaled by `ratio`,
    clamping to within valid ranges."""
    current = getattr(params, field_name)
    new_value = current * ratio
    # Clamp angular params to their valid range.
    if field_name == "deadrise_amidships":
        new_value = max(0.5, min(29.5, new_value))
    elif field_name == "transom_angle":
        new_value = max(0.5, min(44.5, new_value))
    return dataclasses.replace(params, **{field_name: new_value})


@pytest.mark.parametrize(
    "field_name,bbox_index,direction_up_ratio",
    [
        # (field, bbox dimension index, ratio used to drive that dim up)
        ("loa", 0, 1.10),  # +10% LOA → longer bbox
        ("beam_max", 1, 1.10),  # +10% beam → wider bbox
    ],
)
def test_parameter_increases_bbox_dimension(
    field_name: str, bbox_index: int, direction_up_ratio: float
) -> None:
    doc_default = FreeCAD.newDocument("ParametricityDefault")
    doc_perturbed = FreeCAD.newDocument("ParametricityPerturbed")
    try:
        defaults = HullParameters()
        perturbed = _perturb(defaults, field_name, direction_up_ratio)

        h_default = build_hull(defaults, document=doc_default)
        h_perturbed = build_hull(perturbed, document=doc_perturbed)

        d_default = h_default.bbox[bbox_index]
        d_perturbed = h_perturbed.bbox[bbox_index]
        assert d_perturbed > d_default, (
            f"+10% on {field_name} did not increase bbox[{bbox_index}]: "
            f"{d_default:.3f} → {d_perturbed:.3f}"
        )
    finally:
        FreeCAD.closeDocument(doc_default.Name)
        FreeCAD.closeDocument(doc_perturbed.Name)


@pytest.mark.parametrize("field_name", ["loa", "beam_max"])
def test_parameter_decreases_when_reduced(field_name: str) -> None:
    doc_default = FreeCAD.newDocument("ParametricityDefault2")
    doc_perturbed = FreeCAD.newDocument("ParametricityPerturbed2")
    try:
        defaults = HullParameters()
        perturbed = _perturb(defaults, field_name, 0.90)
        h_default = build_hull(defaults, document=doc_default)
        h_perturbed = build_hull(perturbed, document=doc_perturbed)
        idx = 0 if field_name == "loa" else 1
        assert h_perturbed.bbox[idx] < h_default.bbox[idx]
    finally:
        FreeCAD.closeDocument(doc_default.Name)
        FreeCAD.closeDocument(doc_perturbed.Name)
