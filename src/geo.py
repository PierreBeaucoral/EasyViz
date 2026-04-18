"""
Sub-national boundary data from geoBoundaries (https://www.geoboundaries.org).

Provides:
  - `fetch_admin_geojson`  — cached GeoJSON download with typed errors
  - `subset_geojson`       — keep only features matching a region set
  - `simplify_geojson`     — Douglas-Peucker simplification (shapely)
  - `get_region_names`     — list of shapeName strings in a GeoJSON
  - `match_regions`        — fuzzy match user names to shapeName values

The subset + simplify step is what makes ADM2 for large countries
usable in a browser: raw geoBoundaries payloads can be 50–100 MB and
thousands of polygons, which Plotly cannot render interactively.
"""

from __future__ import annotations

import requests
import streamlit as st
from rapidfuzz import fuzz, process

# ── Constants ─────────────────────────────────────────────────────────────────

_GB_API = "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM{level}/"
_HEADERS = {"User-Agent": "EasyViz/1.0 (educational use)"}

# The property used by geoBoundaries for region names.
NAME_PROP = "shapeName"


# ── Errors ────────────────────────────────────────────────────────────────────

class GeoFetchError(RuntimeError):
    """
    Raised by `fetch_admin_geojson` when the geoBoundaries request fails.

    `reason` is one of {"timeout", "http", "parse", "unavailable"} — the
    caller can use it to tailor the user-facing message (e.g. suggest
    ADM1 when an ADM2 download times out).
    """

    def __init__(self, message: str, *, reason: str):
        super().__init__(message)
        self.reason = reason


# ── Fetch ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_admin_geojson(iso3: str, level: int = 1) -> dict:
    """Download ADM-level GeoJSON from geoBoundaries.

    Raises:
        GeoFetchError: on timeout, HTTP error, parse error, or missing level.
    """
    meta_url = _GB_API.format(iso3=iso3.upper(), level=level)

    try:
        meta = requests.get(meta_url, headers=_HEADERS, timeout=20).json()
    except requests.Timeout as e:
        raise GeoFetchError(
            f"geoBoundaries metadata request timed out for {iso3} ADM{level}",
            reason="timeout",
        ) from e
    except requests.RequestException as e:
        raise GeoFetchError(f"geoBoundaries HTTP error: {e}", reason="http") from e
    except ValueError as e:
        raise GeoFetchError(
            f"geoBoundaries metadata is not valid JSON: {e}", reason="parse",
        ) from e

    dl_url = meta.get("gjDownloadURL") or meta.get("downloadURL")
    if not dl_url:
        raise GeoFetchError(
            f"geoBoundaries has no ADM{level} dataset for {iso3}",
            reason="unavailable",
        )

    # Large ADM2 payloads can be 50–100 MB → generous timeout + streaming read.
    try:
        r = requests.get(dl_url, headers=_HEADERS, timeout=180)
        r.raise_for_status()
        return r.json()
    except requests.Timeout as e:
        raise GeoFetchError(
            "geoBoundaries download timed out. ADM2 files for large countries "
            "are very heavy — try ADM1 first, or a smaller country.",
            reason="timeout",
        ) from e
    except requests.RequestException as e:
        raise GeoFetchError(
            f"geoBoundaries download HTTP error: {e}", reason="http",
        ) from e
    except ValueError as e:
        raise GeoFetchError(f"GeoJSON parse error: {e}", reason="parse") from e


# ── Subsetting ────────────────────────────────────────────────────────────────

def subset_geojson(geojson: dict, region_names: list[str] | set[str]) -> dict:
    """
    Return a GeoJSON with only features whose shapeName is in `region_names`.

    If `region_names` is empty, returns the original GeoJSON unchanged
    (so a caller that hasn't matched yet still gets a valid map to show).
    """
    if not region_names:
        return geojson
    keep = set(region_names)
    features = [
        f for f in geojson.get("features", [])
        if f.get("properties", {}).get(NAME_PROP) in keep
    ]
    return {**geojson, "features": features}


# ── Simplification ────────────────────────────────────────────────────────────

def simplify_geojson(geojson: dict, tolerance: float = 0.01) -> dict:
    """
    Douglas-Peucker simplify every feature's geometry.

    `tolerance` is in CRS units — for WGS84 lon/lat, 0.01° ≈ 1 km at the
    equator, which is imperceptible at national zoom but typically
    reduces the payload 5–20×.

    If shapely is not installed, falls back to the unsimplified GeoJSON
    so the map still works.
    """
    try:
        from shapely.geometry import mapping, shape
    except ImportError:
        return geojson

    out_features = []
    for feat in geojson.get("features", []):
        geom = feat.get("geometry")
        if not geom:
            out_features.append(feat)
            continue
        try:
            simplified = shape(geom).simplify(tolerance, preserve_topology=True)
            out_features.append({**feat, "geometry": mapping(simplified)})
        except (TypeError, ValueError):
            # Malformed geometry — keep the original rather than drop it.
            out_features.append(feat)
    return {**geojson, "features": out_features}


# ── Region-name helpers ───────────────────────────────────────────────────────

def get_region_names(geojson: dict) -> list[str]:
    """Return sorted unique shapeName values from GeoJSON features."""
    names = []
    for feat in geojson.get("features", []):
        name = feat.get("properties", {}).get(NAME_PROP, "")
        if name:
            names.append(name)
    return sorted(set(names))


def match_regions(
    user_regions: list[str],
    geojson_names: list[str],
    threshold: int = 72,
) -> dict[str, str | None]:
    """Fuzzy-match user region names to geoBoundaries shapeName values.

    Returns `{user_name: matched_shapeName or None}`.
    """
    mapping = {}
    for name in user_regions:
        result = process.extractOne(
            name,
            geojson_names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold,
        )
        mapping[name] = result[0] if result else None
    return mapping
