"""Read any supported activity file: sniff the format, parse, clean.

The content decides the format: FIT files carry ``.FIT`` at bytes 8 to 11, GPX files open a
``gpx`` element and TCX files a ``TrainingCenterDatabase`` element. The extension is used only
when the content is not recognisable. A file whose extension disagrees with its content is read
by its content and the report says so.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from pathlib import Path

import numpy as np

from blagden.ingest.clean import clean
from blagden.ingest.fit import read_fit
from blagden.ingest.gpx import read_gpx
from blagden.ingest.table import (
    ActivityTable,
    CleaningReport,
    NoHeartRateError,
    RawActivity,
    SourceFormat,
    UnsupportedFormatError,
)
from blagden.ingest.tcx import read_tcx

READERS: dict[SourceFormat, Callable[[str | Path], RawActivity]] = {
    "fit": read_fit,
    "gpx": read_gpx,
    "tcx": read_tcx,
}
_EXTENSIONS: dict[str, SourceFormat] = {".fit": "fit", ".gpx": "gpx", ".tcx": "tcx"}


def sniff_format(path: str | Path) -> SourceFormat | None:
    """Return the format the file content shows, or None when it is not recognisable."""
    with Path(path).open("rb") as fh:
        head = fh.read(4096)
    if len(head) >= 12 and head[8:12] == b".FIT":
        return "fit"
    text = head.decode("utf-8", errors="ignore").lower()
    if "<trainingcenterdatabase" in text:
        return "tcx"
    if "<gpx" in text:
        return "gpx"
    return None


def detect_format(path: str | Path) -> tuple[SourceFormat, str | None]:
    """Choose the format from content, falling back to the extension.

    Returns the format and a note when the extension disagreed with the content.
    """
    by_ext = _EXTENSIONS.get(Path(path).suffix.lower())
    by_content = sniff_format(path)
    if by_content is not None:
        note = None
        if by_ext is not None and by_ext != by_content:
            note = f"extension says {by_ext} but content is {by_content}; read as {by_content}"
        return by_content, note
    if by_ext is not None:
        return by_ext, None
    raise UnsupportedFormatError(
        f"{Path(path).name}: not a FIT, GPX or TCX activity (unknown extension and content)"
    )


def read_activity(
    path: str | Path, *, require_hr: bool = True
) -> tuple[ActivityTable, CleaningReport]:
    """Read, clean and return one activity with its cleaning report.

    Raises
    ------
    UnsupportedFormatError
        When the file is not a FIT, GPX or TCX activity.
    NoHeartRateError
        When ``require_hr`` is True and no valid heart rate remains after cleaning.
    """
    fmt, note = detect_format(path)
    raw = READERS[fmt](path)
    table, report = clean(raw)
    if note is not None:
        report = dataclasses.replace(report, notes=(*report.notes, note))
    if require_hr and not np.isfinite(table.hr_bpm).any():
        removed = report.values_removed.get("hr_out_of_range", 0)
        why = (
            f"all {removed} heart-rate values were outside 30 to 230 bpm"
            if removed
            else "the file has no heart-rate data"
        )
        raise NoHeartRateError(
            f"{Path(path).name}: no valid heart rate ({why}). Core temperature is estimated "
            "from heart rate, so record the run with a heart-rate sensor."
        )
    return table, report
