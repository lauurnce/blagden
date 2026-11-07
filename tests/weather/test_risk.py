"""Risk labels against the tables in docs/SCIENCE.md section 5."""

from __future__ import annotations

from pathlib import Path

import pytest

from blagden.weather.risk import (
    ACSM_2007_ROWS,
    FLAG_MEANINGS,
    RACINAIS_THRESHOLDS_C,
    acsm2007_text,
    flag_for,
    racinais_level,
    racinais_thresholds,
    risk_label,
    wa2020_band,
)

SCIENCE_MD = Path(__file__).resolve().parents[2] / "docs" / "SCIENCE.md"
TEXT = SCIENCE_MD.read_text(encoding="utf-8")
SECTION_5 = TEXT[TEXT.index("\n## 5.") : TEXT.index("\n## 6.")]


def table_rows(start: str, n_cells: int) -> list[list[str]]:
    body = SECTION_5[SECTION_5.index(start) :]
    rows = []
    for line in body.splitlines()[1:]:
        if line.startswith("**") or line.startswith("###"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if line.startswith("| ") and len(cells) == n_cells:
            rows.append(cells)
    return rows[1:]  # drop the header


def test_flag_meanings_match_science() -> None:
    rows = table_rows("**Flag system", 5)
    assert [r[0].lower() for r in rows] == list(FLAG_MEANINGS)
    for row in rows:
        assert FLAG_MEANINGS[row[0].lower()] in row[3]  # type: ignore[index]


def test_acsm_2007_rows_match_science() -> None:
    rows = table_rows("**ACSM position stand 2007**", 4)
    verified = [r for r in rows if r[-1] == "VERIFIED"]
    assert len(verified) == len(ACSM_2007_ROWS)
    for (upper, text), row in zip(ACSM_2007_ROWS, verified, strict=True):
        assert row[0].endswith(f"{upper:.1f}")
        assert f'"{text}"' == row[2]


def test_racinais_table_matches_science() -> None:
    rows = table_rows("**Racinais et al. 2015 consensus**", 5)
    for row in rows:
        assert tuple(float(x) for x in row[1:4]) == RACINAIS_THRESHOLDS_C[row[0].lower()]


def test_wa_bands_match_science() -> None:
    for name in ("Almost Safe", "Caution", "Warning", "Severe Warning", "Danger"):
        assert name in SECTION_5


@pytest.mark.parametrize(
    ("wbgt", "flag"),
    [(9.99, "white"), (10.0, "green"), (17.99, "green"), (18.0, "yellow"), (22.99, "yellow"),
     (23.0, "red"), (28.0, "red"), (28.01, "black")],
)  # fmt: skip
def test_flag_boundaries(wbgt: float, flag: str) -> None:
    assert flag_for(wbgt) == flag


@pytest.mark.parametrize(
    ("wbgt", "band"),
    [(20.99, "Almost Safe"), (21.0, "Caution"), (25.0, "Warning"), (28.0, "Severe Warning"),
     (30.0, "Severe Warning"), (30.01, "Danger")],
)  # fmt: skip
def test_world_athletics_boundaries(wbgt: float, band: str) -> None:
    assert wa2020_band(wbgt) == band


def test_acsm_2007_rounds_to_tenth_and_stops_at_30() -> None:
    assert acsm2007_text(27.84) == ACSM_2007_ROWS[4][1]
    assert acsm2007_text(27.86) == ACSM_2007_ROWS[5][1]
    assert acsm2007_text(30.04) == ACSM_2007_ROWS[5][1]
    assert acsm2007_text(30.06) is None  # cells above 30.0 C are UNVERIFIED


def test_racinais_interpolates_in_humidity() -> None:
    assert racinais_thresholds(50.0) == ((24.0, 28.0, 33.0), False)
    assert racinais_thresholds(100.0) == ((18.0, 24.0, 28.0), False)
    mid, clamped = racinais_thresholds(87.5)
    assert mid == pytest.approx((19.0, 25.0, 28.5)) and not clamped
    assert racinais_thresholds(30.0) == ((24.0, 28.0, 33.0), True)


@pytest.mark.parametrize(
    ("wbgt", "rh", "level"),
    [(17.9, 100.0, "below moderate"), (18.0, 100.0, "moderate"), (26.0, 75.0, "high"),
     (29.0, 75.0, "excessive"), (23.9, 50.0, "below moderate")],
)  # fmt: skip
def test_racinais_levels(wbgt: float, rh: float, level: str) -> None:
    assert racinais_level(wbgt, rh)[0] == level


def test_risk_label_carries_model_error() -> None:
    label = risk_label(26.3, 88.0)
    assert label.flag == "red" and label.wa2020_band == "Warning"
    assert label.racinais_level == "high" and label.model_error_c == 1.0
