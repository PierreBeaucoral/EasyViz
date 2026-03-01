"""
Data fetching from Our World in Data (OWID) and World Bank (WDI).
Results are cached for 1 hour to avoid repeated network calls.
"""

import io

import pandas as pd
import requests
import streamlit as st

_WB_API = (
    "https://api.worldbank.org/v2/country/all/indicator/{code}"
    "?format=json&date=1960:2024&per_page=20000&page={page}"
)

# Shared headers — prevents blocks on Streamlit Cloud
_HEADERS = {
    "User-Agent": "DevViz/1.0 (https://github.com/devviz; educational use)",
    "Accept": "text/csv,application/json",
}

# World Bank aggregate codes — excluded from country lists
_WB_AGGREGATES = {
    "AFE", "AFW", "ARB", "CAA", "CEB", "CSS", "EAP", "EAR", "EAS", "ECA",
    "ECS", "EMU", "EUU", "FCS", "HIC", "HPC", "IBD", "IBT", "IDA", "IDX",
    "LAC", "LCN", "LDC", "LIC", "LMC", "LMY", "MEA", "MIC", "MNA", "NAC",
    "OEC", "OSS", "PRE", "PSS", "PST", "SAR", "SAS", "SSA", "SSF", "SST",
    "TEA", "TEC", "TLA", "TMN", "TSA", "TSS", "UMC", "WLD",
}


def fetch_data(indicator: dict) -> pd.DataFrame | None:
    """Route fetch to the correct source based on indicator config."""
    if indicator["source"] == "owid":
        return _fetch_owid(indicator["slug"])
    if indicator["source"] == "wdi":
        return _fetch_wdi(indicator["indicator"])
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_owid(slug: str) -> pd.DataFrame | None:
    """Download an OWID CSV via requests (with User-Agent) and normalise columns."""
    url = f"https://ourworldindata.org/grapher/{slug}.csv"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))

        value_cols = [c for c in df.columns if c not in ("Entity", "Code", "Year")]
        if not value_cols:
            return None

        value_col = value_cols[0]
        df = df.rename(columns={
            "Entity": "entity",
            "Code": "iso3",
            "Year": "year",
            value_col: "value",
        })[["entity", "iso3", "year", "value"]]
        df["year"]  = pd.to_numeric(df["year"],  errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna(subset=["year", "value"]).astype({"year": int})
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_wdi(code: str) -> pd.DataFrame | None:
    """Fetch a WDI indicator from the World Bank API (handles pagination)."""
    records = []
    page = 1
    try:
        while True:
            r = requests.get(
                _WB_API.format(code=code, page=page),
                headers=_HEADERS,
                timeout=60,   # WB API can be slow for large indicators
            )
            r.raise_for_status()
            resp = r.json()
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
            if meta["page"] >= meta["pages"]:
                break
            page += 1
    except Exception:
        return None

    if not records:
        return None
    return pd.DataFrame(records)
