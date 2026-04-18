"""Tests for the disk-persistent cache."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from src import diskcache


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("EASYVIZ_CACHE_DIR", str(tmp_path))
    return tmp_path


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "entity": ["FRA", "DEU"],
        "iso3":   ["FRA", "DEU"],
        "year":   [2020, 2020],
        "value":  [1.5, 2.0],
    })


def test_save_then_load_round_trips(cache_dir):
    df = _sample_df()
    snap = datetime.now(timezone.utc)
    diskcache.save("wdi", "SP.POP.TOTL", df, snap)

    hit = diskcache.load("wdi", "SP.POP.TOTL")
    assert hit is not None
    df_out, snap_out = hit
    pd.testing.assert_frame_equal(df_out.reset_index(drop=True), df)
    assert abs((snap_out - snap).total_seconds()) < 1


def test_load_miss_returns_none(cache_dir):
    assert diskcache.load("wdi", "NO.SUCH.CODE") is None


def test_load_respects_ttl(cache_dir):
    """Entries older than ttl_seconds are treated as missing."""
    df = _sample_df()
    stale = datetime.now(timezone.utc) - timedelta(days=2)
    diskcache.save("owid", "life-expectancy", df, stale)

    # Short TTL → stale entry ignored.
    assert diskcache.load("owid", "life-expectancy", ttl_seconds=3600) is None
    # Long TTL → same entry returned.
    hit = diskcache.load("owid", "life-expectancy", ttl_seconds=7 * 86400)
    assert hit is not None


def test_unsafe_codes_do_not_escape_cache_dir(cache_dir):
    """A malicious code must not write outside the cache directory."""
    df = _sample_df()
    snap = datetime.now(timezone.utc)
    diskcache.save("wdi", "../../etc/passwd", df, snap)
    # Anything written should live under cache_dir.
    leaked = list(cache_dir.parent.glob("etc/passwd*"))
    assert not leaked


def test_clear_removes_entries(cache_dir):
    df = _sample_df()
    snap = datetime.now(timezone.utc)
    diskcache.save("wdi", "A", df, snap)
    diskcache.save("wdi", "B", df, snap)

    removed = diskcache.clear()
    assert removed >= 2  # parquet + json sidecars
    assert diskcache.load("wdi", "A") is None
