"""freecad-storebro — parametric Storebro motor yacht model for FreeCAD.

Public API:

- :class:`HullParameters` — hull dimensional inputs (frozen dataclass)
- :func:`build_hull` — construct a parametric Storebro hull Body
- :class:`Hull` — return type of :func:`build_hull`
- :class:`HullParameterError` — invalid parameter (pre-FreeCAD)
- :class:`HullConstructionError` — FreeCAD-side construction failure

Example:
    >>> from storebro import build_hull, HullParameters
    >>> # build_hull() requires FreeCAD 1.1+ on this host; see README.md.
"""

from storebro.cli import main
from storebro.deck import (
    AnchorLockerParameters,
    BowPulpitParameters,
    CabinTrunkParameters,
    CabinWindowParameters,
    CleatParameters,
    Deck,
    DeckConstructionError,
    DeckGlazingParameters,
    DeckHardwareParameters,
    DeckParameterError,
    DeckParameters,
    DeckSuperstructureParameters,
    HardtopParameters,
    LifelineParameters,
    PillarParameters,
    RailingParameters,
    RubrailParameters,
    WindshieldGlazingParameters,
    WindshieldParameters,
    build_deck,
)
from storebro.export import (
    ExportArtifact,
    ExportInputError,
    ExportWriteError,
    export_brep,
    export_fcstd,
    export_step,
    export_stl,
)
from storebro.hull import (
    Hull,
    HullConstructionError,
    HullGlazingParameters,
    HullParameterError,
    HullParameters,
    Porthole,
    PortholeParameters,
    build_hull,
)
from storebro.interior import (
    BerthParameters,
    BulkheadParameters,
    FurnitureParameters,
    GalleyParameters,
    HeadParameters,
    Interior,
    InteriorConstructionError,
    InteriorParameterError,
    SalonParameters,
    build_interior,
)

__version__ = "1.0.6"

__all__ = [
    "AnchorLockerParameters",
    "BerthParameters",
    "BowPulpitParameters",
    "BulkheadParameters",
    "CabinTrunkParameters",
    "CabinWindowParameters",
    "CleatParameters",
    "Deck",
    "DeckConstructionError",
    "DeckGlazingParameters",
    "DeckHardwareParameters",
    "DeckParameterError",
    "DeckParameters",
    "DeckSuperstructureParameters",
    "ExportArtifact",
    "ExportInputError",
    "ExportWriteError",
    "FurnitureParameters",
    "GalleyParameters",
    "HardtopParameters",
    "HeadParameters",
    "Hull",
    "HullConstructionError",
    "HullGlazingParameters",
    "HullParameterError",
    "HullParameters",
    "Interior",
    "InteriorConstructionError",
    "InteriorParameterError",
    "LifelineParameters",
    "PillarParameters",
    "Porthole",
    "PortholeParameters",
    "RailingParameters",
    "RubrailParameters",
    "SalonParameters",
    "WindshieldGlazingParameters",
    "WindshieldParameters",
    "__version__",
    "build_deck",
    "build_hull",
    "build_interior",
    "export_brep",
    "export_fcstd",
    "export_step",
    "export_stl",
    "main",
]
