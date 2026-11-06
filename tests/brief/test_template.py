"""Template briefs for three fixed Facts snapshots, compared with golden text."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from blagden.brief.facts import Facts, with_allowed
from blagden.brief.grounding import ground_check
from blagden.brief.template import MAX_WORDS, render_brief

DATA = Path(__file__).resolve().parents[1] / "data" / "briefs"
SNAPSHOTS = ("hot_rise_half", "cool_10k", "hot_flat_no_prediction")


def snapshot(name: str) -> Facts:
    data = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
    data["wbgt_by_hour"] = tuple(tuple(row) for row in data["wbgt_by_hour"])
    return with_allowed(Facts(**data))


@pytest.mark.parametrize("lang", ["en", "tl"])
@pytest.mark.parametrize("name", SNAPSHOTS)
def test_matches_golden_text(name: str, lang: str) -> None:
    expected = (DATA / f"{name}.{lang}.txt").read_text(encoding="utf-8").rstrip("\n")
    assert render_brief(snapshot(name), lang) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize("lang", ["en", "tl"])
@pytest.mark.parametrize("name", SNAPSHOTS)
def test_template_is_grounded_short_and_framed(name: str, lang: str) -> None:
    facts = snapshot(name)
    text = render_brief(facts, lang)  # type: ignore[arg-type]
    assert ground_check(text, facts.allowed_numbers).ok
    assert len(text.split()) < MAX_WORDS
    assert "medical advice" in text


def test_sentence_choice_follows_facts() -> None:
    hot = render_brief(snapshot("hot_rise_half"))
    assert "by 6:30 AM" in hot and "after km 14" in hot and "treat the range as rough" in hot
    cool = render_brief(snapshot("cool_10k"))
    assert cool.startswith("Cooler start: WBGT stays under 23 until 6:45 AM.")
    assert "Drink" not in cool and "rough" not in cool
    flat = render_brief(snapshot("hot_flat_no_prediction"))
    assert "for your whole race" in flat and "pace" not in flat


def test_over_long_text_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    import blagden.brief.template as t

    monkeypatch.setattr(t, "sentences", lambda facts, lang="en": ["word"] * (MAX_WORDS + 1))
    with pytest.raises(ValueError, match="120-word"):
        t.render_brief(snapshot("cool_10k"))
