"""
Plotly chart builders for EasyViz.

Academic-use rules enforced here:

  1. Missing observations never connect: line charts set `connectgaps=False`
     and draw markers on observed years so gaps are visible.
  2. Scatter pages offer a fitted overlay (OLS / LOESS) with R² shown.
  3. Correlation heatmap accepts `method="spearman"` for non-normal data.
  4. `_apply_log` is now imported from `src.transforms` — numerical
     transformations live in a single place.

All functions return a `go.Figure` ready for `st.plotly_chart`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.colors as pc
import plotly.express as px
import plotly.graph_objects as go

from .transforms import log1p_positive

# ── Style constants ───────────────────────────────────────────────────────────

_TEMPLATE = "plotly_white"
_FONT = dict(family="Inter, Arial, sans-serif", size=13, color="#1E293B")


def _scale_color(color_scale: str, pos: float = 0.65) -> str:
    """Extract a single representative colour from a named Plotly colorscale."""
    try:
        return pc.sample_colorscale(color_scale, [pos])[0]
    except Exception:
        return "#2563EB"


def _base_layout(
    fig: go.Figure,
    title: str,
    subtitle: str = "",
    source: str = "",
    extra_margin_b: int = 0,
) -> go.Figure:
    title_text = title
    if subtitle:
        title_text = f"{title}<br><sup style='color:#64748B'>{subtitle}</sup>"

    annotations = []
    if source:
        annotations.append(dict(
            text=f"Source: {source}",
            xref="paper", yref="paper",
            x=0, y=-0.18,
            showarrow=False,
            font=dict(size=10, color="#94A3B8"),
            align="left",
        ))

    bottom_margin = 90 + extra_margin_b if source else 50 + extra_margin_b

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=18, color="#0F172A"), x=0.01),
        font=_FONT,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(t=70, b=bottom_margin, l=60, r=20),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Inter, Arial"),
        annotations=annotations,
    )
    return fig


# ── World map ──────────────────────────────────────────────────────────────────

MAP_SCOPES = {
    "🌍 World":         "world",
    "🌍 Africa":        "africa",
    "🌏 Asia":          "asia",
    "🌎 North America": "north america",
    "🌎 South America": "south america",
    "🌍 Europe":        "europe",
    "🌊 Oceania":       "world",   # Plotly has no oceania scope; fall back to world
}


def make_map(
    df: pd.DataFrame,
    title: str,
    color_scale: str,
    indicator: dict,
    log_scale: bool = False,
    subtitle: str = "",
    source: str = "",
    scope: str = "world",
) -> go.Figure:
    df = df.dropna(subset=["value", "iso3"])
    df = df[df["iso3"].str.len() == 3].copy()

    unit_label = indicator["unit"]
    if log_scale:
        df, suffix = log1p_positive(df)
        unit_label = f"{unit_label} {suffix}"

    projection = "natural earth" if scope == "world" else "equirectangular"

    fig = px.choropleth(
        df,
        locations="iso3",
        color="value",
        hover_name="entity",
        color_continuous_scale=color_scale,
        projection=projection,
        scope=scope,
        labels={"value": unit_label},
        template=_TEMPLATE,
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" + unit_label + ": %{z:,.2f}<extra></extra>",
    )
    fig.update_geos(
        showcoastlines=True, coastlinecolor="#CBD5E1",
        showland=True, landcolor="#F8FAFC",
        showocean=True, oceancolor="#EFF6FF",
        showframe=False,
        showcountries=True, countrycolor="#E2E8F0",
    )
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text=unit_label, font=dict(size=12)),
            thickness=14, len=0.6, tickfont=dict(size=11),
        ),
        margin=dict(t=70, b=0, l=0, r=0),
    )
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig


# ── Line chart ────────────────────────────────────────────────────────────────

def make_line(
    df: pd.DataFrame,
    title: str,
    indicator: dict,
    log_scale: bool = False,
    subtitle: str = "",
    source: str = "",
    xlabel: str = "Year",
    ylabel: str = "",
) -> go.Figure:
    """
    Line chart with missing-data integrity:
      * `connectgaps=False` → no visual interpolation across NaN years
      * Markers on observed years → gap structure is visible at a glance
    """
    df = df.dropna(subset=["value"]).copy()

    unit_label = indicator["unit"]
    if log_scale:
        df, suffix = log1p_positive(df)
        unit_label = f"{unit_label} {suffix}"

    y_label = ylabel if ylabel else unit_label

    fig = px.line(
        df.sort_values("year"),
        x="year", y="value", color="entity",
        markers=True,
        labels={"value": y_label, "year": xlabel, "entity": "Country"},
        template=_TEMPLATE,
    )
    fig.update_traces(
        connectgaps=False,
        marker=dict(size=5),
        line=dict(width=2),
        hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>%{y:,.2f}<extra></extra>",
    )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(
            title=dict(text="Country", font=dict(size=12)),
            orientation="v", x=1.01, y=1,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#E2E8F0", borderwidth=1,
        ),
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=False),
    )
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig


# ── Bar chart ─────────────────────────────────────────────────────────────────

def make_bar(
    df: pd.DataFrame,
    title: str,
    indicator: dict,
    log_scale: bool = False,
    color_scale: str = "Blues",
    top_n: int = 25,
    subtitle: str = "",
    source: str = "",
    xlabel: str = "",
    ylabel: str = "",
) -> go.Figure:
    df = df.dropna(subset=["value"]).sort_values("value", ascending=False).head(top_n).copy()

    unit_label = indicator["unit"]
    if log_scale:
        df, suffix = log1p_positive(df)
        unit_label = f"{unit_label} {suffix}"

    x_label = xlabel if xlabel else unit_label

    fig = px.bar(
        df.sort_values("value"),
        x="value", y="entity", orientation="h",
        color="value", color_continuous_scale=color_scale,
        labels={"value": x_label, "entity": ylabel},
        template=_TEMPLATE,
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>" + unit_label + ": %{x:,.2f}<extra></extra>",
    )
    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        yaxis=dict(tickfont=dict(size=11)),
        height=max(350, top_n * 26),
    )
    _base_layout(fig, title, subtitle=subtitle, source=source, extra_margin_b=top_n * 2)
    return fig


# ── Scatter (2 indicators) with optional OLS / LOESS + R² ──────────────────────

def _fit_overlay(x: np.ndarray, y: np.ndarray, kind: str) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Return (x_sorted, y_hat, r2) for an OLS or LOESS fit.

    OLS → closed form via numpy. LOESS → statsmodels `lowess`. R² is
    computed against the raw y (not the fit line) so it is comparable
    across kinds.
    """
    order = np.argsort(x)
    xs, ys = x[order], y[order]

    if kind == "OLS":
        slope, intercept = np.polyfit(xs, ys, 1)
        y_hat = slope * xs + intercept
    elif kind == "LOESS":
        from statsmodels.nonparametric.smoothers_lowess import lowess
        smoothed = lowess(ys, xs, frac=0.5, it=1, return_sorted=True)
        xs, y_hat = smoothed[:, 0], smoothed[:, 1]
    else:
        return xs, ys, float("nan")

    ss_res = float(np.sum((ys - np.interp(xs, xs, y_hat)) ** 2))
    ss_tot = float(np.sum((ys - ys.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return xs, y_hat, r2


def make_scatter(
    df_wide: pd.DataFrame,
    indicator_cols: list[str],
    col_labels: list[str],
    title: str,
    subtitle: str = "",
    source: str = "",
    log_x: bool = False,
    log_y: bool = False,
    fit: str = "None",   # "None" | "OLS" | "LOESS"
) -> go.Figure:
    """Scatter for exactly 2 indicators with optional log axes and fit overlay."""
    x_col, y_col = indicator_cols
    x_label, y_label = col_labels
    df = df_wide.dropna(subset=indicator_cols).copy()

    fig = px.scatter(
        df,
        x=x_col, y=y_col,
        hover_name="entity",
        template=_TEMPLATE,
        opacity=0.75,
        labels={x_col: x_label, y_col: y_label},
        log_x=log_x,
        log_y=log_y,
    )
    fig.update_traces(
        marker=dict(size=7, line=dict(width=0.5, color="rgba(255,255,255,0.6)"),
                    color="#2563EB"),
        hovertemplate="<b>%{hovertext}</b><br>"
                      + x_label + ": %{x:,.2f}<br>"
                      + y_label + ": %{y:,.2f}<extra></extra>",
    )

    if fit in ("OLS", "LOESS") and len(df) >= 3:
        x_raw = df[x_col].to_numpy()
        y_raw = df[y_col].to_numpy()
        # When the axis is log-scaled, fit in log space so the line is straight.
        x_fit = np.log10(np.clip(x_raw, 1e-12, None)) if log_x else x_raw
        y_fit = np.log10(np.clip(y_raw, 1e-12, None)) if log_y else y_raw
        xs, y_hat, r2 = _fit_overlay(x_fit, y_fit, fit)
        xs_plot = 10 ** xs if log_x else xs
        ys_plot = 10 ** y_hat if log_y else y_hat
        fig.add_trace(go.Scatter(
            x=xs_plot, y=ys_plot,
            mode="lines",
            line=dict(color="#DC2626", width=2, dash="solid"),
            name=f"{fit} fit (R² = {r2:.2f})" if not np.isnan(r2) else fit,
            hoverinfo="skip",
        ))

    fig.update_layout(
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=False),
        height=520,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(255,255,255,0.9)",
        ),
        showlegend=fit in ("OLS", "LOESS"),
    )
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig


# ── Scatter matrix ────────────────────────────────────────────────────────────

def make_scatter_matrix(
    df_wide: pd.DataFrame,
    indicator_cols: list[str],
    col_labels: list[str],
    title: str,
    subtitle: str = "",
    source: str = "",
) -> go.Figure:
    df = df_wide.dropna(subset=indicator_cols).copy()
    df = df.rename(columns=dict(zip(indicator_cols, col_labels, strict=False)))

    fig = px.scatter_matrix(
        df,
        dimensions=col_labels,
        hover_name="entity",
        template=_TEMPLATE,
        opacity=0.7,
    )
    fig.update_traces(
        diagonal_visible=False,
        showupperhalf=False,
        marker=dict(size=5, line=dict(width=0.5, color="rgba(255,255,255,0.6)")),
        hovertemplate="<b>%{hovertext}</b><extra></extra>",
    )
    fig.update_layout(height=max(480, len(col_labels) * 160))
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig


# ── Correlation heatmap (Pearson or Spearman) ─────────────────────────────────

def make_corr_heatmap(
    df_wide: pd.DataFrame,
    indicator_cols: list[str],
    col_labels: list[str],
    title: str,
    subtitle: str = "",
    source: str = "",
    method: str = "pearson",    # "pearson" | "spearman"
) -> go.Figure:
    """
    Correlation heatmap. Pearson by default for continuous near-normal
    data; Spearman (rank) for skewed or ordinal variables — which is
    the common case for cross-country indicators.
    """
    df = df_wide[indicator_cols].dropna().copy()
    df.columns = col_labels
    corr = df.corr(method=method).round(2)

    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        template=_TEMPLATE,
        aspect="auto",
    )
    stat_label = "ρ (Spearman)" if method == "spearman" else "r (Pearson)"
    fig.update_traces(
        texttemplate="%{z:.2f}",
        hovertemplate="<b>%{x}</b> × <b>%{y}</b><br>"
                      + stat_label + " = %{z:.2f}<extra></extra>",
    )
    fig.update_coloraxes(
        colorbar=dict(
            title=dict(text=stat_label, font=dict(size=12)),
            thickness=14, len=0.6, tickfont=dict(size=11),
        )
    )
    fig.update_layout(height=max(350, len(col_labels) * 80 + 120))
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig


