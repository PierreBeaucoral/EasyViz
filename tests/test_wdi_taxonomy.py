"""Tests for the WDI-taxonomy importer (no network)."""

from __future__ import annotations

import pytest

import src.wdi_taxonomy as tax


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("EASYVIZ_CACHE_DIR", str(tmp_path))
    return tmp_path


def _wb_response(records: list[dict]) -> list:
    """Mimic the [meta, records] envelope returned by the WB API."""
    return [{"page": 1, "pages": 1, "per_page": 25000, "total": len(records)}, records]


def test_normalise_happy_path():
    record = {
        "id": "SP.DYN.LE00.IN",
        "name": "Life expectancy at birth, total (years)",
        "topics": [{"id": "9", "value": "Health"}],
        "source": {"id": "2", "value": "years"},
    }
    out = tax._normalise(record)
    assert out["id"] == "wdi_sp_dyn_le00_in"
    assert out["indicator"] == "SP.DYN.LE00.IN"
    assert out["name"].startswith("Life expectancy")
    assert out["category"] == "Health"
    assert out["source"] == "wdi"
    assert "expectancy" in out["tags"]


def test_normalise_defaults_missing_topic_to_other():
    out = tax._normalise({"id": "X.Y.Z", "name": "Something"})
    assert out["category"] == "Other"


def test_normalise_skips_records_without_id_or_name():
    assert tax._normalise({}) is None
    assert tax._normalise({"id": "X"}) is None


def test_refresh_writes_cache(cache_dir, monkeypatch):
    class _FakeR:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return _wb_response([
                {"id": "A.B.C", "name": "Thing", "topics": [{"value": "Health"}]},
                {"id": "D.E.F", "name": "Widget", "topics": [{"value": "Economy"}]},
            ])
    monkeypatch.setattr(tax._session, "get", lambda *a, **kw: _FakeR())

    recs = tax.refresh()
    assert len(recs) == 2
    assert tax._taxonomy_path().exists()


def test_refresh_falls_back_to_cached_on_network_fail(cache_dir, monkeypatch):
    import json
    from datetime import datetime, timezone
    tax._taxonomy_path().write_text(json.dumps({
        "fetched": datetime.now(timezone.utc).isoformat(),
        "records": [{"id": "wdi_a_b_c", "name": "Cached", "category": "Health",
                     "source": "wdi", "indicator": "A.B.C", "unit": "", "tags": []}],
    }))

    def _boom(*a, **kw):
        import requests
        raise requests.ConnectionError("simulated")
    monkeypatch.setattr(tax._session, "get", _boom)

    recs = tax.refresh()
    assert len(recs) == 1
    assert recs[0]["indicator"] == "A.B.C"


def test_refresh_empty_body_returns_empty(cache_dir, monkeypatch):
    class _FakeR:
        def raise_for_status(self): pass
        def json(self):
            return [{"page": 1, "pages": 1}, None]
    monkeypatch.setattr(tax._session, "get", lambda *a, **kw: _FakeR())
    assert tax.refresh() == []
