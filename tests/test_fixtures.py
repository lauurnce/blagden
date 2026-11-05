"""Checks on the synthetic fixtures and the optional real .fit file.

These verify the files only. Parsing into Blagden's sample table arrives with the ingest module.
"""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
RAW = ROOT / "data" / "raw"
GPX_NS = {
    "g": "http://www.topografix.com/GPX/1/1",
    "x": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1",
}
TCX_NS = {"t": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}


def test_gpx_fixture_has_heart_rate_at_every_point() -> None:
    root = ET.parse(FIXTURES / "synthetic_loop.gpx").getroot()
    points = root.findall(".//g:trkpt", GPX_NS)
    assert len(points) == 361
    hrs = [int(p.findtext(".//x:hr", namespaces=GPX_NS) or 0) for p in points]
    assert all(60 <= hr <= 200 for hr in hrs)


def test_tcx_fixture_has_heart_rate_at_every_point() -> None:
    root = ET.parse(FIXTURES / "synthetic_loop.tcx").getroot()
    points = root.findall(".//t:Trackpoint", TCX_NS)
    assert len(points) == 361
    hrs = [int(p.findtext("t:HeartRateBpm/t:Value", namespaces=TCX_NS) or 0) for p in points]
    assert all(60 <= hr <= 200 for hr in hrs)


def test_fixture_route_is_not_a_real_place() -> None:
    root = ET.parse(FIXTURES / "synthetic_loop.gpx").getroot()
    for p in root.findall(".//g:trkpt", GPX_NS):
        assert abs(float(p.attrib["lat"])) < 0.01
        assert abs(float(p.attrib["lon"])) < 0.01


def _real_fit_files() -> list[Path]:
    return sorted(RAW.glob("*.fit")) if RAW.is_dir() else []


@pytest.mark.skipif(
    not _real_fit_files(), reason="no .fit file in data/raw (local only, never committed)"
)
def test_real_fit_file_has_fit_header() -> None:
    for path in _real_fit_files():
        head = path.read_bytes()[:14]
        assert head[0] in (12, 14), f"{path.name}: unexpected FIT header size"
        assert head[8:12] == b".FIT", f"{path.name}: missing .FIT signature"