# ── Histogram ─────────────────────────────────────────────────────────────────

def make_histogram(
    df: pd.DataFrame,
    title: str,
    indicator: dict,
    color_scale: str = "Blues",
    subtitle: str = "",
    source: str = "",
    xlabel: str = "",
    ylabel: str = "",
) -> go.Figure:
    df = df.dropna(subset=["value"]).copy()
    unit_label = indicator["unit"]
    x_label = xlabel if xlabel else unit_label
    fill_color = _scale_color(color_scale)

    fig = px.histogram(
        df,
        x="value",
        nbins=30,
        marginal="rug",
        template=_TEMPLATE,
        labels={"value": x_label},
        opacity=0.8,
    )
    fig.update_traces(
        hovertemplate="Range: %{x}<br>Countries: %{y}<extra></extra>",
        marker_color=fill_color,
        selector=dict(type="histogram"),
    )
    fig.update_layout(
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        yaxis=dict(title=ylabel if ylabel else "Number of countries",
                   showgrid=True, gridcolor="#F1F5F9"),
        showlegend=False,
    )
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig


# ── Box plot ──────────────────────────────────────────────────────────────────

def make_box(
    df: pd.DataFrame,
    title: str,
    indicator: dict,
    color_scale: str = "Blues",
    subtitle: str = "",
    source: str = "",
    xlabel: str = "",
    ylabel: str = "",
) -> go.Figure:
    df = df.dropna(subset=["value"]).copy()
    unit_label = indicator["unit"]
    y_label = ylabel if ylabel else unit_label
    fill_color = _scale_color(color_scale)

    if df["year"].nunique() > 1:
        fig = px.box(
            df.sort_values("year"),
            x="year", y="value",
            template=_TEMPLATE,
            labels={"value": y_label, "year": xlabel if xlabel else "Year"},
            points=False,
            color_discrete_sequence=[fill_color],
        )
        fig.update_traces(
            hovertemplate="Year: %{x}<br>Median: %{median:.2f}<extra></extra>",
        )
    else:
        fig = px.box(
            df,
            y="value",
            template=_TEMPLATE,
            labels={"value": y_label},
            points="outliers",
            color_discrete_sequence=[fill_color],
        )
        fig.update_traces(
            hovertemplate="%{y:.2f}<extra></extra>",
        )

    fig.update_layout(
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        showlegend=False,
    )
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig


