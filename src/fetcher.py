"""
Data fetching from Our World in Data (OWID) and World Bank (WDI).

Results are cached for 1 hour to avoid repeated network calls within a
session. Every fetch now returns both the long-format DataFrame *and*
the UTC snapshot timestamp at which the data was retrieved, so the
citation panel and exported scripts can pin reproducibility.

Errors are typed (RequestException, ValueError) so the caller can
distinguish a transient network failure from a malformed response
and report it to the user instead of silently returning None.
"""

from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from . import diskcache
from .http import session as _session

# ── Constants ─────────────────────────────────────────────────────────────────

_WB_API = (
    "https://api.worldbank.org/v2/country/all/indicator/{code}"
    "?format=json&date=1960:{end}&per_page=20000&page={page}"
)

_HEADERS = {
    "User-Agent": "EasyViz/0.2 (+https://github.com/PierreBeaucoral/EasyViz)",
    "Accept": "text/csv,application/json",
}

# World Bank aggregate ISO codes — always excluded from country panels.
_WB_AGGREGATES: frozenset[str] = frozenset({
    "AFE", "AFW", "ARB", "CAA", "CEB", "CSS", "EAP", "EAR", "EAS", "ECA",
    "ECS", "EMU", "EUU", "FCS", "HIC", "HPC", "IBD", "IBT", "IDA", "IDX",
    "LAC", "LCN", "LDC", "LIC", "LMC", "LMY", "MEA", "MIC", "MNA", "NAC",
    "OEC", "OSS", "PRE", "PSS", "PST", "SAR", "SAS", "SSA", "SSF", "SST",
    "TEA", "TEC", "TLA", "TMN", "TSA", "TSS", "UMC", "WLD",
})

# Most-recent year we allow the WDI fetcher to request. WB data typically
# lags 1–2 years, so requesting 2030 is harmless and means we never need to
# ship a new release just to pick up this year's update.
_WB_END_YEAR = datetime.now(timezone.utc).year + 1


# ── Public types ──────────────────────────────────────────────────────────────

class FetchError(RuntimeError):
    """Raised when an indicator cannot be fetched for a specific reason."""


@dataclass
class FetchResult:
    """A fetched indicator plus the fetch timestamp (UTC)."""
    df: pd.DataFrame
    snapshot: datetime

    @property
    def snapshot_str(self) -> str:
        return self.snapshot.strftime("%Y-%m-%d %H:%M UTC")


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_data(indicator: dict) -> FetchResult:
    """
    Route fetch to the correct source and return (df, snapshot).

    Raises:
        FetchError: when the indicator cannot be retrieved at all.
    """
    src = indicator["source"]
    if src == "owid":
        return _fetch_owid(indicator["slug"])
    if src == "wdi":
        return _fetch_wdi(indicator["indicator"])
    raise FetchError(f"Unknown source: {src!r}")


def fetch_many(indicators: list[dict], max_workers: int = 5) -> dict[str, FetchResult]:
    """
    Fetch several indicators in parallel. Returns {indicator_id: FetchResult}
    for each successful fetch; failures are silently skipped (the caller
    decides how to surface "missing" indicators, typically by showing a
    warning listing the ids that didn't come back).
    """
    out: dict[str, FetchResult] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_id = {ex.submit(fetch_data, ind): ind["id"] for ind in indicators}
        for fut in as_completed(future_to_id):
            ind_id = future_to_id[fut]
            try:
                out[ind_id] = fut.result()
            except FetchError:
                continue
    return out


# ── OWID ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_owid(slug: str) -> FetchResult:
    """Fetch an OWID grapher CSV (disk-cache first, network on miss)."""
    cached = diskcache.load("owid", slug)
    if cached is not None:
        df_cached, snap = cached
        return FetchResult(df=df_cached, snapshot=snap)

    url = f"https://ourworldindata.org/grapher/{slug}.csv"
    try:
        r = _session.get(url, headers=_HEADERS, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise FetchError(f"OWID network error for {slug!r}: {e}") from e

    try:
        df = pd.read_csv(io.StringIO(r.text))
    except (pd.errors.ParserError, ValueError) as e:
        raise FetchError(f"OWID parse error for {slug!r}: {e}") from e

    value_cols = [c for c in df.columns if c not in ("Entity", "Code", "Year")]
    if not value_cols:
        raise FetchError(f"OWID response for {slug!r} had no value column.")

    value_col = value_cols[0]
    df = df.rename(columns={
        "Entity": "entity",
        "Code":   "iso3",
        "Year":   "year",
        value_col: "value",
    })[["entity", "iso3", "year", "value"]]
    df["year"]  = pd.to_numeric(df["year"],  errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["year", "value"]).astype({"year": int})

    snapshot = datetime.now(timezone.utc)
    diskcache.save("owid", slug, df, snapshot)
    return FetchResult(df=df, snapshot=snapshot)


# ── WDI ───────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_wdi(code: str) -> FetchResult:
    """Fetch a WDI indicator from the World Bank API, handling pagination."""
    cached = diskcache.load("wdi", code)
    if cached is not None:
        df_cached, snap = cached
        return FetchResult(df=df_cached, snapshot=snap)

    records: list[dict] = []
    page = 1

    while True:
        try:
            r = _session.get(
                _WB_API.format(code=code, end=_WB_END_YEAR, page=page),
                headers=_HEADERS,
                timeout=60,
            )
            r.raise_for_status()
            resp = r.json()
        except requests.RequestException as e:
            raise FetchError(f"WB API network error for {code!r}: {e}") from e
        except ValueError as e:  # JSON decode
            raise FetchError(f"WB API returned non-JSON for {code!r}: {e}") from e

        if not resp or len(resp) < 2 or resp[1] is None:
            break

        meta, data = resp[0], resp[1]
        for rec in data:
            iso3 = rec.get("countryiso3code", "")
            if rec.get("value") is None or iso3 in _WB_AGGREGATES:
                continue
            records.append({
                "entity": rec["country"]["value"],
                "iso3":   iso3,
                "year":   int(rec["date"]),
                "value":  float(rec["value"]),
            })

        if meta.get("page", 1) >= meta.get("pages", 1):
            break
        page += 1

    if not records:
        raise FetchError(
            f"WB API returned no rows for {code!r}. Common causes: "
            "the indicator was retired, the code is wrong, "
            "or the series is aggregate-only."
        )

    df = pd.DataFrame(records)
    snapshot = datetime.now(timezone.utc)
    diskcache.save("wdi", code, df, snapshot)
    return FetchResult(df=df, snapshot=snapshot)
