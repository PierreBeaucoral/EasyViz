"""
Pure, testable data transformations for EasyViz.

Every transform takes a long-format DataFrame with columns
(entity, iso3, year, value) and returns the same shape plus a
unit-label suffix that the caller can splice into the y-axis title.

These functions are free of Streamlit, Plotly, and any IO — they are
the only place in the codebase where numerical transforms live, which
keeps the viz layer pure and makes the logic unit-testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ── Per-entity transforms ─────────────────────────────────────────────────────

# Human-readable names → internal identifiers. Kept stable across UI refactors.
TRANSFORM_CHOICES: list[str] = [
    "None",
    "% of max (normalize 0–100)",
    "% change vs first year",
    "Cumulative sum",
    "Rolling avg (3 yr)",
    "Rank (1 = highest)",
]


def apply_transform(
    df: pd.DataFrame,
    transform: str,
    unit: str,
) -> tuple[pd.DataFrame, str]:
    """
    Apply a per-entity transform and return (df, new_unit_label).

    The transform is applied independently to each entity — so cumulative
    sum accumulates within a country, rolling average is per-country, etc.
    An empty / None / "None" transform is a passthrough.
    """
    if not transform or transform == "None":
        return df, unit

    data = df.copy().sort_values(["entity", "year"])

    if transform == "% of max (normalize 0–100)":
        mx = data["value"].max()
        data["value"] = (data["value"] / mx * 100) if mx else data["value"]
        return data, "% of max"

    if transform == "% change vs first year":
        # For each entity, rescale value as % change vs. the earliest-year value.
        # Computed per-entity via a plain Python loop to sidestep the
        # DataFrameGroupBy.apply deprecation warning and keep the edge case
        # (first_year_value == 0 → NaN) explicit.
        out_values = pd.Series(np.nan, index=data.index)
        for _, idx in data.groupby("entity").groups.items():
            sub = data.loc[idx]
            first = sub.loc[sub["year"].idxmin(), "value"]
            if first:
                out_values.loc[idx] = (sub["value"] - first) / first * 100
        data["value"] = out_values
        return data, "% change vs first year"

    if transform == "Cumulative sum":
        data["value"] = data.groupby("entity")["value"].cumsum()
        return data, f"cumulative {unit}"

    if transform == "Rolling avg (3 yr)":
        data["value"] = (
            data.groupby("entity")["value"]
            .transform(lambda s: s.rolling(3, min_periods=1).mean())
        )
        return data, f"3-yr avg {unit}"

    if transform == "Rank (1 = highest)":
        data["value"] = data.groupby("year")["value"].rank(
            ascending=False, method="min"
        )
        return data, "rank"

    # Unknown label: fail open with a passthrough
    return data, unit


# ── Period aggregation ────────────────────────────────────────────────────────

AGG_CHOICES: list[str] = ["Mean", "Sum", "Median", "Min", "Max"]

_AGG_FUNCS: dict[str, str] = {
    "Mean": "mean", "Sum": "sum", "Median": "median", "Min": "min", "Max": "max",
}


def aggregate_period(df: pd.DataFrame, agg_label: str) -> pd.DataFrame:
    """
    Collapse a long-format DataFrame to one row per country using `agg_label`.

    Rows with NaN values are dropped *before* aggregation so a country with
    partial coverage is still summarised on its observed years.
    """
    func = _AGG_FUNCS.get(agg_label, "mean")
    return (
        df.dropna(subset=["value"])
        .groupby(["entity", "iso3"], as_index=False)["value"]
        .agg(func)
    )


def period_label(agg_label: str, y0: int, y1: int) -> str:
    """Produce a short label like 'Mean 2000–2020' for chart titles."""
    return f"{agg_label} {y0}–{y1}"


# ── Log transform (shared by viz + codegen) ───────────────────────────────────

def log1p_positive(df: pd.DataFrame, col: str = "value") -> tuple[pd.DataFrame, str]:
    """
    Apply log1p after clipping negatives to zero.

    Limitation: series with legitimate negative values (growth rates,
    WGI estimates, current-account balance) will be distorted — the UI
    should refuse log for these variables. A future improvement is
    `signed_log = sign(x) * log1p(|x|)`, but that changes the axis
    interpretation in a way that is not always welcome for a quick chart.
    """
    out = df.copy()
    out[col] = np.log1p(out[col].clip(lower=0))
    return out, "(log scale)"
