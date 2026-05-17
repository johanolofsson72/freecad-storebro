"""Geometry test: FCStd scrubbed metadata (T028).

Covers FR-003, FR-004, FR-020. Verifies the .FCStd Document.xml does not leak
timestamps, usernames, or hostnames.
"""

from __future__ import annotations

import getpass
import socket
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from storebro import build_hull, export_fcstd


def _read_document_xml(path: Path) -> bytes:
    with zipfile.ZipFile(path, "r") as zf:
        return zf.read("Document.xml")


def test_document_xml_has_no_user_or_hostname_leak(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "metadata.FCStd"
    export_fcstd(hull.document, out)

    xml_bytes = _read_document_xml(out)
    xml_text = xml_bytes.decode("utf-8")

    user = getpass.getuser()
    host = socket.gethostname()
    assert user not in xml_text, "FR-004: local user leaked into Document.xml"
    assert host not in xml_text, "FR-004: local hostname leaked into Document.xml"


def test_document_xml_scrubbed_metadata_fields(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "scrub.FCStd"
    export_fcstd(hull.document, out)

    xml_bytes = _read_document_xml(out)
    root = ET.fromstring(xml_bytes)

    # CreatedBy / LastModifiedBy → "freecad-storebro"
    for tag in ("CreatedBy", "LastModifiedBy"):
        for elem in root.iter(tag):
            assert elem.text == "freecad-storebro", (
                f"FR-020: {tag} not scrubbed (got: {elem.text!r})"
            )

    # CreationDate / LastModifiedDate → fixed epoch
    for tag in ("CreationDate", "LastModifiedDate"):
        for elem in root.iter(tag):
            assert elem.text == "1980-01-01T00:00:00Z", (
                f"FR-020: {tag} not scrubbed (got: {elem.text!r})"
            )
