"""Minimal FIT writer for tests: file_id, record and activity messages only.

It follows the published FIT protocol (header, definition and data messages, CRC-16). The tests
read its output with fitdecode set to raise on any CRC error, so a mistake here fails loudly.
Coordinates in tests stay near 0 N, 0 E.
"""

from __future__ import annotations

import struct
from datetime import UTC, datetime
from pathlib import Path

FIT_EPOCH = datetime(1989, 12, 31, tzinfo=UTC)
_CRC_TABLE = (
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
)  # fmt: skip

# (field number, size in bytes, base type, struct code)
_RECORD_FIELDS = (
    (253, 4, 0x86, "I"),  # timestamp, uint32 s
    (0, 4, 0x85, "i"),  # position_lat, sint32 semicircles
    (1, 4, 0x85, "i"),  # position_long
    (2, 2, 0x84, "H"),  # altitude, uint16, scale 5 offset 500
    (3, 1, 0x02, "B"),  # heart_rate, uint8
    (5, 4, 0x86, "I"),  # distance, uint32, scale 100
    (6, 2, 0x84, "H"),  # speed, uint16, scale 1000
)
_INVALID = {"I": 0xFFFFFFFF, "i": 0x7FFFFFFF, "H": 0xFFFF, "B": 0xFF}


def _crc(data: bytes, crc: int = 0) -> int:
    for byte in data:
        tmp = _CRC_TABLE[crc & 0xF]
        crc = ((crc >> 4) & 0x0FFF) ^ tmp ^ _CRC_TABLE[byte & 0xF]
        tmp = _CRC_TABLE[crc & 0xF]
        crc = ((crc >> 4) & 0x0FFF) ^ tmp ^ _CRC_TABLE[(byte >> 4) & 0xF]
    return crc


def _definition(
    local: int, global_num: int, fields: tuple[tuple[int, int, int, str], ...]
) -> bytes:
    out = struct.pack("<BBBHB", 0x40 | local, 0, 0, global_num, len(fields))
    return out + b"".join(struct.pack("<BBB", n, s, t) for n, s, t, _ in fields)


def _fit_time(t: datetime) -> int:
    return int((t - FIT_EPOCH).total_seconds())


def write_fit(
    path: Path,
    rows: list[tuple[datetime, int | None, float | None, float | None]],
    *,
    local_offset_s: int | None = None,
) -> Path:
    """Write rows of (time UTC, heart rate or None, distance m or None, lat deg or None)."""
    body = bytearray()
    body += _definition(0, 0, ((0, 1, 0x00, "B"),))  # file_id.type
    body += struct.pack("<BB", 0, 4)  # activity file
    body += _definition(1, 20, _RECORD_FIELDS)
    for t, hr, dist, lat in rows:
        semis = int(round(lat * 2**31 / 180.0)) if lat is not None else _INVALID["i"]
        values = (
            _fit_time(t),
            semis,
            semis,
            int(round((5.0 + 500.0) * 5)),
            hr if hr is not None else _INVALID["B"],
            int(round(dist * 100)) if dist is not None else _INVALID["I"],
            2800,
        )
        body += struct.pack("<B", 1)
        body += b"".join(
            struct.pack("<" + f[3], v) for f, v in zip(_RECORD_FIELDS, values, strict=True)
        )
    if local_offset_s is not None:
        last = rows[-1][0]
        body += _definition(2, 34, ((253, 4, 0x86, "I"), (5, 4, 0x86, "I")))
        body += struct.pack("<BII", 2, _fit_time(last), _fit_time(last) + local_offset_s)
    header = struct.pack("<BBHI4s", 14, 0x20, 2132, len(body), b".FIT")
    header += struct.pack("<H", _crc(header))
    data = header + bytes(body)
    path.write_bytes(data + struct.pack("<H", _crc(data)))
    return path
