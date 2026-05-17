"""Seed / refresh `expected_hashes.toml` on a FreeCAD-equipped host.

Run with:
    uv run python tests/geometry/fixtures/refresh_hashes.py

Prints TOML stanzas to stdout. The maintainer pastes them into
`tests/geometry/fixtures/expected_hashes.toml` and commits, ideally as part
of a release-prep PATCH bump that touches the CHANGELOG with the FreeCAD
version that produced the new baselines.

Importing this module requires FreeCAD on PATH; otherwise it fails with a
clear ImportError.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

try:
    import FreeCAD  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "FreeCAD is not importable on this host. Install FreeCAD 1.1+ and "
        "ensure its Python bindings are on sys.path before running this script."
    ) from exc

from storebro import (
    HullParameters,
    build_hull,
    export_brep,
    export_fcstd,
    export_step,
    export_stl,
)


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _kwargs_key(kwargs: dict[str, object]) -> str:
    return _short_hash(json.dumps(kwargs, sort_keys=True))


def main() -> None:
    fc_version = FreeCAD.Version()
    fc_key = f"{fc_version[0]}_{fc_version[1]}_{fc_version[2]}"

    defaults = HullParameters()
    source_key = _short_hash(repr(defaults))

    hull = build_hull(defaults)
    body = hull.body
    document = hull.document

    print(f"# Seeded against FreeCAD {fc_version[0]}.{fc_version[1]}.{fc_version[2]}")
    print("# Source: HullParameters() defaults (Storebro Royal Cruiser 34, 1972)")
    print()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # STEP
        step_path = tmp_dir / "default.step"
        export_step(body, step_path)
        print(f"[step__{fc_key}__{source_key}__{_kwargs_key({})}]")
        print(f'sha256 = "{_sha256_of(step_path)}"')
        print()

        # STL
        stl_path = tmp_dir / "default.stl"
        export_stl(body, stl_path)
        print(f"[stl__{fc_key}__{source_key}__{_kwargs_key({'tessellation_tolerance': 0.001})}]")
        print(f'sha256 = "{_sha256_of(stl_path)}"')
        print()

        # BREP
        brep_path = tmp_dir / "default.brep"
        export_brep(body, brep_path)
        print(f"[brep__{fc_key}__{source_key}__{_kwargs_key({})}]")
        print(f'sha256 = "{_sha256_of(brep_path)}"')
        print()

        # FCStd
        fcstd_path = tmp_dir / "default.FCStd"
        export_fcstd(document, fcstd_path)
        print(f"[fcstd__{fc_key}__{source_key}__{_kwargs_key({})}]")
        print(f'sha256 = "{_sha256_of(fcstd_path)}"')
        print()


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    main()
