"""Tests for the on-disk weather cache."""

from __future__ import annotations

from pathlib import Path

from blagden.weather.cache import DiskCache, default_cache_dir

URL = "https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0"


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


def test_hit_within_ttl_and_miss_after(tmp_path: Path) -> None:
    clock = Clock()
    cache = DiskCache(tmp_path, clock)
    assert cache.get(URL, 60.0) is None
    cache.put(URL, b'{"a": 1}')
    clock.now += 59.0
    assert cache.get(URL, 60.0) == b'{"a": 1}'
    clock.now += 2.0
    assert cache.get(URL, 60.0) is None


def test_none_ttl_never_expires(tmp_path: Path) -> None:
    clock = Clock()
    cache = DiskCache(tmp_path, clock)
    cache.put(URL, b"{}")
    clock.now += 10**9
    assert cache.get(URL, None) == b"{}"


def test_keys_differ_by_url_and_corrupt_entry_is_a_miss(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    cache.put(URL, b"{}")
    assert cache.get(URL + "&x=1", None) is None
    cache.path_for(URL).write_text("not json", encoding="utf-8")
    assert cache.get(URL, None) is None


def test_default_dir_follows_xdg(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert default_cache_dir() == tmp_path / "blagden" / "open-meteo"
