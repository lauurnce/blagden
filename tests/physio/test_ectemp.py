"""Tests for the ECTemp filter against docs/SCIENCE.md section 1."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from blagden.physio.ectemp import (
    DEFAULT_TC0_C,
    DEFAULT_V0_C2,
    ECTEMP_2013,
)

SCIENCE_MD = Path(__file__).resolve().parents[2] / "docs" / "SCIENCE.md"


def science_table(section: str, next_section: str) -> dict[str, list[str]]:
    """Return the parameter table rows of one SCIENCE.md section, keyed by symbol."""
    text = SCIENCE_MD.read_text(encoding="utf-8")
    body = text[text.index(f"\n## {section}") : text.index(f"\n## {next_section}")]
    table = body[body.index("### Parameters") :]
    rows: dict[str, list[str]] = {}
    for line in table.splitlines()[1:]:
        if line.startswith("### "):
            break
        if line.startswith("|") and not line.startswith("|---"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows[cells[0]] = cells[1:]
    return rows


def test_parameters_match_science_table() -> None:
    rows = science_table("1.", "2.")
    expected = {
        r"$\gamma$": ECTEMP_2013.gamma,
        r"$b_0$": ECTEMP_2013.b0,
        r"$b_1$": ECTEMP_2013.b1,
        r"$b_2$": ECTEMP_2013.b2,
        r"$\sigma$": ECTEMP_2013.sigma,
    }
    for symbol, value in expected.items():
        assert float(rows[symbol][0]) == value, symbol
        assert rows[symbol][-1].startswith("VERIFIED"), symbol
    assert float(rows[r"$\gamma^2$"][0]) == pytest.approx(ECTEMP_2013.gamma**2, abs=1e-12)
    assert float(rows[r"$\sigma^2$"][0]) == pytest.approx(ECTEMP_2013.sigma**2, abs=1e-9)
    start = rows["$CT_0$, $v_0$ with no measurement"]
    tc0, v0 = (float(x) for x in re.split(r",\s*", start[0]))
    assert (tc0, v0) == (DEFAULT_TC0_C, DEFAULT_V0_C2)
    assert start[-1].startswith("VERIFIED")
