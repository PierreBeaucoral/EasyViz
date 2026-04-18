"""
Full World Bank WDI taxonomy importer.

The curated `catalog.INDICATORS` list is deliberately small (a few dozen
hand-picked series with clean tags). For users who know what they want,
or for exploratory analysis, this module provides access to the complete
~1,500 WDI indicators keyed by the authoritative WB metadata endpoint.

Design:
  * One cached network call per day populates a local parquet file.
  * `load_all()` returns a list of `{id, name, category, source, indicator,
    unit, tags}` dicts that plug straight into the existing search /
    catalog rendering pipelines.
  * Failures are non-fatal: if the WB endpoint is down we return the
    cached copy (even if stale) or an empty list.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests
import streamlit as st

from .diskcache import _cache_dir
from .http import session as _session

_WB_ALL_URL = "https://api.worldbank.org/v2/indicator?format=json&per_page=25000&page=1"
_TAXONOMY_FILE = "wdi_taxonomy.json"


def _taxonomy_path() -> Path:
    return _cache_dir() / _TAXONOMY_FILE


def _slugify(code: str) -> str:
    return "wdi_" + code.lower().replace(".", "_")


def _normalise(raw_record: dict) -> dict | None:
    """Convert one WB metadata record to an EasyViz indicator dict."""
    code = raw_record.get("id")
    name = raw_record.get("name")
    if not code or not name:
        return None
    topics = raw_record.get("topics") or []
    # Topic is a list of {id, value}; first one is primary.
    category = (topics[0].get("value") if topics else "") or "Other"
    source = raw_record.get("source", {}) or {}
    unit = source.get("value", "") or ""
    tags = [w.lower() for w in name.split() if len(w) > 3]
    return {
        "id":        _slugify(code),
        "name":      name,
        "category":  category.strip() or "Other",
        "source":    "wdi",
        "indicator": code,
        "unit":      unit,
        "tags":      tags,
    }


def _fetch_from_api() -> list[dict]:
    try:
        r = _session.get(_WB_ALL_URL, timeout=60)
        r.raise_for_status()
        body = r.json()
    except (requests.RequestException, ValueError):
        return []

    if not body or len(body) < 2 or not body[1]:
        return []

    records = []
    for raw in body[1]:
        norm = _normalise(raw)
        if norm is not None:
            records.append(norm)
    return records


def refresh(force: bool = False) -> list[dict]:
    """
    Download the full taxonomy and cache it. Returns the fresh list.

    If the network call fails and a cached copy exists, returns that
    instead (stale but usable). If both fail, returns an empty list.
    """
    path = _taxonomy_path()
    records = _fetch_from_api()
    if records:
        path.write_text(json.dumps({
            "fetched": datetime.now(timezone.utc).isoformat(),
            "records": records,
        }))
        return records
    # Fallback to cache if present.
    if path.exists():
        try:
            return json.loads(path.read_text()).get("records", [])
        except (OSError, json.JSONDecodeError):
            return []
    return []


@st.cache_data(ttl=86400, show_spinner=False)
def load_all() -> list[dict]:
    """
    Return the full WDI taxonomy, using the on-disk cache when fresh.

    Refreshes automatically if the disk copy is older than 24 h.
    """
    path = _taxonomy_path()
    if path.exists():
        try:
            body = json.loads(path.read_text())
            fetched = datetime.fromisoformat(body["fetched"])
            age_s = (datetime.now(timezone.utc) - fetched).total_seconds()
            if age_s < 86400:
                return body.get("records", [])
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            pass
    return refresh()