# ── Gapminder-style animated scatter ──────────────────────────────────────────

def make_gapminder(
    df_long: pd.DataFrame,
    x_col: str,
    y_col: str,
    size_col: str | None,
    x_label: str,
    y_label: str,
    size_label: str,
    title: str,
    subtitle: str = "",
    source: str = "",
    log_x: bool = False,
    log_y: bool = False,
) -> go.Figure:
    """
    Gapminder-style animated bubble scatter.

    Expects a long DataFrame with columns:
        entity, iso3, year, <x_col>, <y_col>, optional <size_col>

    Animates over `year`; each frame is a cross-section. When `size_col`
    is None, a constant bubble size is used.
    """
    df = df_long.dropna(subset=[x_col, y_col]).copy()
    if size_col:
        df = df.dropna(subset=[size_col]).copy()
        df[size_col] = df[size_col].clip(lower=0)

    # Fix axis ranges so bubbles don't jump between frames.
    x_pad = (df[x_col].max() - df[x_col].min()) * 0.05 if len(df) else 1
    y_pad = (df[y_col].max() - df[y_col].min()) * 0.05 if len(df) else 1
    x_range = [df[x_col].min() - x_pad, df[x_col].max() + x_pad]
    y_range = [df[y_col].min() - y_pad, df[y_col].max() + y_pad]

    kw = dict(
        data_frame=df.sort_values(["year", "entity"]),
        x=x_col, y=y_col,
        color="entity",
        animation_frame="year",
        animation_group="entity",
        hover_name="entity",
        template=_TEMPLATE,
        labels={x_col: x_label, y_col: y_label, "entity": "Country"},
        log_x=log_x,
        log_y=log_y,
        range_x=x_range if not log_x else None,
        range_y=y_range if not log_y else None,
    )
    if size_col:
        kw.update(size=size_col, size_max=55)
        kw["labels"][size_col] = size_label

    fig = px.scatter(**kw)
    fig.update_traces(
        marker=dict(line=dict(width=0.5, color="rgba(255,255,255,0.7)")),
    )
    fig.update_layout(
        height=600,
        legend=dict(
            orientation="v", x=1.02, y=1,
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#E2E8F0", borderwidth=1,
            title=dict(text="Country"),
        ),
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=False),
    )
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig


# ── Sub-national admin choropleth ─────────────────────────────────────────────

def make_admin_map(
    df: pd.DataFrame,
    geojson: dict,
    title: str,
    color_scale: str = "Blues",
    unit: str = "value",
    log_scale: bool = False,
    subtitle: str = "",
    source: str = "",
) -> go.Figure:
    df = df.dropna(subset=["value", "region"]).copy()
    if log_scale:
        df, suffix = log1p_positive(df)
        unit = f"{unit} {suffix}"

    fig = px.choropleth(
        df,
        geojson=geojson,
        featureidkey="properties.shapeName",
        locations="region",
        color="value",
        color_continuous_scale=color_scale,
        labels={"value": unit},
        template=_TEMPLATE,
        hover_name="region",
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" + unit + ": %{z:,.2f}<extra></extra>",
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text=unit, font=dict(size=12)),
            thickness=14, len=0.6, tickfont=dict(size=11),
        ),
        margin=dict(t=70, b=20, l=0, r=0),
        height=580,
    )
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig
