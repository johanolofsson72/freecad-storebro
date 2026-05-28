"""Geometry test: hull construction rollback (spec 006 T009a).

Covers FR-012 + spec.allium `RollbackOnConstructionFailure` — when
`build_hull` raises mid-construction, every document object it added
MUST be removed in reversed order before the exception propagates.
"""

from __future__ import annotations

from typing import Any

import pytest

import storebro.hull as hull_mod
from storebro import HullConstructionError, build_hull

pytestmark = pytest.mark.requires_freecad


_PARTDESIGN_PREFIXES = (
    "PartDesign::",
    "Sketcher::SketchObject",
)


def _count_partdesign_objects(doc: Any) -> int:
    """Count document objects that are PartDesign Body children or sketches."""
    return sum(
        1
        for obj in doc.Objects
        if any(obj.TypeId.startswith(prefix) for prefix in _PARTDESIGN_PREFIXES)
        or obj.TypeId == "PartDesign::Body"
    )


def test_rollback_removes_body_when_loft_fails(
    freecad_doc: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forced failure in _apply_loft_and_mirror leaves zero PartDesign artifacts."""
    objects_before = _count_partdesign_objects(freecad_doc)

    def boom(_body: Any, _sketches: list[Any], _parameters: Any) -> tuple[Any, Any]:
        raise RuntimeError("forced loft failure for rollback test")

    monkeypatch.setattr(hull_mod, "_apply_loft_and_mirror", boom)

    with pytest.raises(HullConstructionError) as exc_info:
        build_hull(document=freecad_doc)
    assert "forced loft failure" in str(exc_info.value.underlying)

    objects_after = _count_partdesign_objects(freecad_doc)
    assert objects_after == objects_before, (
        f"FR-012 violation: rollback left {objects_after - objects_before} orphan "
        f"PartDesign objects after forced failure"
    )


def test_rollback_removes_partial_sketches_when_sketch_fails(
    freecad_doc: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forced failure mid-sketch-loop removes Body + previously-created datums and sketches."""
    objects_before = _count_partdesign_objects(freecad_doc)

    call_count = {"sketches": 0}
    original_sketch = hull_mod._create_station_sketch

    def boom_after_third_sketch(profile: Any, body: Any, datum: Any) -> Any:
        call_count["sketches"] += 1
        if call_count["sketches"] >= 3:
            raise RuntimeError("forced sketch failure for rollback test")
        return original_sketch(profile, body, datum)

    monkeypatch.setattr(hull_mod, "_create_station_sketch", boom_after_third_sketch)

    with pytest.raises(HullConstructionError):
        build_hull(document=freecad_doc)

    objects_after = _count_partdesign_objects(freecad_doc)
    assert objects_after == objects_before, (
        f"FR-012 violation: rollback left {objects_after - objects_before} orphan "
        f"PartDesign objects after partial-sketch failure"
    )


def test_rollback_does_not_remove_other_documents_objects(
    freecad_doc: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-existing objects in the user-supplied document must survive a rollback."""
    pre_existing = freecad_doc.addObject("App::FeaturePython", "UserExistingObject")
    objects_before = len(freecad_doc.Objects)

    def boom(_body: Any, _sketches: list[Any]) -> tuple[Any, Any]:
        raise RuntimeError("forced failure")

    monkeypatch.setattr(hull_mod, "_apply_loft_and_mirror", boom)

    with pytest.raises(HullConstructionError):
        build_hull(document=freecad_doc)

    assert pre_existing.Name in [o.Name for o in freecad_doc.Objects], (
        "FR-012 violation: rollback removed a pre-existing user object"
    )
    assert len(freecad_doc.Objects) == objects_before, (
        "FR-012 violation: document object count changed across rollback"
    )
