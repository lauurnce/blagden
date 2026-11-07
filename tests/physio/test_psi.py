"""Tests for the Physiological Strain Index against docs/SCIENCE.md section 3."""

from __future__ import annotations

from pathlib import Path

from blagden.physio.psi import PSI_HR_CEILING_BPM, PSI_TC_CEILING_C, PSI_WEIGHT

SCIENCE_MD = Path(__file__).resolve().parents[2] / "docs" / "SCIENCE.md"


def test_constants_match_science_table() -> None:
    text = SCIENCE_MD.read_text(encoding="utf-8")
    body = text[text.index("\n## 3.") : text.index("\n## 4.")]
    rows: dict[str, list[str]] = {}
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if line.startswith("| ") and len(cells) > 5:
            rows[cells[0]] = cells
    assert float(rows["39.5"][1]) == PSI_TC_CEILING_C
    assert float(rows["180"][1]) == PSI_HR_CEILING_BPM
    assert float(rows["5, 5"][1]) == PSI_WEIGHT
    for key in ("39.5", "180", "5, 5"):
        assert rows[key][-1].startswith("VERIFIED"), key
    assert "70 bpm" in body  # default resting heart rate convention
