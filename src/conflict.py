"""
Conflict-event data loaders.

Two public-interest sources are supported:

  * **UCDP GED** — Uppsala Conflict Data Program Georeferenced Event
    Dataset, via the public `ucdpapi.pcr.uu.se` API (no key required).
    Returns an event-level frame with `date, country, best (deaths),
    lat, lon, type_of_violence`.

  * **HDX (Humanitarian Data Exchange)** — generic CSV URL paste. The
    user copies any CSV resource link from `data.humdata.org` and we
    fetch/parse it. No auth; CKAN exposes direct CSV links.

Typical usage in the Streamlit UI:

    events = fetch_ucdp(country="Nigeria", year_from=2015, year_to=2023)
    df = fetch_hdx_csv("https://data.humdata.org/.../some.csv")
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from .http import session as _session

# ── Errors ────────────────────────────────────────────────────────────────────

class ConflictFetchError(RuntimeError):
    """Raised when a conflict-data request cannot be completed."""

    def __init__(self, message: str, *, reason: str = "error"):
        super().__init__(message)
        self.reason = reason


# ── UCDP GED ──────────────────────────────────────────────────────────────────

# The public UCDP API. `version` changes once a year; 24.1 is the 2024 release.
_UCDP_URL = "https://ucdpapi.pcr.uu.se/api/gedevents/24.1"


@dataclass
class UcdpResult:
    df: pd.DataFrame
    snapshot: datetime

    @property
    def snapshot_str(self) -> str:
        return self.snapshot.strftime("%Y-%m-%d %H:%M UTC")


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_ucdp(country: str | None = None,
               year_from: int | None = None,
               year_to: int | None = None,
               pagesize: int = 1000,
               max_pages: int = 20) -> UcdpResult:
    """
    Fetch UCDP GED events with optional country / year filters.

    Paginates up to `max_pages` × `pagesize` rows (20 × 1000 = 20 000 by
    default; enough for any single country across all years, and safe for
    a free public API).
    """
    records: list[dict] = []
    params: dict[str, str] = {"pagesize": str(pagesize)}
    if country:
        params["Country"] = country
    if year_from is not None:
        params["StartDate"] = f"{year_from}-01-01"
    if year_to is not None:
        params["EndDate"] = f"{year_to}-12-31"

    next_url: str | None = _UCDP_URL
    page = 0
    while next_url and page < max_pages:
        try:
            r = _session.get(next_url, params=params if page == 0 else None, timeout=60)
            r.raise_for_status()
            body = r.json()
        except requests.Timeout as e:
            raise ConflictFetchError("UCDP request timed out.", reason="timeout") from e
        except requests.RequestException as e:
            raise ConflictFetchError(f"UCDP HTTP error: {e}", reason="http") from e
        except ValueError as e:
            raise ConflictFetchError(f"UCDP parse error: {e}", reason="parse") from e

        page_records = body.get("Result") or body.get("result") or []
        records.extend(page_records)
        next_url = body.get("NextPageUrl") or body.get("NextPage") or None
        if not page_records:
            break
        page += 1

    if not records:
        raise ConflictFetchError(
            "UCDP returned no events for the given filters.",
            reason="empty",
        )

    df = pd.DataFrame(records)
    # Normalise the handful of columns we surface in the UI.
    keep = [
        "date_start", "date_end", "country", "region",
        "best", "low", "high",
        "type_of_violence", "conflict_name",
        "latitude", "longitude", "year",
    ]
    present = [c for c in keep if c in df.columns]
    df = df[present].copy()
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    for c in ("best", "low", "high", "latitude", "longitude"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return UcdpResult(df=df, snapshot=datetime.now(timezone.utc))


# ── HDX CSV paste ─────────────────────────────────────────────────────────────

def _looks_like_csv_url(url: str) -> bool:
    """Heuristic check — HDX exposes CKAN resource URLs that usually end with .csv
    or contain `/download/`. We keep this permissive so the user can paste
    slightly non-standard links."""
    lowered = url.lower()
    return (
        lowered.startswith("http://") or lowered.startswith("https://")
    ) and ("hdx" in lowered or "humdata" in lowered or lowered.endswith(".csv"))


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_hdx_csv(url: str) -> pd.DataFrame:
    """
    Fetch a CSV resource from data.humdata.org (or any public CSV URL).

    Returns the raw DataFrame as parsed by pandas. The caller is
    responsible for picking the right country / value / year columns.
    """
    if not _looks_like_csv_url(url):
        raise ConflictFetchError(
            "This doesn't look like an HDX CSV URL. Paste a direct link to a "
            ".csv resource from data.humdata.org.",
            reason="invalid_url",
        )
    try:
        r = _session.get(url, timeout=60)
        r.raise_for_status()
    except requests.Timeout as e:
        raise ConflictFetchError("HDX request timed out.", reason="timeout") from e
    except requests.RequestException as e:
        raise ConflictFetchError(f"HDX HTTP error: {e}", reason="http") from e

    try:
        # HDX sometimes serves UTF-8-BOM or latin-1 files.
        return pd.read_csv(io.BytesIO(r.content), encoding_errors="replace")
    except (pd.errors.ParserError, ValueError) as e:
        raise ConflictFetchError(f"HDX CSV parse error: {e}", reason="parse") from e
