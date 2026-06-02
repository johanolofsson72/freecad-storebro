"""Unit tests for the render palette + role resolution (spec 015 T004).

Pure-Python — no FreeCAD required (`not requires_freecad`). Covers contract
invariants 1-3 and 7-8 from specs/015-render-attributes/contracts/render-api.md.
"""

from __future__ import annotations

import pytest

from storebro.render import PALETTE, RenderAttribute, role_for_label

_REQUIRED_ROLES = {
    "hull",
    "superstructure",
    "frame",
    "glass",
    "trim",
    "metal",
    "bulkhead",
    "engine",
    "steel",
    "bronze",
    "DEFAULT",
}


def test_palette_covers_required_roles() -> None:
    """Invariant 1: every documented role (+ DEFAULT) is present."""
    assert set(PALETTE) >= _REQUIRED_ROLES


def test_glass_is_translucent() -> None:
    """Invariant 2: glass alpha < 1.0 (FR-014)."""
    assert PALETTE["glass"].color[3] < 1.0


def test_every_palette_entry_is_valid() -> None:
    """Invariant 3: channels in [0,1], material non-empty."""
    for role, attr in PALETTE.items():
        assert len(attr.color) == 4, role
        for channel in attr.color:
            assert 0.0 <= channel <= 1.0, (role, channel)
        assert attr.material, role


def test_non_glass_roles_are_opaque() -> None:
    for role, attr in PALETTE.items():
        if role != "glass":
            assert attr.color[3] == 1.0, role


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("HullBody", "hull"),
        ("Deck_WindshieldGlass", "glass"),  # most-specific-first beats Deck_Windshield
        ("Deck_Windshield", "frame"),
        ("Deck_Rubrail", "trim"),
        ("Deck_Rubrail_port", "trim"),
        ("Deck_Railings", "metal"),
        ("Deck_Railings_starboard", "metal"),
        ("Deck_BowPulpit", "metal"),
        ("Deck_Cleat_port_0", "metal"),
        ("Deck_Cleats", "metal"),
        ("Deck_Lifelines", "metal"),
        ("Deck_HardtopPillars", "metal"),
        ("Deck_Pillar_port_1", "metal"),
        ("Deck_DeckPlate", "superstructure"),
        ("Deck_CabinTrunk", "superstructure"),
        ("Deck_Hardtop", "superstructure"),
        ("Deck_AnchorLocker", "superstructure"),
        ("Interior_Alternativ3_ForwardCabin", "trim"),
        ("Interior_Alternativ1_Galley", "trim"),
        ("Propulsion_EngineBed", "engine"),
        ("Propulsion_Engine", "engine"),
        ("Propulsion_Engine001", "engine"),  # twin-screw auto-numbering
        ("Propulsion_Shaft", "steel"),
        ("Propulsion_Propeller", "bronze"),
        ("Propulsion_Rudder", "bronze"),
    ],
)
def test_role_for_label_known(label: str, expected: str) -> None:
    """Invariant 7: label → role, most-specific-first."""
    assert role_for_label(label) == expected


@pytest.mark.parametrize("label", ["", "Foo", "Random123", "deck_lowercase", "Box"])
def test_role_for_label_unknown_is_default(label: str) -> None:
    """Invariant 8: unmatched labels → DEFAULT (FR-010)."""
    assert role_for_label(label) == "DEFAULT"


def test_render_attribute_rejects_bad_color() -> None:
    with pytest.raises(ValueError):
        RenderAttribute((1.2, 0.0, 0.0, 1.0), "x")
    with pytest.raises(ValueError):
        RenderAttribute((0.0, 0.0, 0.0), "x")  # type: ignore[arg-type]


def test_render_attribute_rejects_empty_material() -> None:
    with pytest.raises(ValueError):
        RenderAttribute((0.0, 0.0, 0.0, 1.0), "")


def test_apply_render_attributes_disabled_is_noop() -> None:
    """Invariant 4 (pure side): enabled=False returns 0 without touching FreeCAD."""
    from storebro.render import apply_render_attributes

    sentinel = object()  # would explode if the applier tried to use it
    assert apply_render_attributes([sentinel], enabled=False) == 0
