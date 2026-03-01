"""
DevViz — Development Data Explorer
Landing page + data explorer with OWID and World Bank data.
"""

import io

import streamlit as st

from src.catalog import INDICATORS
from src.codegen import python_code, r_code
from src.fetcher import fetch_data
from src.search import fuzzy_search
from src.viz import make_bar, make_line, make_map

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="DevViz — Development Data Explorer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Shared CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark sidebar */
section[data-testid="stSidebar"] { background: #0F172A; }
section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
section[data-testid="stSidebar"] .stTextInput input {
    background: #1E293B; border: 1px solid #334155;
    color: #F1F5F9 !important; border-radius: 8px;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #F8FAFC; border-radius: 10px;
    padding: 12px 16px; border: 1px solid #E2E8F0;
}

/* Download buttons */
.stDownloadButton button {
    background: #1E40AF; color: white; border: none;
    border-radius: 8px; font-weight: 500;
}
.stDownloadButton button:hover { background: #1D4ED8; }

.section-label {
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #64748B; margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────

CAT_ICON = {
    "Health": "🏥", "Economy": "💰", "Education": "📚",
    "Environment": "🌿", "Demographics": "👥", "Governance": "🏛️",
}

POPULAR_IDS = [
    "under5_mortality", "gdp_per_capita_ppp", "co2_per_capita",
    "extreme_poverty", "life_expectancy", "literacy_rate",
    "access_electricity", "fertility_rate",
]

DEFAULT_COUNTRIES = [
    "United States", "China", "Germany", "Brazil", "India",
    "Nigeria", "France", "United Kingdom", "South Africa", "Indonesia",
    "Mexico", "Bangladesh", "Ethiopia", "Kenya", "Colombia",
    "Vietnam", "Egypt", "Pakistan", "Tanzania", "Ghana",
]

# ── State ─────────────────────────────────────────────────────────────────────

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None


# ══════════════════════════════════════════════════════════════════════════════
# HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════

def home_page():
    # Hide sidebar and toggle button
    st.markdown("""
    <style>
    section[data-testid="stSidebar"]  { display: none !important; }
    [data-testid="collapsedControl"]   { display: none !important; }

    /* Big rounded search bar */
    div[data-testid="stTextInput"] input {
        font-size: 1.1rem !important;
        padding: 14px 22px !important;
        border-radius: 50px !important;
        border: 2px solid #E2E8F0 !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.07) !important;
        transition: all 0.2s;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #2563EB !important;
        box-shadow: 0 4px 24px rgba(37,99,235,0.14) !important;
        outline: none !important;
    }

    /* Result buttons — pill style */
    div[data-testid="stHorizontalBlock"] .stButton button,
    .result-btn .stButton button {
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        background: white;
        color: #1E293B;
        text-align: left;
        padding: 10px 14px;
        font-size: 0.95rem;
        transition: all 0.15s;
    }
    div[data-testid="stHorizontalBlock"] .stButton button:hover,
    .result-btn .stButton button:hover {
        border-color: #2563EB;
        color: #1E40AF;
        background: #EFF6FF;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding-top:9vh'></div>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            "<h1 style='text-align:center;font-size:3rem;margin-bottom:6px'>🌍 DevViz</h1>"
            "<p style='text-align:center;color:#64748B;font-size:1.05rem;margin-bottom:36px'>"
            "Explore development data, beautifully.</p>",
            unsafe_allow_html=True,
        )

        query = st.text_input(
            "search",
            placeholder="🔍   child mortality, GDP, CO₂, poverty, literacy…",
            label_visibility="collapsed",
        )

        if query:
            results = fuzzy_search(query, INDICATORS, limit=7)
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            for r in results:
                icon = CAT_ICON.get(r["category"], "📊")
                if st.button(
                    f"{icon}  {r['name']}   ·   {r['category']}  —  {r['unit']}",
                    key=f"home_{r['id']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_id = r["id"]
                    st.rerun()
        else:
            st.markdown(
                "<p style='text-align:center;color:#94A3B8;font-size:0.82rem;"
                "margin:28px 0 14px;letter-spacing:0.08em'>POPULAR INDICATORS</p>",
                unsafe_allow_html=True,
            )
            popular = [r for r in INDICATORS if r["id"] in POPULAR_IDS]
            for row in [popular[:4], popular[4:]]:
                cols = st.columns(len(row))
                for i, ind in enumerate(row):
                    with cols[i]:
                        icon = CAT_ICON.get(ind["category"], "📊")
                        if st.button(
                            f"{icon}  {ind['name']}",
                            key=f"pop_{ind['id']}",
                            use_container_width=True,
                        ):
                            st.session_state.selected_id = ind["id"]
                            st.rerun()

        st.markdown(
            "<p style='text-align:center;color:#CBD5E1;font-size:0.75rem;margin-top:48px'>"
            "Data: Our World in Data · World Bank WDI</p>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# DATA PAGE
# ══════════════════════════════════════════════════════════════════════════════

def data_page():

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<h1 style='color:#F1F5F9;font-size:1.4rem;margin-bottom:8px'>🌍 DevViz</h1>",
            unsafe_allow_html=True,
        )
        if st.button("← New search", use_container_width=True):
            st.session_state.selected_id = None
            st.rerun()

        st.divider()
        st.markdown("**Switch indicator**")
        query_sb = st.text_input(
            "sb_search", placeholder="Search…",
            label_visibility="collapsed", key="sidebar_search",
        )
        sb_results = fuzzy_search(query_sb, INDICATORS, limit=12) if query_sb else INDICATORS
        selected_id = st.radio(
            "Select:",
            options=[r["id"] for r in sb_results],
            index=next(
                (i for i, r in enumerate(sb_results)
                 if r["id"] == st.session_state.selected_id), 0,
            ),
            format_func=lambda x: next(r["name"] for r in INDICATORS if r["id"] == x),
            label_visibility="collapsed",
        )
        if selected_id != st.session_state.selected_id:
            st.session_state.selected_id = selected_id
            st.rerun()

        st.divider()
        indicator = next(r for r in INDICATORS if r["id"] == selected_id)
        src_label = "Our World in Data" if indicator["source"] == "owid" else "World Bank"
        src_color = "#10B981" if indicator["source"] == "owid" else "#3B82F6"
        st.markdown(
            f"<span style='background:{src_color};color:white;padding:3px 10px;"
            f"border-radius:20px;font-size:0.78rem;font-weight:600'>{src_label}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<br>**Unit:** {indicator['unit']}", unsafe_allow_html=True)
        st.markdown(
            f"**Category:** {CAT_ICON.get(indicator['category'], '📊')} {indicator['category']}"
        )

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner(f"Loading **{indicator['name']}**…"):
        df = fetch_data(indicator)

    if df is None or df.empty:
        st.error(
            f"**{indicator['name']}** could not be loaded from {src_label}. "
            "The data may be sparse or temporarily unavailable."
        )
        st.markdown("**Try a related indicator:**")
        alts = [
            r for r in INDICATORS
            if r["category"] == indicator["category"] and r["id"] != indicator["id"]
        ][:4]
        cols = st.columns(len(alts)) if alts else []
        for i, alt in enumerate(alts):
            with cols[i]:
                if st.button(
                    f"{CAT_ICON.get(alt['category'], '📊')} {alt['name']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_id = alt["id"]
                    st.rerun()
        return

    df = df[df["iso3"].notna() & (df["iso3"].str.len() == 3)]

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"## {CAT_ICON.get(indicator['category'], '📊')} {indicator['name']}"
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Source", src_label)
    m2.metric("Unit", indicator["unit"])
    m3.metric("Countries", df["entity"].nunique())
    m4.metric("Year range", f"{int(df['year'].min())} – {int(df['year'].max())}")
    st.divider()

    # ── Filters ───────────────────────────────────────────────────────────────
    all_countries = sorted(df["entity"].unique().tolist())
    default_sel = [c for c in DEFAULT_COUNTRIES if c in all_countries]
    year_min, year_max = int(df["year"].min()), int(df["year"].max())

    col_c, col_y = st.columns([3, 1])
    with col_c:
        selected_countries = st.multiselect(
            "Countries (Line & Bar charts)",
            options=all_countries,
            default=default_sel[:15],
        )
    with col_y:
        year_range = st.slider(
            "Year range",
            min_value=year_min, max_value=year_max,
            value=(max(year_min, year_max - 20), year_max),
        )

    _countries = selected_countries if selected_countries else all_countries
    filtered = df[
        df["entity"].isin(_countries)
        & df["year"].between(year_range[0], year_range[1])
    ]

    st.divider()

    # ── Chart controls ────────────────────────────────────────────────────────
    col_ctrl, col_chart = st.columns([1, 3])

    with col_ctrl:
        st.markdown('<div class="section-label">Chart type</div>', unsafe_allow_html=True)
        chart_type = st.radio(
            "chart_type",
            ["🗺️ World Map", "📈 Line Chart", "📊 Bar Chart"],
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="section-label" style="margin-top:16px">Transform data</div>',
            unsafe_allow_html=True,
        )
        st.caption("Applies to Line & Bar charts")
        transform = st.selectbox(
            "transform", label_visibility="collapsed",
            options=[
                "None",
                "% of max (normalize 0–100)",
                "% change vs first year",
                "Cumulative sum",
                "Rolling avg (3 yr)",
                "Rank (1 = highest)",
            ],
        )

        st.markdown(
            '<div class="section-label" style="margin-top:16px">Customise</div>',
            unsafe_allow_html=True,
        )
        chart_title    = st.text_input("Title", value=indicator["name"])
        chart_subtitle = st.text_input("Subtitle", placeholder="e.g. 2000–2023, Sub-Saharan Africa")
        chart_source   = st.text_input("Source note", value=src_label,
                                       help="Footnote shown at the bottom of the chart")
        axis_col1, axis_col2 = st.columns(2)
        with axis_col1:
            x_label = st.text_input("X label", placeholder="Year")
        with axis_col2:
            y_label = st.text_input("Y label", placeholder=indicator["unit"])
        log_scale      = st.checkbox("Logarithmic scale")
        color_scale    = st.selectbox(
            "Color palette",
            ["Blues", "Viridis", "RdYlGn", "Plasma", "YlOrRd",
             "Oranges", "Greens", "Cividis", "Turbo", "Reds"],
        )

        # Always-defined year / bar vars (widgets shown conditionally)
        map_year = year_range[1]
        bar_year = year_range[1]
        top_n    = 20
        if "Map" in chart_type:
            map_year = st.number_input(
                "Map year", min_value=year_min, max_value=year_max, value=year_range[1]
            )
        if "Bar" in chart_type:
            bar_year = st.number_input(
                "Bar year",
                min_value=year_range[0], max_value=year_range[1], value=year_range[1],
            )
            top_n = st.slider("Top N countries", 5, 50, 20)

    # ── Apply transform ───────────────────────────────────────────────────────
    def _apply_transform(data, t):
        """Apply a data transformation per entity, return transformed df + unit suffix."""
        import numpy as _np
        if t == "None" or not t:
            return data, indicator["unit"]
        data = data.copy().sort_values(["entity", "year"])
        if t == "% of max (normalize 0–100)":
            mx = data["value"].max()
            data["value"] = data["value"] / mx * 100 if mx else data["value"]
            return data, "% of max"
        if t == "% change vs first year":
            def _pct(g):
                first = g.loc[g["year"].idxmin(), "value"]
                g = g.copy()
                g["value"] = ((g["value"] - first) / first * 100) if first else _np.nan
                return g
            data = data.groupby("entity", group_keys=False).apply(_pct)
            return data, "% change vs first year"
        if t == "Cumulative sum":
            data["value"] = data.groupby("entity")["value"].cumsum()
            return data, f"cumulative {indicator['unit']}"
        if t == "Rolling avg (3 yr)":
            data["value"] = (
                data.groupby("entity")["value"]
                .transform(lambda s: s.rolling(3, min_periods=1).mean())
            )
            return data, f"3-yr avg {indicator['unit']}"
        if t == "Rank (1 = highest)":
            data["value"] = data.groupby("year")["value"].rank(ascending=False, method="min")
            return data, "rank"
        return data, indicator["unit"]

    filtered_t, unit_label = _apply_transform(filtered, transform)

    # Build a patched indicator dict with the transformed unit label
    indicator_t = {**indicator, "unit": unit_label}

    # ── Build & display chart ─────────────────────────────────────────────────
    with col_chart:
        # Map uses raw data (transforms need time series); Line/Bar use filtered_t
        shared_kw = dict(
            log_scale=log_scale,
            subtitle=chart_subtitle,
            source=chart_source,
            xlabel=x_label,
            ylabel=y_label,
        )
        if "Map" in chart_type:
            fig = make_map(
                df[df["year"] == map_year],
                title=chart_title,
                color_scale=color_scale,
                indicator=indicator,   # raw unit for map
                log_scale=log_scale,
                subtitle=chart_subtitle,
                source=chart_source,
            )
        elif "Line" in chart_type:
            fig = make_line(filtered_t, title=chart_title, indicator=indicator_t, **shared_kw)
        else:
            fig = make_bar(
                filtered_t[filtered_t["year"] == bar_year].sort_values("value", ascending=False),
                title=f"{chart_title} ({bar_year})",
                color_scale=color_scale,
                top_n=top_n,
                indicator=indicator_t,
                **shared_kw,
            )
        st.plotly_chart(fig, use_container_width=True)

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Download**")
    dl1, dl2, dl3, dl4 = st.columns(4)

    with dl1:
        st.download_button(
            "⬇️ Data (CSV)", filtered.to_csv(index=False),
            f"{indicator['id']}.csv", "text/csv", use_container_width=True,
        )
    with dl2:
        try:
            buf = io.BytesIO()
            fig.write_image(buf, format="png", scale=2, width=1400, height=800)
            st.download_button(
                "⬇️ Chart (PNG)", buf.getvalue(),
                f"{indicator['id']}.png", "image/png", use_container_width=True,
            )
        except Exception:
            st.button("⬇️ PNG (needs kaleido)", disabled=True, use_container_width=True)
    with dl3:
        st.download_button(
            "⬇️ Chart (HTML)", fig.to_html(full_html=True, include_plotlyjs="cdn"),
            f"{indicator['id']}.html", "text/html", use_container_width=True,
        )
    with dl4:
        try:
            svg_buf = io.BytesIO()
            fig.write_image(svg_buf, format="svg")
            st.download_button(
                "⬇️ Chart (SVG)", svg_buf.getvalue(),
                f"{indicator['id']}.svg", "image/svg+xml", use_container_width=True,
            )
        except Exception:
            st.button("⬇️ SVG (needs kaleido)", disabled=True, use_container_width=True)

    # ── Reproduce this chart ──────────────────────────────────────────────────
    st.divider()
    with st.expander("👩‍💻 Reproduce this chart — get the code"):
        _code_kw = dict(
            indicator=indicator,
            selected_countries=_countries,
            year_range=year_range,
            chart_type=chart_type,
            map_year=map_year,
            bar_year=bar_year,
            top_n=top_n,
            log_scale=log_scale,
            color_scale=color_scale,
            chart_title=chart_title,
        )
        tab_py, tab_r = st.tabs(["🐍 Python", "📦 R"])
        with tab_py:
            py_script = python_code(**_code_kw)
            st.code(py_script, language="python")
            st.download_button(
                "⬇️ Download .py", py_script,
                f"{indicator['id']}_chart.py", "text/x-python",
            )
        with tab_r:
            r_script = r_code(**_code_kw)
            st.code(r_script, language="r")
            st.download_button(
                "⬇️ Download .R", r_script,
                f"{indicator['id']}_chart.R", "text/plain",
            )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        "<br><p style='text-align:center;color:#94A3B8;font-size:0.78rem'>"
        "Data: <a href='https://ourworldindata.org' target='_blank'>Our World in Data</a> · "
        "<a href='https://data.worldbank.org' target='_blank'>World Bank WDI</a> · "
        "Built with Streamlit + Plotly</p>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.selected_id is None:
    home_page()
else:
    data_page()
