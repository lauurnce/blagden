"""Read GPX 1.0 and 1.1 track points with heart rate from extensions.

Heart rate is found by element name anywhere inside a point's ``extensions``, so the Garmin
TrackPointExtension v1 and v2 (``hr``), the Cluetrust GPXData extension (``hr``) and the plain
``heartrate`` or ``heart_rate`` elements some apps write are all read. Speed is read from an
extension ``speed`` element when present. GPX has no distance field; cleaning computes it from
positions. Parsing uses defusedxml because run files come from users.
"""

from __future__ import annotations

from pathlib import Path

from defusedxml import ElementTree

from blagden.ingest._xmlutil import local_name, parse_time, to_float
from blagden.ingest.table import EmptyActivityError, RawActivity, RawRecord

HR_NAMES = frozenset({"hr", "heartrate", "heart_rate"})
SPEED_NAMES = frozenset({"speed"})


def read_gpx(path: str | Path) -> RawActivity:
    """Read every ``trkpt`` of a GPX file into raw records.

    Raises
    ------
    EmptyActivityError
        When the file contains no track points.
    """
    root = ElementTree.parse(Path(path)).getroot()
    records: list[RawRecord] = []
    offsets: set[int] = set()
    naive = 0
    for point in root.iter():
        if local_name(point.tag) != "trkpt":
            continue
        time_utc = None
        alt = hr = speed = None
        for child in point:
            name = local_name(child.tag)
            if name == "time":
                time_utc, offset_s, was_naive = parse_time(child.text)
                naive += was_naive
                if offset_s is not None:
                    offsets.add(offset_s)
            elif name == "ele":
                alt = to_float(child.text)
            elif name == "extensions":
                for ext in child.iter():
                    ext_name = local_name(ext.tag)
                    if ext_name in HR_NAMES and hr is None:
                        hr = to_float(ext.text)
                    elif ext_name in SPEED_NAMES and speed is None:
                        speed = to_float(ext.text)
        records.append(
            RawRecord(
                time_utc=time_utc,
                hr_bpm=hr,
                lat_deg=to_float(point.get("lat")),
                lon_deg=to_float(point.get("lon")),
                alt_m=alt,
                speed_mps=speed,
            )
        )
    if not records:
        raise EmptyActivityError(f"{Path(path).name}: no track points found in the GPX file")
    notes = (f"{naive} times without a zone were read as UTC",) if naive else ()
    nonzero = {o for o in offsets if o != 0}
    local = nonzero.pop() if len(nonzero) == 1 else None
    return RawActivity(tuple(records), "gpx", local_utc_offset_s=local, notes=notes)
