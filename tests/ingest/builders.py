"""Small hand-built activity files for ingest tests. All positions sit near 0 N, 0 E."""

from __future__ import annotations

from pathlib import Path

GPX_HEAD = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1"\n'
    '  xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1"\n'
    '  xmlns:tpx2="http://www.garmin.com/xmlschemas/TrackPointExtension/v2"\n'
    '  xmlns:gpxdata="http://www.cluetrust.com/XML/GPXDATA/1/0">\n'
    "<trk><trkseg>\n"
)
GPX_TAIL = "</trkseg></trk></gpx>\n"


def gpx_point(time: str | None, hr_xml: str = "", lat: float = 0.0, lon: float = 0.0) -> str:
    time_xml = f"<time>{time}</time>" if time is not None else ""
    ext = f"<extensions>{hr_xml}</extensions>" if hr_xml else ""
    return f'<trkpt lat="{lat}" lon="{lon}"><ele>5.0</ele>{time_xml}{ext}</trkpt>\n'


def tpx_hr(hr: int) -> str:
    return f"<gpxtpx:TrackPointExtension><gpxtpx:hr>{hr}</gpxtpx:hr></gpxtpx:TrackPointExtension>"


def write_gpx(path: Path, points: list[str]) -> Path:
    path.write_text(GPX_HEAD + "".join(points) + GPX_TAIL, encoding="utf-8")
    return path


TCX_HEAD = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"\n'
    '  xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2">\n'
    '<Activities><Activity Sport="Running"><Id>2026-01-04T21:00:00Z</Id>\n'
    '<Lap StartTime="2026-01-04T21:00:00Z"><Track>\n'
)
TCX_TAIL = "</Track></Lap></Activity></Activities></TrainingCenterDatabase>\n"


def tcx_point(
    time: str,
    hr: int | None = None,
    dist: float | None = None,
    speed: float | None = None,
    position: bool = True,
) -> str:
    parts = [f"<Time>{time}</Time>"]
    if position:
        parts.append(
            "<Position><LatitudeDegrees>0.001</LatitudeDegrees>"
            "<LongitudeDegrees>0.001</LongitudeDegrees></Position>"
        )
    parts.append("<AltitudeMeters>5.0</AltitudeMeters>")
    if dist is not None:
        parts.append(f"<DistanceMeters>{dist}</DistanceMeters>")
    if hr is not None:
        parts.append(f"<HeartRateBpm><Value>{hr}</Value></HeartRateBpm>")
    if speed is not None:
        parts.append(f"<Extensions><ns3:TPX><ns3:Speed>{speed}</ns3:Speed></ns3:TPX></Extensions>")
    return "<Trackpoint>" + "".join(parts) + "</Trackpoint>\n"


def write_tcx(path: Path, points: list[str]) -> Path:
    path.write_text(TCX_HEAD + "".join(points) + TCX_TAIL, encoding="utf-8")
    return path
