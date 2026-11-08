"""Markdown report writer."""

from __future__ import annotations

from pathlib import Path

from blagden.charts import ChartFiles
from blagden.report import FOOTER, md_chart, md_table, write_report


def test_table_escapes_and_shows_missing() -> None:
    text = md_table(["a", "b"], [[1, None], ["x|y", 2.5]])
    assert text.splitlines() == ["| a | b |", "|---|---|", "| 1 | n/a |", "| x\\|y | 2.5 |"]


def test_report_with_relative_chart_links(tmp_path: Path) -> None:
    chart = ChartFiles(tmp_path / "wbgt.png", tmp_path / "wbgt.svg")
    path = write_report(tmp_path, "Race morning", [("WBGT", md_chart(chart, tmp_path, "WBGT"))])
    text = path.read_text(encoding="utf-8")
    assert path.name == "REPORT.md" and text.startswith("# Race morning\n")
    assert "![WBGT](wbgt.png)" in text and "[SVG version](wbgt.svg)" in text
    assert text.rstrip().endswith(FOOTER)
