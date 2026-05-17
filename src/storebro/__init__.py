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
    HullParameterError,
    HullParameters,
    build_hull,
)

__version__ = "0.2.0"

__all__ = [
    "ExportArtifact",
    "ExportInputError",
    "ExportWriteError",
    "Hull",
    "HullConstructionError",
    "HullParameterError",
    "HullParameters",
    "__version__",
    "build_hull",
    "export_brep",
    "export_fcstd",
    "export_step",
    "export_stl",
]
