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
    df = df.copy()
    df[col] = np.log1p(df[col].clip(lower=0))
    return df, "(log scale)"


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

    # Source footnote placed well below the x-axis tick labels
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

    # Enough bottom margin so source text sits below x-axis ticks
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

# Plotly scope strings mapped from display names
MAP_SCOPES = {
    "🌍 World":         "world",
    "🌍 Africa":        "africa",
    "🌏 Asia":          "asia",
    "🌎 North America": "north america",
    "🌎 South America": "south america",
    "🌍 Europe":        "europe",
    "🌊 Oceania":       "world",   # Plotly has no oceania scope; zoom via geo center instead
}


def make_map(
    df,
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
        df, suffix = _apply_log(df)
        unit_label = f"{unit_label} {suffix}"

    # Natural earth looks good for world; use equirectangular for regions
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
    df,
    title: str,
    indicator: dict,
    log_scale: bool = False,
    subtitle: str = "",
    source: str = "",
    xlabel: str = "Year",
    ylabel: str = "",
) -> go.Figure:
    df = df.dropna(subset=["value"]).copy()

    unit_label = indicator["unit"]
    if log_scale:
        df, suffix = _apply_log(df)
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
    df,
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
        df, suffix = _apply_log(df)
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


# ── Scatter matrix ─────────────────────────────────────────────────────────────

def make_scatter_matrix(
    df_wide,
    indicator_cols: list,
    col_labels: list,
    title: str,
    subtitle: str = "",
    source: str = "",
) -> go.Figure:
    """Scatter matrix (lower triangle only) — no trendlines, country name on hover."""
    df = df_wide.dropna(subset=indicator_cols).copy()
    df = df.rename(columns=dict(zip(indicator_cols, col_labels)))

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


# ── Correlation heatmap ────────────────────────────────────────────────────────

def make_corr_heatmap(
    df_wide,
    indicator_cols: list,
    col_labels: list,
    title: str,
    subtitle: str = "",
    source: str = "",
) -> go.Figure:
    """Pearson r heatmap — colour + number only, no equations."""
    df = df_wide[indicator_cols].dropna().copy()
    df.columns = col_labels
    corr = df.corr(method="pearson").round(2)

    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        template=_TEMPLATE,
        aspect="auto",
    )
    fig.update_traces(
        texttemplate="%{z:.2f}",
        hovertemplate="<b>%{x}</b> × <b>%{y}</b><br>r = %{z:.2f}<extra></extra>",
    )
    fig.update_coloraxes(
        colorbar=dict(
            title=dict(text="r", font=dict(size=12)),
            thickness=14,
            len=0.6,
            tickfont=dict(size=11),
        )
    )
    fig.update_layout(height=max(350, len(col_labels) * 80 + 120))
    _base_layout(fig, title, subtitle=subtitle, source=source)
    return fig


# ── Histogram ─────────────────────────────────────────────────────────────────

def make_histogram(
    df,
    title: str,
    indicator: dict,
    subtitle: str = "",
    source: str = "",
    xlabel: str = "",
    ylabel: str = "",
) -> go.Figure:
    """Distribution of indicator values across countries for a given period."""
    df = df.dropna(subset=["value"]).copy()
    unit_label = indicator["unit"]
    x_label = xlabel if xlabel else unit_label

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
        marker_color="#2563EB",
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
    df,
    title: str,
    indicator: dict,
    subtitle: str = "",
    source: str = "",
    xlabel: str = "",
    ylabel: str = "",
) -> go.Figure:
    """Distribution across countries — one box per year if time series."""
    df = df.dropna(subset=["value"]).copy()
    unit_label = indicator["unit"]
    y_label = ylabel if ylabel else unit_label

    if df["year"].nunique() > 1:
        fig = px.box(
            df.sort_values("year"),
            x="year", y="value",
            template=_TEMPLATE,
            labels={"value": y_label, "year": xlabel if xlabel else "Year"},
            points=False,
            color_discrete_sequence=["#2563EB"],
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
            color_discrete_sequence=["#2563EB"],
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
