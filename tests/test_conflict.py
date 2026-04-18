"""Tests for conflict-data loaders — monkeypatched, no network."""

from __future__ import annotations

import pytest
import requests

import src.conflict as conf


@pytest.fixture
def _unwrap():
    """Strip the Streamlit @cache_data decorator so monkeypatch is effective."""
    return (
        getattr(conf.fetch_ucdp, "__wrapped__", conf.fetch_ucdp),
        getattr(conf.fetch_hdx_csv, "__wrapped__", conf.fetch_hdx_csv),
    )


# ── UCDP ──────────────────────────────────────────────────────────────────────

def test_ucdp_returns_dataframe_and_normalises_columns(monkeypatch, _unwrap):
    fetch_ucdp, _ = _unwrap

    class _R:
        def raise_for_status(self): pass
        def json(self):
            return {
                "Result": [
                    {"date_start": "2020-01-15", "date_end": "2020-01-15",
                     "country": "Nigeria", "region": "Africa",
                     "best": "3", "low": "1", "high": "5",
                     "type_of_violence": 1, "conflict_name": "Insurgency",
                     "latitude": "9.1", "longitude": "7.5", "year": "2020"},
                    {"date_start": "2021-02-10", "date_end": "2021-02-10",
                     "country": "Nigeria", "region": "Africa",
                     "best": "0", "low": "0", "high": "0",
                     "type_of_violence": 2, "conflict_name": "Other",
                     "latitude": "6.4", "longitude": "3.4", "year": "2021"},
                ],
                "NextPageUrl": None,
            }

    monkeypatch.setattr(conf._session, "get", lambda *a, **kw: _R())
    res = fetch_ucdp(country="Nigeria", year_from=2020, year_to=2021)
    assert len(res.df) == 2
    assert res.df["best"].dtype.kind in ("f", "i")
    assert set(["country", "best", "year"]).issubset(res.df.columns)


def test_ucdp_empty_result_raises_empty(monkeypatch, _unwrap):
    fetch_ucdp, _ = _unwrap

    class _R:
        def raise_for_status(self): pass
        def json(self): return {"Result": [], "NextPageUrl": None}
    monkeypatch.setattr(conf._session, "get", lambda *a, **kw: _R())

    with pytest.raises(conf.ConflictFetchError) as excinfo:
        fetch_ucdp(country="Atlantis")
    assert excinfo.value.reason == "empty"


def test_ucdp_timeout_tagged(monkeypatch, _unwrap):
    fetch_ucdp, _ = _unwrap
    def _boom(*a, **kw): raise requests.Timeout("slow")
    monkeypatch.setattr(conf._session, "get", _boom)
    with pytest.raises(conf.ConflictFetchError) as excinfo:
        fetch_ucdp(country="Nigeria")
    assert excinfo.value.reason == "timeout"


# ── HDX ───────────────────────────────────────────────────────────────────────

def test_hdx_url_guard_rejects_junk(_unwrap):
    _, fetch_hdx_csv = _unwrap
    with pytest.raises(conf.ConflictFetchError) as excinfo:
        fetch_hdx_csv("not-a-url")
    assert excinfo.value.reason == "invalid_url"


def test_hdx_parses_csv_payload(monkeypatch, _unwrap):
    _, fetch_hdx_csv = _unwrap
    csv_body = b"country,year,value\nFRA,2020,1.5\nDEU,2020,2.0\n"

    class _R:
        content = csv_body
        def raise_for_status(self): pass
    monkeypatch.setattr(conf._session, "get", lambda *a, **kw: _R())

    df = fetch_hdx_csv("https://data.humdata.org/dataset/foo/resource/bar.csv")
    assert list(df.columns) == ["country", "year", "value"]
    assert df.shape == (2, 3)


def test_hdx_http_error_tagged(monkeypatch, _unwrap):
    _, fetch_hdx_csv = _unwrap
    def _boom(*a, **kw): raise requests.ConnectionError("x")
    monkeypatch.setattr(conf._session, "get", _boom)
    with pytest.raises(conf.ConflictFetchError) as excinfo:
        fetch_hdx_csv("https://data.humdata.org/dataset/foo.csv")
    assert excinfo.value.reason == "http"
