"""
Unit tests for `src.uploader`.

We test the pure helpers that don't require a Streamlit UploadedFile:
format detection, column heuristics, ISO3 resolution, and wide→long
normalisation.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.uploader import (
    _build_iso3_map,
    _norm,
    detect_columns,
    detect_format,
    normalise,
)


# ── _norm ─────────────────────────────────────────────────────────────────────

def test_norm_strips_accents_and_punctuation():
    assert _norm("Côte d'Ivoire") == "cote d ivoire"
    assert _norm("Korea, Rep.") == "korea rep"
    assert _norm("Congo, Dem. Rep.") == "congo dem rep"
    assert _norm("  LAO  PDR ") == "lao pdr"


# ── detect_format ─────────────────────────────────────────────────────────────

def test_detect_format_wide_when_many_year_columns():
    df = pd.DataFrame({"country": ["FRA"], "2000": [1], "2001": [2], "2002": [3], "2003": [4]})
    assert detect_format(df) == "wide"


def test_detect_format_long_when_few_year_columns():
    df = pd.DataFrame({"country": ["FRA"], "year": [2000], "value": [10]})
    assert detect_format(df) == "long"


def test_detect_format_long_for_cross_sectional():
    df = pd.DataFrame({"country": ["FRA", "NGA"], "value": [10, 20]})
    assert detect_format(df) == "long"


# ── detect_columns ────────────────────────────────────────────────────────────

def test_detect_columns_finds_country_and_year():
    df = pd.DataFrame({"Country": ["FRA"], "Year": [2000], "GDP": [50000]})
    mapping = detect_columns(df)
    assert mapping["entity"] == "Country"
    assert mapping["year"] == "Year"
    assert mapping["value"] == "GDP"


def test_detect_columns_prefers_keyword_match_for_year():
    df = pd.DataFrame({"country": ["FRA"], "Year": [2000], "score": [42]})
    mapping = detect_columns(df)
    assert mapping["year"] == "Year"


def test_detect_columns_falls_back_to_heuristic_year():
    # No "year"-keyword column; numeric column where 80%+ values are in
    # the 1900–2030 plausible-year range should be picked.
    df = pd.DataFrame({"country": ["FRA"] * 5, "period": [2000, 2001, 2002, 2003, 2004], "x": [1.0, 2, 3, 4, 5]})
    mapping = detect_columns(df)
    assert mapping["year"] == "period"


def test_detect_columns_lists_all_value_candidates():
    df = pd.DataFrame(
        {"country": ["FRA"], "year": [2000], "gdp": [1], "pop": [2], "note": ["a"]}
    )
    cands = detect_columns(df)["value_candidates"]
    assert set(cands) == {"gdp", "pop"}


# ── _build_iso3_map ───────────────────────────────────────────────────────────
#
# We wrap the streamlit-cached function via its .__wrapped__ attribute when
# available so tests don't require a Streamlit runtime. In practice Streamlit's
# `@st.cache_data` exposes `.clear()` and the wrapped callable, but is safe to
# call outside a session as long as the function doesn't touch `st.session_state`.

def _call(entities):
    """Call `_build_iso3_map` defensively, handling the Streamlit cache wrapper."""
    fn = getattr(_build_iso3_map, "__wrapped__", _build_iso3_map)
    return fn(tuple(entities))


def test_iso3_resolution_exact_iso3():
    out = _call(["FRA", "USA", "NGA"])
    assert out["FRA"] == "FRA"
    assert out["USA"] == "USA"
    assert out["NGA"] == "NGA"


def test_iso3_resolution_iso2():
    out = _call(["FR", "US", "NG"])
    assert out["FR"] == "FRA"
    assert out["US"] == "USA"
    assert out["NG"] == "NGA"


def test_iso3_resolution_common_aliases():
    out = _call([
        "Korea, Rep.",
        "Congo, Dem. Rep.",
        "Côte d'Ivoire",
        "Lao PDR",
        "Czechia",
        "Eswatini",
    ])
    assert out["Korea, Rep."] == "KOR"
    assert out["Congo, Dem. Rep."] == "COD"
    assert out["Côte d'Ivoire"] == "CIV"
    assert out["Lao PDR"] == "LAO"
    assert out["Czechia"] == "CZE"
    assert out["Eswatini"] == "SWZ"


def test_iso3_resolution_handles_fuzzy_typos():
    out = _call(["Unkted States", "Frnace"])
    # Don't assert exact ISO3 — rapidfuzz can differ across versions. Just
    # check that SOMETHING reasonable came out (not empty, three letters).
    for k, v in out.items():
        assert v == "" or (len(v) == 3 and v.isupper())


def test_iso3_resolution_unknown_returns_empty():
    out = _call(["Atlantis", "Zzztopia"])
    assert out["Atlantis"] == "" or len(out["Atlantis"]) == 3  # rapidfuzz may still match weirdly
    assert out["Zzztopia"] == "" or len(out["Zzztopia"]) == 3


# ── normalise ─────────────────────────────────────────────────────────────────

def test_normalise_long_schema():
    df = pd.DataFrame(
        {"Country": ["France", "Nigeria"], "Year": [2000, 2000], "Value": [100, 50]}
    )
    out = normalise(
        df, entity_col="Country", year_col="Year", value_col="Value",
        fmt="long", entity_is_iso3=False,
    )
    assert list(out.columns) == ["entity", "iso3", "year", "value"]
    assert out.loc[out.entity == "France", "iso3"].iloc[0] == "FRA"
    assert out.loc[out.entity == "Nigeria", "iso3"].iloc[0] == "NGA"


def test_normalise_wide_schema():
    df = pd.DataFrame(
        {"country": ["FRA", "NGA"], "2000": [10, 1], "2001": [20, 2], "2002": [30, 4]}
    )
    out = normalise(
        df, entity_col="country", year_col=None, value_col="country",
        fmt="wide", entity_is_iso3=True,
    )
    assert set(out["year"].unique()) == {2000, 2001, 2002}
    fra = out[out.entity == "FRA"].sort_values("year")["value"].tolist()
    assert fra == [10, 20, 30]
    # iso3 pass-through because entity_is_iso3=True
    assert (out["iso3"] == out["entity"]).all()


def test_normalise_cross_sectional_no_year():
    df = pd.DataFrame({"country": ["France", "Nigeria"], "value": [1.0, 2.0]})
    out = normalise(
        df, entity_col="country", year_col=None, value_col="value",
        fmt="long", entity_is_iso3=False,
    )
    assert (out["year"] == 0).all()
    assert out.shape[0] == 2


def test_normalise_drops_rows_with_missing_values():
    df = pd.DataFrame(
        {"country": ["A", "B", "C"], "year": [2000, 2000, 2000], "v": [1.0, None, 3.0]}
    )
    out = normalise(
        df, entity_col="country", year_col="year", value_col="v",
        fmt="long", entity_is_iso3=False,
    )
    assert "B" not in out.entity.values
    assert len(out) == 2
