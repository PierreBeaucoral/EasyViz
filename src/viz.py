"""
Plotly chart builders for DevViz.
All functions return a go.Figure ready for st.plotly_chart.
"""

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

_TEMPLATE = "plotly_white"
_FONT = dict(family="Inter, Arial, sans-serif", size=13, color="#1E293B")


def _apply_log(df, col: str = "value") -> tuple:
    """Return a log-transformed series and an updated label."""
    df = df.copy()
    df[col] = np.log1p(df[col].clip(lower=0))
    return df, "(log scale)"


def _base_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="#0F172A"), x=0.01),
        font=_FONT,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(t=60, b=40, l=40, r=20),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Inter, Arial"),
    )
    return fig


# ── World map ──────────────────────────────────────────────────────────────────

def make_map(
    df,
    title: str,
    color_scale: str,
    indicator: dict,
    log_scale: bool = False,
) -> go.Figure:
    df = df.dropna(subset=["value", "iso3"])
    df = df[df["iso3"].str.len() == 3].copy()

    unit_label = indicator["unit"]
    if log_scale:
        df, suffix = _apply_log(df)
        unit_label = f"{unit_label} {suffix}"

    fig = px.choropleth(
        df,
        locations="iso3",
        color="value",
        hover_name="entity",
        color_continuous_scale=color_scale,
        projection="natural earth",
        labels={"value": unit_label},
        template=_TEMPLATE,
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" + unit_label + ": %{z:,.2f}<extra></extra>",
    )
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="#CBD5E1",
        showland=True,
        landcolor="#F8FAFC",
        showocean=True,
        oceancolor="#EFF6FF",
        showframe=False,
        showcountries=True,
        countrycolor="#E2E8F0",
    )
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text=unit_label, font=dict(size=12)),
            thickness=14,
            len=0.6,
            tickfont=dict(size=11),
        ),
        margin=dict(t=50, b=0, l=0, r=0),
    )
    _base_layout(fig, title)
    return fig


# ── Line chart ────────────────────────────────────────────────────────────────

def make_line(
    df,
    title: str,
    indicator: dict,
    log_scale: bool = False,
) -> go.Figure:
    df = df.dropna(subset=["value"]).copy()

    unit_label = indicator["unit"]
    if log_scale:
        df, suffix = _apply_log(df)
        unit_label = f"{unit_label} {suffix}"

    fig = px.line(
        df.sort_values("year"),
        x="year",
        y="value",
        color="entity",
        markers=True,
        labels={
            "value": unit_label,
            "year": "Year",
            "entity": "Country",
        },
        template=_TEMPLATE,
    )
    fig.update_traces(
        marker=dict(size=5),
        line=dict(width=2),
        hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>%{y:,.2f}<extra></extra>",
    )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(
            title=dict(text="Country", font=dict(size=12)),
            orientation="v",
            x=1.01,
            y=1,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#E2E8F0",
            borderwidth=1,
        ),
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", zeroline=False),
    )
    _base_layout(fig, title)
    return fig


# ── Bar chart ─────────────────────────────────────────────────────────────────

def make_bar(
    df,
    title: str,
    indicator: dict,
    log_scale: bool = False,
    color_scale: str = "Blues",
    top_n: int = 25,
) -> go.Figure:
    df = df.dropna(subset=["value"]).sort_values("value", ascending=False).head(top_n).copy()

    unit_label = indicator["unit"]
    if log_scale:
        df, suffix = _apply_log(df)
        unit_label = f"{unit_label} {suffix}"

    fig = px.bar(
        df.sort_values("value"),          # ascending so highest bar is at top
        x="value",
        y="entity",
        orientation="h",
        color="value",
        color_continuous_scale=color_scale,
        labels={"value": unit_label, "entity": ""},
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
    _base_layout(fig, title)
    return fig
