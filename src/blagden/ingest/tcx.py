"""Read TCX (Training Center Database v2) trackpoints.

Each ``Trackpoint`` gives Time, optional Position, AltitudeMeters, DistanceMeters and
HeartRateBpm/Value. Speed comes from the ActivityExtension ``TPX/Speed`` element when present.
Elements are matched by local name, so any namespace prefix works. Parsing uses defusedxml.
"""

from __future__ import annotations

from pathlib import Path

from defusedxml import ElementTree

from blagden.ingest._xmlutil import local_name, parse_time, to_float
from blagden.ingest.table import EmptyActivityError, RawActivity, RawRecord


def read_tcx(path: str | Path) -> RawActivity:
    """Read every ``Trackpoint`` of a TCX file into raw records.

    Raises
    ------
    EmptyActivityError
        When the file contains no trackpoints.
    """
    root = ElementTree.parse(Path(path)).getroot()
    records: list[RawRecord] = []
    offsets: set[int] = set()
    naive = 0
    for point in root.iter():
        if local_name(point.tag) != "trackpoint":
            continue
        time_utc = None
        hr = lat = lon = alt = dist = speed = None
        for child in point:
            name = local_name(child.tag)
            if name == "time":
                time_utc, offset_s, was_naive = parse_time(child.text)
                naive += was_naive
                if offset_s is not None:
                    offsets.add(offset_s)
            elif name == "position":
                for pos in child:
                    pos_name = local_name(pos.tag)
                    if pos_name == "latitudedegrees":
                        lat = to_float(pos.text)
                    elif pos_name == "longitudedegrees":
                        lon = to_float(pos.text)
            elif name == "altitudemeters":
                alt = to_float(child.text)
            elif name == "distancemeters":
                dist = to_float(child.text)
            elif name == "heartratebpm":
                for value in child:
                    if local_name(value.tag) == "value":
                        hr = to_float(value.text)
            elif name == "extensions":
                for ext in child.iter():
                    if local_name(ext.tag) == "speed" and speed is None:
                        speed = to_float(ext.text)
        records.append(RawRecord(time_utc, hr, lat, lon, alt, speed, dist))
    if not records:
        raise EmptyActivityError(f"{Path(path).name}: no trackpoints found in the TCX file")
    notes = (f"{naive} times without a zone were read as UTC",) if naive else ()
    nonzero = {o for o in offsets if o != 0}
    local = nonzero.pop() if len(nonzero) == 1 else None
    return RawActivity(tuple(records), "tcx", local_utc_offset_s=local, notes=notes)
