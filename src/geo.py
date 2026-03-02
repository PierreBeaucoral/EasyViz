"""
Sub-national boundary data from geoBoundaries (https://www.geoboundaries.org).
Provides GeoJSON download and fuzzy region-name matching.
"""

import requests
import streamlit as st
from rapidfuzz import fuzz, process

# geoBoundaries REST API — free, no key required
_GB_API = "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM{level}/"
_HEADERS = {"User-Agent": "DevViz/1.0 (educational use)"}

# The property used by geoBoundaries for region names
NAME_PROP = "shapeName"


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_admin_geojson(iso3: str, level: int = 1) -> dict | None:
    """Download ADM-level GeoJSON for a country via the geoBoundaries API.

    Returns the parsed GeoJSON dict, or None on failure.
    """
    try:
        meta_url = _GB_API.format(iso3=iso3.upper(), level=level)
        meta = requests.get(meta_url, headers=_HEADERS, timeout=20).json()
        dl_url = meta.get("gjDownloadURL") or meta.get("downloadURL")
        if not dl_url:
            return None
        gj = requests.get(dl_url, headers=_HEADERS, timeout=90).json()
        return gj
    except Exception:
        return None


def get_region_names(geojson: dict) -> list[str]:
    """Return sorted list of shapeName values from GeoJSON features."""
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
    """Fuzzy-match user region names against geoBoundaries shapeName values.

    Returns {user_name: matched_shapeName or None}.
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
