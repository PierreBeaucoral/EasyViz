"""
Unit tests for `src.transforms`.

These are pure numerical functions — no IO, no Streamlit. We verify
semantics, edge cases (single-country series, zero first-year value,
partial NaNs), and unit-label propagation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.transforms import (
    AGG_CHOICES,
    TRANSFORM_CHOICES,
    aggregate_period,
    apply_transform,
    log1p_positive,
    period_label,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def toy_long() -> pd.DataFrame:
    """
    Two countries, four years, monotonic values — easy to reason about.

        entity       year   value
        France       2000   10
        France       2001   20
        France       2002   30
        France       2003   40
        Nigeria      2000    1
        Nigeria      2001    2
        Nigeria      2002    4
        Nigeria      2003    8
    """
    return pd.DataFrame(
        {
            "entity": ["France"] * 4 + ["Nigeria"] * 4,
            "iso3":   ["FRA"] * 4 + ["NGA"] * 4,
            "year":   list(range(2000, 2004)) * 2,
            "value":  [10, 20, 30, 40, 1, 2, 4, 8],
        }
    )


# ── apply_transform ───────────────────────────────────────────────────────────

def test_transform_none_is_passthrough(toy_long):
    out, unit = apply_transform(toy_long, "None", "usd")
    pd.testing.assert_frame_equal(
        out.reset_index(drop=True),
        toy_long.reset_index(drop=True),
    )
    assert unit == "usd"


def test_transform_pct_of_max(toy_long):
    out, unit = apply_transform(toy_long, "% of max (normalize 0–100)", "usd")
    assert unit == "% of max"
    # Max was 40 (France 2003) → becomes 100.
    assert out.loc[(out.entity == "France") & (out.year == 2003), "value"].iloc[0] == pytest.approx(100.0)
    # Nigeria 2000 had value 1 → should now be 2.5.
    assert out.loc[(out.entity == "Nigeria") & (out.year == 2000), "value"].iloc[0] == pytest.approx(2.5)


def test_transform_pct_change_vs_first_year(toy_long):
    out, unit = apply_transform(toy_long, "% change vs first year", "usd")
    assert unit == "% change vs first year"
    # France: (10, 20, 30, 40) baseline 10 → (0, 100, 200, 300)
    fra = out[out.entity == "France"].sort_values("year")["value"].tolist()
    assert fra == pytest.approx([0.0, 100.0, 200.0, 300.0])
    # Nigeria baseline 1 → (0, 100, 300, 700)
    nga = out[out.entity == "Nigeria"].sort_values("year")["value"].tolist()
    assert nga == pytest.approx([0.0, 100.0, 300.0, 700.0])


def test_transform_pct_change_zero_first_year_produces_nan():
    df = pd.DataFrame(
        {"entity": ["A", "A", "A"], "iso3": ["AAA"] * 3, "year": [2000, 2001, 2002], "value": [0, 5, 10]}
    )
    out, _ = apply_transform(df, "% change vs first year", "unit")
    assert out["value"].isna().all()


def test_transform_cumulative_sum(toy_long):
    out, unit = apply_transform(toy_long, "Cumulative sum", "tonnes")
    assert unit == "cumulative tonnes"
    fra = out[out.entity == "France"].sort_values("year")["value"].tolist()
    assert fra == [10, 30, 60, 100]
    nga = out[out.entity == "Nigeria"].sort_values("year")["value"].tolist()
    assert nga == [1, 3, 7, 15]


def test_transform_rolling_avg_3yr(toy_long):
    out, unit = apply_transform(toy_long, "Rolling avg (3 yr)", "pct")
    assert unit == "3-yr avg pct"
    fra = out[out.entity == "France"].sort_values("year")["value"].tolist()
    # (10), (10+20)/2=15, (10+20+30)/3=20, (20+30+40)/3=30
    assert fra == pytest.approx([10.0, 15.0, 20.0, 30.0])


def test_transform_rank(toy_long):
    out, unit = apply_transform(toy_long, "Rank (1 = highest)", "usd")
    assert unit == "rank"
    # In 2000, France (10) > Nigeria (1) → France rank 1, Nigeria rank 2.
    for y in range(2000, 2004):
        fra_rank = out[(out.entity == "France") & (out.year == y)]["value"].iloc[0]
        nga_rank = out[(out.entity == "Nigeria") & (out.year == y)]["value"].iloc[0]
        assert fra_rank == 1
        assert nga_rank == 2


def test_transform_unknown_is_passthrough(toy_long):
    out, unit = apply_transform(toy_long, "nonexistent transform", "usd")
    assert unit == "usd"
    assert len(out) == len(toy_long)


def test_all_transform_choices_are_executable(toy_long):
    """Every UI-exposed label must run without error on well-formed data."""
    for choice in TRANSFORM_CHOICES:
        out, _ = apply_transform(toy_long, choice, "usd")
        assert isinstance(out, pd.DataFrame)


# ── aggregate_period ──────────────────────────────────────────────────────────

def test_aggregate_period_mean(toy_long):
    out = aggregate_period(toy_long, "Mean")
    assert set(out.columns) == {"entity", "iso3", "value"}
    fra = out[out.entity == "France"]["value"].iloc[0]
    assert fra == pytest.approx(25.0)  # mean(10, 20, 30, 40)


def test_aggregate_period_sum(toy_long):
    out = aggregate_period(toy_long, "Sum")
    assert out[out.entity == "Nigeria"]["value"].iloc[0] == 15


def test_aggregate_period_median(toy_long):
    out = aggregate_period(toy_long, "Median")
    assert out[out.entity == "France"]["value"].iloc[0] == pytest.approx(25.0)


def test_aggregate_period_min_max(toy_long):
    mn = aggregate_period(toy_long, "Min")
    mx = aggregate_period(toy_long, "Max")
    assert mn[mn.entity == "France"]["value"].iloc[0] == 10
    assert mx[mx.entity == "France"]["value"].iloc[0] == 40


def test_aggregate_period_drops_nan_rows():
    df = pd.DataFrame(
        {
            "entity": ["A", "A", "A"],
            "iso3":   ["AAA"] * 3,
            "year":   [2000, 2001, 2002],
            "value":  [10.0, np.nan, 20.0],
        }
    )
    out = aggregate_period(df, "Mean")
    assert out["value"].iloc[0] == pytest.approx(15.0)


def test_all_aggregation_choices_run(toy_long):
    for choice in AGG_CHOICES:
        out = aggregate_period(toy_long, choice)
        assert not out.empty


def test_period_label():
    assert period_label("Mean", 2000, 2020) == "Mean 2000–2020"
    assert period_label("Sum", 1990, 1991) == "Sum 1990–1991"


# ── log1p_positive ────────────────────────────────────────────────────────────

def test_log1p_clips_negatives(toy_long):
    df = toy_long.copy()
    df.loc[0, "value"] = -5
    out, suffix = log1p_positive(df)
    assert suffix == "(log scale)"
    # Negative clipped to 0 → log1p(0) = 0.
    assert out["value"].iloc[0] == pytest.approx(0.0)
    # Positive values: log1p(20) ≈ 3.044…
    assert out["value"].iloc[1] == pytest.approx(np.log1p(20))
