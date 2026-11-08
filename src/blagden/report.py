"""Markdown reports that bundle a command's summary, charts and brief.

A report is one ``REPORT.md`` in the output folder, with charts referenced by
relative path so the folder can be moved or shared as a whole. Reports never
contain coordinates from a run file.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from blagden.charts import ChartFiles

FOOTER = "Training insight, not medical advice."


def md_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """Render a Markdown table; None is shown as n/a."""

    def cell(v: object) -> str:
        return "n/a" if v is None else str(v).replace("|", "\\|")

    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def md_chart(chart: ChartFiles, out_dir: Path, alt: str) -> str:
    """Embed a chart by its PNG, with a link to the SVG."""
    png, svg = chart.png.relative_to(out_dir), chart.svg.relative_to(out_dir)
    return f"![{alt}]({png.as_posix()})\n\n[SVG version]({svg.as_posix()})"


def write_report(out_dir: Path, title: str, sections: Sequence[tuple[str, str]]) -> Path:
    """Write ``REPORT.md`` with one ``##`` heading per section and return its path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = [f"# {title}", ""]
    for heading, body in sections:
        parts += [f"## {heading}", "", body.strip(), ""]
    parts += ["---", "", FOOTER, ""]
    path = out_dir / "REPORT.md"
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
