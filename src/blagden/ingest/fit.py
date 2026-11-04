"""Read FIT activity files with fitdecode (MIT licence, D-013).

Only ``record`` messages become rows. fitdecode applies the profile's scale and offset, so speed
is in m/s, altitude and distance in metres, and timestamps are timezone-aware UTC. Positions
arrive in semicircles and are converted with degrees = semicircles x 180 / 2^31
(docs/SCIENCE.md section 8). The ``activity`` message's ``local_timestamp`` gives the device's
UTC offset when present.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import fitdecode

from blagden.ingest.table import EmptyActivityError, IngestError, RawActivity, RawRecord

SEMICIRCLE_TO_DEG = 180.0 / 2**31


def _num(message: Any, *names: str) -> float | None:
    for name in names:
        if message.has_field(name):
            value = message.get_value(name, fallback=None)
            if isinstance(value, int | float):
                return float(value)
    return None


def _deg(message: Any, name: str) -> float | None:
    value = _num(message, name)
    return value * SEMICIRCLE_TO_DEG if value is not None else None


def read_fit(path: str | Path) -> RawActivity:
    """Read every ``record`` message of a FIT file into raw records.

    Raises
    ------
    IngestError
        When the file is not a readable FIT file.
    EmptyActivityError
        When it has no record messages.
    """
    records: list[RawRecord] = []
    local_offset: int | None = None
    try:
        with fitdecode.FitReader(
            str(path),
            check_crc=fitdecode.CrcCheck.RAISE,
            error_handling=fitdecode.ErrorHandling.RAISE,
        ) as reader:
            for frame in reader:
                if not isinstance(frame, fitdecode.FitDataMessage):
                    continue
                if frame.name == "record":
                    stamp = frame.get_value("timestamp", fallback=None)
                    records.append(
                        RawRecord(
                            time_utc=stamp if isinstance(stamp, datetime) else None,
                            hr_bpm=_num(frame, "heart_rate"),
                            lat_deg=_deg(frame, "position_lat"),
                            lon_deg=_deg(frame, "position_long"),
                            alt_m=_num(frame, "enhanced_altitude", "altitude"),
                            speed_mps=_num(frame, "enhanced_speed", "speed"),
                            distance_m=_num(frame, "distance"),
                        )
                    )
                elif frame.name == "activity" and local_offset is None:
                    utc = frame.get_value("timestamp", fallback=None)
                    local = frame.get_value("local_timestamp", fallback=None)
                    if isinstance(utc, datetime) and isinstance(local, datetime):
                        local_offset = int(round((local - utc).total_seconds()))
    except fitdecode.FitError as exc:
        raise IngestError(f"{Path(path).name}: not a readable FIT file ({exc})") from exc
    if not records:
        raise EmptyActivityError(f"{Path(path).name}: no record messages found in the FIT file")
    return RawActivity(tuple(records), "fit", local_utc_offset_s=local_offset)
