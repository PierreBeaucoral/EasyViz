"""
Unit tests for `src.geo` — non-network helpers only.

Network calls (fetch_admin_geojson) aren't tested directly because they
depend on an external API; the error paths are covered by construction
of `GeoFetchError` and by a monkeypatched fake request.
"""

from __future__ import annotations

import pytest
import requests

from src.geo import (
    GeoFetchError,
    fetch_admin_geojson,
    get_region_names,
    match_regions,
    simplify_geojson,
    subset_geojson,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _square(lon0: float, lat0: float, size: float = 1.0) -> dict:
    """Return a dense-ish polygon for simplification tests."""
    # 10-point perimeter — simplification should prune to 4-5 vertices.
    step = size / 10
    ring = []
    for i in range(11):   # bottom edge
        ring.append([lon0 + i * step, lat0])
    for i in range(1, 11):  # right edge
        ring.append([lon0 + size, lat0 + i * step])
    for i in range(1, 11):  # top edge
        ring.append([lon0 + size - i * step, lat0 + size])
    for i in range(1, 11):  # left edge, closing
        ring.append([lon0, lat0 + size - i * step])
    return {"type": "Polygon", "coordinates": [ring]}


@pytest.fixture
def sample_geojson() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature",
             "properties": {"shapeName": "Alpha"},
             "geometry": _square(0, 0)},
            {"type": "Feature",
             "properties": {"shapeName": "Beta"},
             "geometry": _square(10, 0)},
            {"type": "Feature",
             "properties": {"shapeName": "Gamma"},
             "geometry": _square(20, 0)},
        ],
    }


# ── get_region_names ──────────────────────────────────────────────────────────

def test_get_region_names_returns_sorted_unique(sample_geojson):
    names = get_region_names(sample_geojson)
    assert names == ["Alpha", "Beta", "Gamma"]


def test_get_region_names_handles_empty():
    assert get_region_names({"features": []}) == []
    assert get_region_names({}) == []


def test_get_region_names_skips_empty_strings():
    gj = {"features": [
        {"properties": {"shapeName": ""}},
        {"properties": {"shapeName": "X"}},
    ]}
    assert get_region_names(gj) == ["X"]


# ── match_regions ─────────────────────────────────────────────────────────────

def test_match_regions_exact():
    out = match_regions(["Alpha", "Beta"], ["Alpha", "Beta", "Gamma"])
    assert out == {"Alpha": "Alpha", "Beta": "Beta"}


def test_match_regions_fuzzy_close_typo():
    # Token-sort ratio should still match 'alphaa' to 'Alpha'.
    out = match_regions(["alphaa"], ["Alpha", "Beta"], threshold=60)
    assert out["alphaa"] == "Alpha"


def test_match_regions_returns_none_below_threshold():
    out = match_regions(["QQQ"], ["Alpha", "Beta"], threshold=95)
    assert out["QQQ"] is None


# ── subset_geojson ────────────────────────────────────────────────────────────

def test_subset_keeps_only_named_features(sample_geojson):
    out = subset_geojson(sample_geojson, {"Alpha", "Gamma"})
    names = [f["properties"]["shapeName"] for f in out["features"]]
    assert set(names) == {"Alpha", "Gamma"}
    assert len(out["features"]) == 2


def test_subset_empty_names_returns_original(sample_geojson):
    out = subset_geojson(sample_geojson, [])
    assert out == sample_geojson


def test_subset_preserves_top_level_keys(sample_geojson):
    sample_geojson["crs"] = "EPSG:4326"
    out = subset_geojson(sample_geojson, {"Alpha"})
    assert out["type"] == "FeatureCollection"
    assert out["crs"] == "EPSG:4326"


def test_subset_is_non_destructive(sample_geojson):
    """Subsetting must not mutate the original GeoJSON."""
    original_len = len(sample_geojson["features"])
    _ = subset_geojson(sample_geojson, {"Alpha"})
    assert len(sample_geojson["features"]) == original_len


# ── simplify_geojson ──────────────────────────────────────────────────────────

def _vertex_count(geojson: dict) -> int:
    total = 0
    for f in geojson["features"]:
        coords = f["geometry"]["coordinates"][0]
        total += len(coords)
    return total


def test_simplify_reduces_vertex_count(sample_geojson):
    before = _vertex_count(sample_geojson)
    simplified = simplify_geojson(sample_geojson, tolerance=0.5)
    after = _vertex_count(simplified)
    assert after < before, f"expected simplification, got {before} -> {after}"


def test_simplify_preserves_feature_count(sample_geojson):
    out = simplify_geojson(sample_geojson, tolerance=0.5)
    assert len(out["features"]) == len(sample_geojson["features"])


def test_simplify_preserves_shape_names(sample_geojson):
    out = simplify_geojson(sample_geojson, tolerance=0.5)
    names = [f["properties"]["shapeName"] for f in out["features"]]
    assert names == ["Alpha", "Beta", "Gamma"]


def test_simplify_keeps_square_as_quadrilateral(sample_geojson):
    """A square with collinear perimeter points simplifies to ~4 corners."""
    out = simplify_geojson(sample_geojson, tolerance=0.01)
    for f in out["features"]:
        vertices = f["geometry"]["coordinates"][0]
        # Perfect square → 4 corners + 1 closing point = 5 vertices.
        # Allow 4–8 to accommodate shapely quirks across versions.
        assert 4 <= len(vertices) <= 8


def test_simplify_handles_missing_geometry():
    gj = {"features": [
        {"properties": {"shapeName": "NoGeom"}, "geometry": None},
        {"properties": {"shapeName": "Good"}, "geometry": _square(0, 0)},
    ]}
    out = simplify_geojson(gj, tolerance=0.5)
    assert len(out["features"]) == 2


# ── GeoFetchError semantics ───────────────────────────────────────────────────

def test_geofetcherror_carries_reason():
    err = GeoFetchError("boom", reason="timeout")
    assert err.reason == "timeout"
    assert str(err) == "boom"


def test_fetch_raises_timeout_when_requests_times_out(monkeypatch):
    """Network timeout must be surfaced as GeoFetchError(reason='timeout')."""
    def fake_get(*a, **kw):
        raise requests.Timeout("simulated")

    monkeypatch.setattr("src.geo._session.get", fake_get)
    # Bypass streamlit cache so monkeypatch isn't shadowed by a cached result.
    fetch = getattr(fetch_admin_geojson, "__wrapped__", fetch_admin_geojson)

    with pytest.raises(GeoFetchError) as excinfo:
        fetch("FRA", 1)
    assert excinfo.value.reason == "timeout"


def test_fetch_raises_unavailable_when_metadata_has_no_url(monkeypatch):
    class _R:
        def json(self):
            return {}
    monkeypatch.setattr("src.geo._session.get", lambda *a, **kw: _R())
    fetch = getattr(fetch_admin_geojson, "__wrapped__", fetch_admin_geojson)

    with pytest.raises(GeoFetchError) as excinfo:
        fetch("XYZ", 2)
    assert excinfo.value.reason == "unavailable"
