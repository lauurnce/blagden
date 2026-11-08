"""Charts: core temperature with heart rate, and WBGT across the race window.

Each chart is saved as PNG and SVG. Files are deterministic for the same input
(no timestamps in the metadata, fixed SVG ids), so reports can be compared.
Training insight, not medical advice.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from numpy.typing import ArrayLike  # noqa: E402

from blagden.physio.ectemp import CoreTempEstimate  # noqa: E402
from blagden.physio.summary import LIMITATION_NOTE, REPORT_THRESHOLD_C  # noqa: E402
from blagden.weather.openmeteo import ATTRIBUTION  # noqa: E402
from blagden.weather.race_morning import RaceMorning  # noqa: E402
from blagden.weather.risk import WBGT_MODEL_ERROR_C  # noqa: E402

plt.rcParams["svg.hashsalt"] = "blagden"

FLAG_BANDS = (
    (-50.0, 10.0, "white", "#f4f4f4"),
    (10.0, 18.0, "green", "#d9efd5"),
    (18.0, 23.0, "yellow", "#fbf0bf"),
    (23.0, 28.0, "red", "#f6c9c4"),
    (28.0, 60.0, "black", "#d4d4d4"),
)
"""Race flag bands, C (1996 ACSM flags, SCIENCE.md section 5) and their shading."""

SENSITIVITY_LINE_C = 39.0
"""Above this the heart-rate method detects fewer than half of readings (de Korte 2022)."""


@dataclass(frozen=True)
class ChartFiles:
    """Paths of one chart in both formats."""

    png: Path
    svg: Path


def _datenum(t: datetime) -> float:
    """Matplotlib date number: days since 1970-01-01 UTC (the default epoch)."""
    return t.timestamp() / 86400.0


def _save(fig: Figure, out_dir: Path, stem: str) -> ChartFiles:
    out_dir.mkdir(parents=True, exist_ok=True)
    png, svg = out_dir / f"{stem}.png", out_dir / f"{stem}.svg"
    fig.savefig(png, dpi=150, metadata={"Software": None})
    fig.savefig(svg, metadata={"Date": None, "Creator": None})
    plt.close(fig)
    return ChartFiles(png, svg)


def _caption(fig: Figure, text: str) -> None:
    fig.text(0.01, 0.01, textwrap.fill(text, 130), fontsize=7, va="bottom", ha="left")


def core_temp_chart(
    hr_bpm_per_min: ArrayLike,
    estimate: CoreTempEstimate,
    out_dir: Path,
    stem: str = "core_temperature",
    title: str = "Estimated core temperature",
) -> ChartFiles:
    """Core temperature and heart rate per minute; the limitation note is the caption."""
    hr = np.asarray(hr_bpm_per_min, dtype=np.float64)
    minutes = np.arange(1, len(estimate) + 1)
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.subplots_adjust(bottom=0.24, top=0.9, right=0.88)
    ax.plot(minutes, estimate.tc_c, color="#b2182b", lw=2, label="estimated core temperature")
    ax.axhline(REPORT_THRESHOLD_C, color="#b2182b", ls=":", lw=1, label="38.5 C summary threshold")
    ax.axhline(SENSITIVITY_LINE_C, color="#555555", ls="--", lw=1)
    ax.text(
        minutes[0],
        SENSITIVITY_LINE_C,
        " 39.0 C: method less sensitive above",
        fontsize=7,
        va="bottom",
    )
    ax.set_xlabel("minutes from start")
    ax.set_ylabel("estimated core temperature (C)")
    ax.set_ylim(
        min(36.5, float(np.min(estimate.tc_c)) - 0.2), max(39.5, float(np.max(estimate.tc_c)) + 0.2)
    )
    ax2 = ax.twinx()
    ax2.plot(minutes, hr, color="#2166ac", lw=1, alpha=0.7, label="heart rate (minute mean)")
    ax2.set_ylabel("heart rate (bpm)")
    lines = ax.get_lines()[:2] + ax2.get_lines()
    ax.legend(lines, [str(line.get_label()) for line in lines], loc="lower right", fontsize=8)
    ax.set_title(title)
    _caption(fig, f"{LIMITATION_NOTE} Training insight, not medical advice.")
    return _save(fig, out_dir, stem)


def wbgt_chart(
    rm: RaceMorning,
    out_dir: Path,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    stem: str = "wbgt",
    title: str = "WBGT across the race window",
) -> ChartFiles:
    """Hourly WBGT with the race flag bands shaded and the race window marked."""
    pts = [(h.time_local, h.wbgt_c) for h in rm.hours if h.wbgt_c is not None]
    if not pts:
        raise ValueError("no WBGT values to chart")
    times = [t for t, _ in pts]
    x = np.array([_datenum(t) for t in times])
    values = np.array([float(v) for _, v in pts if v is not None])
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.subplots_adjust(bottom=0.22, top=0.9)
    lo, hi = min(values) - 2.0, max(values) + 2.0
    for b_lo, b_hi, name, colour in FLAG_BANDS:
        if b_hi > lo and b_lo < hi:
            ax.axhspan(max(b_lo, lo), min(b_hi, hi), color=colour, zorder=0)
            mid = (max(b_lo, lo) + min(b_hi, hi)) / 2
            ax.text(x[-1], mid, f" {name} flag", fontsize=7, va="center", clip_on=False)
    err = WBGT_MODEL_ERROR_C
    ax.fill_between(
        x,
        values - err,
        values + err,
        color="#333333",
        alpha=0.12,
        lw=0,
        label="about +/- 1 C model error",
    )
    ax.plot(x, values, color="#222222", marker="o", lw=2, label="WBGT")
    for edge, label in ((start, "start"), (end, "predicted finish")):
        if edge is not None:
            ex = _datenum(edge)
            ax.axvline(ex, color="#2166ac", ls="--", lw=1)
            ax.text(ex, hi, f" {label}", fontsize=7, va="top", color="#2166ac")
    ax.set_ylim(lo, hi)
    ax.set_ylabel("WBGT (C)")
    ax.set_xlabel("local time (Asia/Manila)")
    hours = [_datenum(t) for t in times if t.minute == 0]
    ax.set_xticks(hours, [t.strftime("%H:%M") for t in times if t.minute == 0])
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title(f"{title}, {rm.day.isoformat()}")
    _caption(
        fig,
        "Shaded bands: race flags (1996 ACSM, as used in race medicine). "
        "Training insight, not a go or no-go decision. " + ATTRIBUTION,
    )
    return _save(fig, out_dir, stem)
