"""The LLM path with fake providers. No test calls a real provider."""

from __future__ import annotations

import json
import logging
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from blagden.brief import llm
from blagden.brief.facts import Facts, with_allowed
from blagden.brief.template import render_brief

DATA = Path(__file__).resolve().parents[1] / "data" / "briefs"


def facts() -> Facts:
    data = json.loads((DATA / "hot_rise_half.json").read_text(encoding="utf-8"))
    data["wbgt_by_hour"] = tuple(tuple(row) for row in data["wbgt_by_hour"])
    return with_allowed(Facts(**data))


@dataclass
class FakeProvider:
    reply: str = ""
    error: Exception | None = None
    name: str = "fake"
    prompts: list[str] = field(default_factory=list)

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.reply


GOOD = (
    "Gun at 5:00 AM, WBGT 24.7 and rising to the high-risk band by 06:30. Hold 6:00/km, "
    "aiming for 2:06:42 (2:03:05 to 2:10:54). From km 14, drink at every station. "
    "This is training insight, not medical advice."
)


def test_no_provider_means_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(llm.ENV_PROVIDER, raising=False)
    out = llm.write_brief(facts())
    assert out.source == "template" and out.text == render_brief(facts())


def test_grounded_llm_text_is_used() -> None:
    p = FakeProvider(GOOD)
    out = llm.write_brief(facts(), provider=p)
    assert out.source == "llm" and out.text == GOOD and out.provider == "fake"


def test_invented_number_falls_back_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    p = FakeProvider(GOOD.replace("6:00/km", "5:55/km"))
    with caplog.at_level(logging.WARNING, logger="blagden.brief"):
        out = llm.write_brief(facts(), "tl", provider=p)
    assert out.source == "template" and out.text == render_brief(facts(), "tl")
    assert out.rejected_reason and "5:55" in out.rejected_reason
    assert "5:55" in caplog.text


@pytest.mark.parametrize(
    ("reply", "error", "reason"),
    [
        (GOOD + " Conditions are safe.", None, "forbidden words: safe"),
        (" ".join(["run"] * 130), None, "120-word limit"),
        ("", llm.LLMError("timeout"), "provider error: timeout"),
    ],
)
def test_other_rejections_fall_back(reply: str, error: Exception | None, reason: str) -> None:
    out = llm.write_brief(facts(), provider=FakeProvider(reply, error))
    assert out.source == "template" and reason in (out.rejected_reason or "")


def test_prompt_contains_only_the_facts() -> None:
    p = FakeProvider(GOOD)
    llm.write_brief(facts(), provider=p)
    prompt = p.prompts[0]
    head, payload = prompt.split("\n\nFacts:\n", 1)
    assert json.loads(payload) == llm.facts_payload(facts())
    assert "allowed_numbers" not in payload
    assert "Taglish" not in head and "plain English" in head
    assert render_brief(facts()) not in prompt  # the template text is not sent


def test_provider_selection_from_environment(caplog: pytest.LogCaptureFixture) -> None:
    assert llm.provider_from_env({}) is None
    p = llm.provider_from_env({llm.ENV_PROVIDER: "Anthropic", llm.ENV_KEY: "k"})
    assert isinstance(p, llm.AnthropicProvider)
    assert (p.model, p.api_key) == (llm.ANTHROPIC_DEFAULT_MODEL, "k")
    q = llm.provider_from_env({llm.ENV_PROVIDER: "anthropic", llm.ENV_MODEL: "claude-haiku-5-5"})
    assert (
        isinstance(q, llm.AnthropicProvider) and q.model == "claude-haiku-5-5" and q.api_key is None
    )
    with caplog.at_level(logging.WARNING, logger="blagden.brief"):
        assert llm.provider_from_env({llm.ENV_PROVIDER: "other"}) is None
    assert "not supported" in caplog.text


def test_env_provider_is_used_by_write_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeProvider(GOOD)
    monkeypatch.setattr(llm, "provider_from_env", lambda env=None: fake)
    assert llm.write_brief(facts()).source == "llm"
    assert llm.write_brief(facts(), use_env=False).source == "template"


def fake_anthropic(
    monkeypatch: pytest.MonkeyPatch, stop_reason: str, text: str
) -> dict[str, object]:
    calls: dict[str, object] = {}

    class Messages:
        def create(self, **kwargs: object) -> object:
            calls.update(kwargs)
            block = types.SimpleNamespace(type="text", text=text)
            return types.SimpleNamespace(stop_reason=stop_reason, content=[block])

    class Client:
        def __init__(self, api_key: str | None = None) -> None:
            calls["api_key"] = api_key
            self.beta = types.SimpleNamespace(messages=Messages())

    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=Client))
    return calls


def test_anthropic_provider_request_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_anthropic(monkeypatch, "end_turn", GOOD)
    out = llm.write_brief(facts(), provider=llm.AnthropicProvider(api_key="k"))
    assert out.source == "llm" and out.provider == "anthropic"
    assert calls["model"] == "claude-opus-5-5" and calls["api_key"] == "k"
    assert calls["fallbacks"] == "default" and calls["betas"] == ["server-side-fallback-2026-07-01"]
    assert "thinking" not in calls


def test_anthropic_refusal_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_anthropic(monkeypatch, "refusal", "")
    out = llm.write_brief(facts(), provider=llm.AnthropicProvider())
    assert out.source == "template" and "declined" in (out.rejected_reason or "")


def test_missing_sdk_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)
    out = llm.write_brief(facts(), provider=llm.AnthropicProvider())
    assert out.source == "template" and "not installed" in (out.rejected_reason or "")
