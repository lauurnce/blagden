"""Optional LLM wording for the brief. Off by default; templates are always the fallback.

Environment variables pick the provider:

    BLAGDEN_LLM_PROVIDER   "anthropic" (the only provider built so far); unset = templates only
    BLAGDEN_LLM_MODEL      model name (anthropic default: claude-opus-5-5)
    BLAGDEN_LLM_API_KEY    API key; if unset the provider's own lookup is used
                           (for anthropic: ANTHROPIC_API_KEY or an ``ant auth login`` profile)

The prompt contains only the Facts. Every generated text goes through the
grounding check; if a number is not in Facts, a forbidden word appears, the
text is too long, or the provider fails, the template brief is returned and the
reason is logged. No provider SDK is a dependency of blagden: the anthropic
provider imports ``anthropic`` only when it is selected (``pip install
blagden[llm-anthropic]``).
"""

from __future__ import annotations

import importlib
import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Literal, Protocol

from blagden.brief.facts import Facts
from blagden.brief.grounding import ground_check
from blagden.brief.template import MAX_WORDS, Lang, render_brief

log = logging.getLogger("blagden.brief")

ENV_PROVIDER = "BLAGDEN_LLM_PROVIDER"
ENV_MODEL = "BLAGDEN_LLM_MODEL"
ENV_KEY = "BLAGDEN_LLM_API_KEY"
ANTHROPIC_DEFAULT_MODEL = "claude-opus-5-5"

LANG_NAMES = {
    "en": "plain English",
    "tl": "Taglish (Filipino and English mixed as Metro Manila runners speak)",
}

INSTRUCTIONS = (
    "Write a race-morning brief for a runner in {language}, under {max_words} words, "
    "in short plain sentences. Use only the facts below. Every number you write must "
    "appear in the facts exactly; do not round, convert or add numbers. Do not give medical "
    "advice or say conditions are safe. End with: this is training insight, not medical advice."
)


class LLMError(RuntimeError):
    """The provider could not produce text."""


class LLMProvider(Protocol):
    """Anything that turns a prompt into text."""

    @property
    def name(self) -> str:
        """Short provider name for logs, for example "anthropic"."""
        ...

    def generate(self, prompt: str) -> str:
        """Return generated text for ``prompt``."""
        ...


@dataclass(frozen=True)
class BriefText:
    """A finished brief and where its wording came from."""

    text: str
    source: Literal["template", "llm"]
    provider: str | None = None
    rejected_reason: str | None = None


def facts_payload(facts: Facts) -> dict[str, object]:
    """Facts as plain JSON values, without the derived allowed set."""
    out: dict[str, object] = {}
    for f in fields(facts):
        if f.name == "allowed_numbers":
            continue
        value = getattr(facts, f.name)
        out[f.name] = [list(row) for row in value] if f.name == "wbgt_by_hour" else value
    return out


def build_prompt(facts: Facts, lang: Lang = "en") -> str:
    """Build the prompt: fixed instructions plus the Facts as JSON, nothing else."""
    head = INSTRUCTIONS.format(language=LANG_NAMES[lang], max_words=MAX_WORDS)
    return f"{head}\n\nFacts:\n{json.dumps(facts_payload(facts), indent=1, sort_keys=True)}"


@dataclass(frozen=True)
class AnthropicProvider:
    """Claude through the official ``anthropic`` SDK, imported only when used."""

    model: str = ANTHROPIC_DEFAULT_MODEL
    api_key: str | None = None
    name: str = "anthropic"

    def generate(self, prompt: str) -> str:
        """Call the Messages API once and return the text."""
        try:
            anthropic = importlib.import_module("anthropic")
        except ImportError as exc:
            raise LLMError("the anthropic package is not installed") from exc
        client = (
            anthropic.Anthropic(api_key=self.api_key) if self.api_key else anthropic.Anthropic()
        )
        response = client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            raise LLMError("the model declined the request")
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            raise LLMError("the model returned no text")
        return text


def provider_from_env(env: Mapping[str, str] | None = None) -> LLMProvider | None:
    """Return the configured provider, or None for templates only."""
    env = os.environ if env is None else env
    name = env.get(ENV_PROVIDER, "").strip().lower()
    if not name:
        return None
    if name == "anthropic":
        return AnthropicProvider(
            model=env.get(ENV_MODEL) or ANTHROPIC_DEFAULT_MODEL, api_key=env.get(ENV_KEY) or None
        )
    log.warning("LLM provider %r is not supported; using the template brief", name)
    return None


def write_brief(
    facts: Facts, lang: Lang = "en", provider: LLMProvider | None = None, *, use_env: bool = True
) -> BriefText:
    """Return LLM wording when a provider is configured and the text passes the checks.

    Falls back to the template brief, logging the reason, on any failure.
    """
    template = render_brief(facts, lang)
    chosen = provider or (provider_from_env() if use_env else None)
    if chosen is None:
        return BriefText(template, "template")
    try:
        text = chosen.generate(build_prompt(facts, lang))
    except Exception as exc:  # any provider failure falls back; the reason is logged
        log.warning("LLM brief rejected (provider error: %s); using the template brief", exc)
        return BriefText(template, "template", chosen.name, f"provider error: {exc}")
    result = ground_check(text, facts.allowed_numbers)
    reason: str | None = None if result.ok else result.reason()
    if reason is None and len(text.split()) > MAX_WORDS:
        reason = f"{len(text.split())} words, over the {MAX_WORDS}-word limit"
    if reason is not None:
        log.warning("LLM brief rejected (%s); using the template brief", reason)
        return BriefText(template, "template", chosen.name, reason)
    return BriefText(text, "llm", chosen.name)
