"""Unit tests for custom-YAML error paths (T040, partial of SC-007's 10+ cases)."""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import InteriorParameterError
from storebro.interior import _load_layout, _validate_layout_schema


def _write_yaml(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content)
    return path


def test_missing_schema_version_via_custom_yaml(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        "bad.yaml",
        """
layout_name: X
source: y
compartments:
  - name: A
    type: forward_cabin
    position: { x: 0, y: 0, z: 0 }
    dimensions: { length: 1, width: 1, height: 1 }
""",
    )
    source, raw = _load_layout(str(p))
    with pytest.raises(InteriorParameterError) as exc:
        _validate_layout_schema(raw, source)
    assert exc.value.field == "schema_version"


def test_unknown_compartment_type_via_custom_yaml(tmp_path: Path) -> None:
    # spec 025: engine_room is now a valid type; use a genuinely unknown one.
    p = _write_yaml(
        tmp_path,
        "bad.yaml",
        """
schema_version: 1
layout_name: X
source: y
compartments:
  - name: A
    type: submarine_bay
    position: { x: 0, y: 0, z: 0 }
    dimensions: { length: 1, width: 1, height: 1 }
""",
    )
    source, raw = _load_layout(str(p))
    with pytest.raises(InteriorParameterError) as exc:
        _validate_layout_schema(raw, source)
    assert exc.value.field == "type"


def test_position_y_nonzero_accepted_via_custom_yaml(tmp_path: Path) -> None:
    # spec 025: asymmetric layouts — y!=0 parses fine (the transverse bound is
    # enforced later against the hull half-beam).
    p = _write_yaml(
        tmp_path,
        "ok.yaml",
        """
schema_version: 1
layout_name: X
source: y
compartments:
  - name: A
    type: forward_cabin
    position: { x: 0, y: 0.5, z: 0 }
    dimensions: { length: 1, width: 1, height: 1 }
""",
    )
    source, raw = _load_layout(str(p))
    spec = _validate_layout_schema(raw, source)
    assert spec.compartments[0].position.y == 0.5


def test_zero_dim_via_custom_yaml(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        "bad.yaml",
        """
schema_version: 1
layout_name: X
source: y
compartments:
  - name: A
    type: forward_cabin
    position: { x: 0, y: 0, z: 0 }
    dimensions: { length: 0, width: 1, height: 1 }
""",
    )
    source, raw = _load_layout(str(p))
    with pytest.raises(InteriorParameterError) as exc:
        _validate_layout_schema(raw, source)
    assert exc.value.field == "dimensions.length"


def test_duplicate_compartment_names_via_custom_yaml(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        "bad.yaml",
        """
schema_version: 1
layout_name: X
source: y
compartments:
  - name: Same
    type: forward_cabin
    position: { x: 0, y: 0, z: 0 }
    dimensions: { length: 1, width: 1, height: 1 }
  - name: Same
    type: galley
    position: { x: 2, y: 0, z: 0 }
    dimensions: { length: 1, width: 1, height: 1 }
""",
    )
    source, raw = _load_layout(str(p))
    with pytest.raises(InteriorParameterError) as exc:
        _validate_layout_schema(raw, source)
    assert exc.value.compartment_name == "Same"
