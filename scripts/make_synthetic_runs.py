"""Write small synthetic GPX and TCX runs with heart rate into tests/fixtures.

The route is a made-up 400 m loop centred on 0 N, 0 E, in open ocean, so it describes no real
place. Heart rate follows a fixed warm-up ramp, a steady state, two surges and a cool-down, with
seeded noise, so the files are identical on every run. One sample every 5 seconds for 30 minutes.
"""

from __future__ import annotations

import math
import random
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

OUT_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
START = datetime(2026, 1, 4, 21, 0, 0, tzinfo=UTC)
STEP_S = 5
DURATION_MIN = 30
LOOP_RADIUS_M = 400.0 / (2.0 * math.pi)
SPEED_MPS = 2.8
M_PER_DEG = 111_320.0
SEED = 20260104


def heart_rate(t_min: float, rng: random.Random) -> int:
    if t_min < 5.0:
        base = 95.0 + 10.0 * t_min
    elif t_min < 25.0:
        base = 148.0 + 0.6 * (t_min - 5.0)
    else:
        base = 160.0 - 8.0 * (t_min - 25.0)
    if 12.0 <= t_min < 13.5 or 19.0 <= t_min < 20.5:
        base += 12.0
    return int(round(base + rng.gauss(0.0, 2.0)))


def samples() -> list[tuple[datetime, float, float, float, int, float]]:
    rng = random.Random(SEED)
    rows = []
    for i in range(DURATION_MIN * 60 // STEP_S + 1):
        t_s = i * STEP_S
        dist_m = SPEED_MPS * t_s
        angle = dist_m / LOOP_RADIUS_M
        lat = (LOOP_RADIUS_M * math.sin(angle)) / M_PER_DEG
        lon = (LOOP_RADIUS_M * (1.0 - math.cos(angle))) / M_PER_DEG
        rows.append(
            (START + timedelta(seconds=t_s), lat, lon, 5.0, heart_rate(t_s / 60.0, rng), dist_m)
        )
    return rows


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def write_gpx(
    rows: Sequence[tuple[datetime, float, float, float, int | None, float]], path: Path
) -> None:
    def ext(hr: int | None) -> str:
        if hr is None:
            return ""
        return (
            f"<extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>{hr}</gpxtpx:hr>"
            "</gpxtpx:TrackPointExtension></extensions>"
        )

    pts = "\n".join(
        f'      <trkpt lat="{lat:.7f}" lon="{lon:.7f}"><ele>{ele:.1f}</ele><time>{iso(t)}</time>'
        f"{ext(hr)}</trkpt>"
        for t, lat, lon, ele, hr, _ in rows
    )
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="blagden synthetic fixtures"\n'
        '     xmlns="http://www.topografix.com/GPX/1/1"\n'
        '     xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">\n'
        f"  <trk><name>{escape('Synthetic loop')}</name><type>running</type><trkseg>\n"
        f"{pts}\n"
        "  </trkseg></trk>\n</gpx>\n",
        encoding="utf-8",
    )


def write_tcx(rows: list[tuple[datetime, float, float, float, int, float]], path: Path) -> None:
    pts = "\n".join(
        f"          <Trackpoint><Time>{iso(t)}</Time><Position><LatitudeDegrees>{lat:.7f}"
        f"</LatitudeDegrees><LongitudeDegrees>{lon:.7f}</LongitudeDegrees></Position>"
        f"<AltitudeMeters>{ele:.1f}</AltitudeMeters><DistanceMeters>{dist:.1f}</DistanceMeters>"
        f"<HeartRateBpm><Value>{hr}</Value></HeartRateBpm></Trackpoint>"
        for t, lat, lon, ele, hr, dist in rows
    )
    total_s = (rows[-1][0] - rows[0][0]).total_seconds()
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">\n'
        '  <Activities><Activity Sport="Running"><Id>' + iso(rows[0][0]) + "</Id>\n"
        f'    <Lap StartTime="{iso(rows[0][0])}"><TotalTimeSeconds>{total_s:.0f}</TotalTimeSeconds>'
        f"<DistanceMeters>{rows[-1][5]:.1f}</DistanceMeters><Calories>0</Calories>"
        "<Intensity>Active</Intensity><TriggerMethod>Manual</TriggerMethod>\n"
        "        <Track>\n"
        f"{pts}\n"
        "        </Track>\n    </Lap>\n  </Activity></Activities>\n</TrainingCenterDatabase>\n",
        encoding="utf-8",
    )


def edge_rows() -> list[tuple[datetime, float, float, float, int | None, float]]:
    """Return a 20-minute run with the cases the cleaner must handle.

    A gap from minute 8 to minute 11, a 250 bpm spike at 5:00 (outside 30 to 230),
    a duplicate timestamp at 3:00 with a different heart rate, two points out of
    order around 12:00, and a point without heart rate at 15:00.
    """
    rows: list[tuple[datetime, float, float, float, int | None, float]] = []
    for i in range(20 * 6 + 1):
        t_s = i * 10
        if 8 * 60 < t_s < 11 * 60:
            continue
        hr: int | None = 120 + i % 30
        if t_s == 5 * 60:
            hr = 250
        if t_s == 15 * 60:
            hr = None
        dist = SPEED_MPS * t_s
        rows.append((START + timedelta(seconds=t_s), dist / M_PER_DEG, 0.0, 5.0, hr, dist))
        if t_s == 3 * 60:
            rows.append((START + timedelta(seconds=t_s), dist / M_PER_DEG, 0.0, 5.0, 99, dist))
    a = next(k for k, r in enumerate(rows) if r[0] == START + timedelta(minutes=12))
    rows[a], rows[a + 1] = rows[a + 1], rows[a]
    return rows


def write_fit_loop(
    rows: list[tuple[datetime, float, float, float, int, float]], path: Path
) -> None:
    """Write the loop as FIT with the test-only writer (our own code; no Garmin SDK)."""
    sys.path.insert(0, str(OUT_DIR.parent.parent))
    from tests.ingest.fitwriter import write_fit

    write_fit(path, [(t, hr, dist, lat) for t, lat, _lon, _alt, hr, dist in rows])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = samples()
    write_gpx(rows, OUT_DIR / "synthetic_loop.gpx")
    write_tcx(rows, OUT_DIR / "synthetic_loop.tcx")
    write_fit_loop(rows, OUT_DIR / "synthetic_loop.fit")
    write_gpx(edge_rows(), OUT_DIR / "synthetic_edge.gpx")
    print(f"wrote {len(rows)} samples to {OUT_DIR}")


if __name__ == "__main__":
    main()
