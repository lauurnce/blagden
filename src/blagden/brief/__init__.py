"""Race-morning brief built only from computed numbers. Training insight, not medical advice."""

from blagden.brief.facts import Facts, build_facts
from blagden.brief.grounding import GroundingResult, ground_check
from blagden.brief.llm import BriefText, LLMProvider, provider_from_env, write_brief
from blagden.brief.template import render_brief

__all__ = [
    "BriefText",
    "Facts",
    "GroundingResult",
    "LLMProvider",
    "build_facts",
    "ground_check",
    "provider_from_env",
    "render_brief",
    "write_brief",
]
