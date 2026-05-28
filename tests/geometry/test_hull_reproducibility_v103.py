"""Spec 009 T022 — reproducibility of STEP/STL/BREP exports under v1.0.3 hull.

Two identical ``build_hull(params)`` calls MUST produce byte-identical
STEP/STL/BREP exports. Verifies that the new denser-station + B-spline
+ bilge-arc geometry flows through the spec 002 deterministic writers
without regression.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro.export import export_brep, export_step, export_stl
from storebro.hull import HullParameters, build_hull

pytestmark = pytest.mark.requires_freecad


@pytest.mark.parametrize(
    "params",
    [
        HullParameters(),  # default v1.0.3 (denser stations + bilge arc)
        HullParameters(station_count=5),  # legacy
        HullParameters(bilge_radius=0.0),  # sharp chine
        HullParameters(station_count=12, bilge_radius=0.05),  # custom
    ],
    ids=["default", "legacy-5", "sharp-chine", "custom-12"],
)
def test_step_reproducibility(params: HullParameters, tmp_path: Path) -> None:
    h1 = build_hull(params)
    art1 = export_step(h1.body, tmp_path / "hull_1.step")

    h2 = build_hull(params)
    art2 = export_step(h2.body, tmp_path / "hull_2.step")

    assert art1.sha256 == art2.sha256, "STEP reproducibility broken"


def test_stl_reproducibility_default(tmp_path: Path) -> None:
    params = HullParameters()
    h1 = build_hull(params)
    art1 = export_stl(h1.body, tmp_path / "hull_1.stl")

    h2 = build_hull(params)
    art2 = export_stl(h2.body, tmp_path / "hull_2.stl")

    assert art1.sha256 == art2.sha256, "STL reproducibility broken"


def test_brep_reproducibility_default(tmp_path: Path) -> None:
    params = HullParameters()
    h1 = build_hull(params)
    art1 = export_brep(h1.body, tmp_path / "hull_1.brep")

    h2 = build_hull(params)
    art2 = export_brep(h2.body, tmp_path / "hull_2.brep")

    assert art1.sha256 == art2.sha256, "BREP reproducibility broken"
