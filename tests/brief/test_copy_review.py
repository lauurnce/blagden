"""docs/COPY_REVIEW.md quotes every template string exactly."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_every_template_string_is_in_copy_review() -> None:
    templates = json.loads((ROOT / "shared" / "brief_templates.json").read_text(encoding="utf-8"))
    review = (ROOT / "docs" / "COPY_REVIEW.md").read_text(encoding="utf-8")
    for lang in ("en", "tl"):
        for key, value in templates[lang].items():
            strings = value.values() if isinstance(value, dict) else [value]
            for s in strings:
                assert f"`{s}`" in review, f"{lang}.{key} not quoted in COPY_REVIEW.md"


def test_example_briefs_match_golden_text() -> None:
    review = (ROOT / "docs" / "COPY_REVIEW.md").read_text(encoding="utf-8")
    for path in sorted((ROOT / "tests" / "data" / "briefs").glob("*.txt")):
        assert f"> {path.read_text(encoding='utf-8').strip()}" in review, path.name
