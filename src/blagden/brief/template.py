"""Deterministic race-morning brief from Facts, in English or Taglish.

Wording lives in ``shared/brief_templates.json`` (shared with the web app) and
is listed for review in docs/COPY_REVIEW.md. Templates hold placeholders only;
the choice of sentence is made here from Facts, so the same Facts always give
the same text.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Literal

from blagden.brief.facts import Facts

Lang = Literal["en", "tl"]
MAX_WORDS = 120

_CANDIDATES = (
    Path(__file__).with_name("brief_templates.json"),  # installed wheel
    Path(__file__).resolve().parents[3] / "shared" / "brief_templates.json",  # source tree
)


@cache
def load_templates() -> dict[str, dict[str, object]]:
    """Read the template file."""
    for path in _CANDIDATES:
        if path.exists():
            data: dict[str, dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
            return data
    raise FileNotFoundError("brief_templates.json not found")


def sentences(facts: Facts, lang: Lang = "en") -> list[str]:
    """Return the brief's sentences in order."""
    t = load_templates()[lang]
    bands = t["bands"]
    assert isinstance(bands, dict)

    def fill(key: str, **values: str) -> str:
        template = t[key]
        assert isinstance(template, str)
        return template.format(**values)

    out = []
    if facts.cool_threshold is not None:
        if facts.cool_until is not None:
            out.append(fill("start_cool_until", cool_threshold=facts.cool_threshold,
                            cool_until=facts.cool_until))  # fmt: skip
        else:
            out.append(fill("start_cool_all", cool_threshold=facts.cool_threshold))
    elif facts.rise_time is not None and facts.rise_level is not None:
        out.append(fill("start_hot_rise", start_time=facts.start_time, start_wbgt=facts.start_wbgt,
                        start_band=bands[facts.start_level], rise_band=bands[facts.rise_level],
                        rise_time=facts.rise_time))  # fmt: skip
    else:
        out.append(fill("start_hot_flat", start_time=facts.start_time, start_wbgt=facts.start_wbgt,
                        start_band=bands[facts.start_level]))  # fmt: skip
    if facts.pace_cap and facts.finish and facts.finish_low and facts.finish_high:
        out.append(fill("pace", pace_cap=facts.pace_cap, finish=facts.finish,
                        finish_low=facts.finish_low, finish_high=facts.finish_high))  # fmt: skip
    if facts.drink_from_start:
        out.append(fill("drink_from_start"))
    elif facts.drink_km is not None:
        out.append(fill("drink_from_km", drink_km=facts.drink_km))
    if facts.hi_peak is not None and facts.hi_category is not None:
        out.append(fill("heat_index", hi_peak=facts.hi_peak, hi_category=facts.hi_category))
    if facts.extrapolated:
        out.append(fill("extrapolated"))
    out.append(fill("closing"))
    return out


def render_brief(facts: Facts, lang: Lang = "en") -> str:
    """Render the brief as one paragraph. Raises ValueError if it exceeds 120 words."""
    text = " ".join(sentences(facts, lang))
    if len(text.split()) > MAX_WORDS:
        raise ValueError(f"brief is {len(text.split())} words, over the {MAX_WORDS}-word limit")
    return text
