"""Unit tests for layout loader + schema validation (T020).

Covers FR-002, FR-020, FR-021, SC-004, SC-007.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import InteriorParameterError
from storebro.interior import _load_layout, _validate_layout_schema


class TestCanonicalLayoutLoading:
    @pytest.mark.parametrize(
        "name",
        ["Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"],
    )
    def test_canonical_name_loads_fixture(self, name: str) -> None:
        source, raw = _load_layout(name)
        assert source == name
        assert raw["schema_version"] == 1
        assert raw["layout_name"] == name
        assert isinstance(raw["compartments"], list)

    def test_unknown_name_raises(self) -> None:
        with pytest.raises(InteriorParameterError) as exc_info:
            _load_layout("Alternativ99")
        assert exc_info.value.source == "Alternativ99"

    def test_nonexistent_path_raises(self) -> None:
        with pytest.raises(InteriorParameterError) as exc_info:
            _load_layout("/tmp/no_such_layout_xyz123.yaml")
        assert "no_such_layout_xyz123.yaml" in exc_info.value.source

    def test_loader_is_deterministic_for_canonical_names(self) -> None:
        # SC-004 — same canonical name → same parsed dict
        _, raw1 = _load_layout("Alternativ3")
        _, raw2 = _load_layout("Alternativ3")
        assert raw1 == raw2


class TestSchemaValidation:
    def _valid_minimum(self) -> dict:
        return {
            "schema_version": 1,
            "layout_name": "TestLayout",
            "source": "test-only",
            "compartments": [
                {
                    "name": "C1",
                    "type": "forward_cabin",
                    "position": {"x": 0.5, "y": 0, "z": 0.6},
                    "dimensions": {"length": 2.0, "width": 1.8, "height": 1.2},
                }
            ],
        }

    def test_minimum_valid_layout(self) -> None:
        spec = _validate_layout_schema(self._valid_minimum(), "test")
        assert spec.schema_version == 1
        assert spec.layout_name == "TestLayout"
        assert len(spec.compartments) == 1
        assert spec.compartments[0].name == "C1"

    def test_missing_schema_version_raises(self) -> None:
        raw = self._valid_minimum()
        del raw["schema_version"]
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.field == "schema_version"

    def test_wrong_schema_version_raises(self) -> None:
        raw = self._valid_minimum()
        raw["schema_version"] = 99
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.field == "schema_version"

    def test_missing_layout_name_raises(self) -> None:
        raw = self._valid_minimum()
        del raw["layout_name"]
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.field == "layout_name"

    def test_empty_compartments_raises(self) -> None:
        raw = self._valid_minimum()
        raw["compartments"] = []
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.field == "compartments"

    def test_unknown_compartment_type_raises(self) -> None:
        raw = self._valid_minimum()
        raw["compartments"][0]["type"] = "engine_room"
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.compartment_name == "C1"
        assert exc_info.value.field == "type"

    def test_position_y_not_zero_raises(self) -> None:
        raw = self._valid_minimum()
        raw["compartments"][0]["position"]["y"] = 0.5
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.field == "position.y"

    def test_duplicate_compartment_name_raises(self) -> None:
        raw = self._valid_minimum()
        raw["compartments"].append(dict(raw["compartments"][0]))
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.compartment_name == "C1"

    def test_zero_dimension_raises(self) -> None:
        raw = self._valid_minimum()
        raw["compartments"][0]["dimensions"]["length"] = 0
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.field == "dimensions.length"

    def test_negative_dimension_raises(self) -> None:
        raw = self._valid_minimum()
        raw["compartments"][0]["dimensions"]["width"] = -1
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.field == "dimensions.width"

    def test_missing_position_axis_raises(self) -> None:
        raw = self._valid_minimum()
        del raw["compartments"][0]["position"]["z"]
        with pytest.raises(InteriorParameterError) as exc_info:
            _validate_layout_schema(raw, "test")
        assert exc_info.value.field == "position.z"


class TestCustomYAMLPath:
    def test_load_custom_yaml(self, tmp_path: Path) -> None:
        yaml_text = """
schema_version: 1
layout_name: MyTestLayout
source: hand-crafted
compartments:
  - name: MyCabin
    type: forward_cabin
    position: { x: 0.5, y: 0, z: 0.6 }
    dimensions: { length: 2.0, width: 1.8, height: 1.2 }
"""
        path = tmp_path / "my_layout.yaml"
        path.write_text(yaml_text)

        source, raw = _load_layout(str(path))
        assert source == str(path.resolve())
        assert raw["layout_name"] == "MyTestLayout"

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text("schema_version: 1\n  bad indent: stuff:\n no")
        with pytest.raises(InteriorParameterError) as exc_info:
            _load_layout(str(path))
        assert "YAML" in exc_info.value.reason or "parse" in exc_info.value.reason.lower()
