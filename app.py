"""
DevViz — Development Data Explorer
A lightweight Streamlit app for exploring OWID and World Bank data with
interactive, customisable, and downloadable charts.
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
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background: #0F172A; }
    section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    section[data-testid="stSidebar"] .stTextInput input {
        background: #1E293B; border: 1px solid #334155; color: #F1F5F9 !important;
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] .stRadio label { color: #94A3B8 !important; }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { color: #F1F5F9 !important; }

    /* Download buttons */
    .stDownloadButton button {
        background: #1E40AF; color: white; border: none;
        border-radius: 8px; font-weight: 500;
        transition: background 0.2s;
    }
    .stDownloadButton button:hover { background: #1D4ED8; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #F8FAFC; border-radius: 10px;
        padding: 12px 16px; border: 1px solid #E2E8F0;
    }

    /* Section headers */
    .section-label {
        font-size: 0.78rem; font-weight: 600; letter-spacing: 0.08em;
        text-transform: uppercase; color: #64748B; margin-bottom: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Default country selection ─────────────────────────────────────────────────

_DEFAULTS = [
    "United States", "China", "Germany", "Brazil", "India",
    "Nigeria", "France", "United Kingdom", "South Africa", "Indonesia",
    "Mexico", "Bangladesh", "Ethiopia", "Kenya", "Colombia",
    "Vietnam", "Egypt", "Pakistan", "Tanzania", "Ghana",
]

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<h1 style='color:#F1F5F9;font-size:1.6rem;margin-bottom:0'>🌍 DevViz</h1>"
        "<p style='color:#64748B;font-size:0.85rem;margin-top:2px'>"
        "Explore development data, beautifully.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    query = st.text_input(
        "Search indicator",
        placeholder="child mortality, GDP, CO₂, poverty…",
    )
    results = fuzzy_search(query, INDICATORS, limit=12) if query else INDICATORS

    selected_id = st.radio(
        "Select:",
        options=[r["id"] for r in results],
        format_func=lambda x: next(r["name"] for r in INDICATORS if r["id"] == x),
        label_visibility="collapsed",
    )

    st.divider()
    indicator = next(r for r in INDICATORS if r["id"] == selected_id)
    source_color = "#3B82F6" if indicator["source"] == "wdi" else "#10B981"
    source_label = "World Bank" if indicator["source"] == "wdi" else "Our World in Data"
    st.markdown(
        f"<span style='background:{source_color};color:white;padding:3px 10px;"
        f"border-radius:20px;font-size:0.78rem;font-weight:600'>{source_label}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<br>**Unit:** {indicator['unit']}", unsafe_allow_html=True)
    st.markdown(f"**Category:** {indicator['category']}")

# ── Load data ─────────────────────────────────────────────────────────────────

with st.spinner(f"Loading **{indicator['name']}**…"):
    df = fetch_data(indicator)

if df is None or df.empty:
    st.error(
        f"Could not load data for **{indicator['name']}**. "
        "The source may be temporarily unavailable — try another indicator."
    )
    st.stop()

# Drop rows without a valid 3-letter ISO code
df = df[df["iso3"].notna() & (df["iso3"].str.len() == 3)]

# ── Header metrics ────────────────────────────────────────────────────────────

st.markdown(f"## {indicator['name']}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Source", source_label)
m2.metric("Unit", indicator["unit"])
m3.metric("Countries", df["entity"].nunique())
m4.metric("Year range", f"{int(df['year'].min())} – {int(df['year'].max())}")

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────

all_countries = sorted(df["entity"].unique().tolist())
default_sel = [c for c in _DEFAULTS if c in all_countries]

year_min, year_max = int(df["year"].min()), int(df["year"].max())

col_countries, col_years = st.columns([3, 1])

with col_countries:
    selected_countries = st.multiselect(
        "Countries (used for Line & Bar charts)",
        options=all_countries,
        default=default_sel[:15],
    )

with col_years:
    year_range = st.slider(
        "Year range",
        min_value=year_min,
        max_value=year_max,
        value=(max(year_min, year_max - 20), year_max),
    )

# Filtered subset for line / bar charts
_countries = selected_countries if selected_countries else all_countries
filtered = df[
    df["entity"].isin(_countries)
    & df["year"].between(year_range[0], year_range[1])
]

st.divider()

# ── Chart selector + customisation ───────────────────────────────────────────

col_ctrl, col_chart = st.columns([1, 3])

with col_ctrl:
    st.markdown('<div class="section-label">Chart type</div>', unsafe_allow_html=True)
    chart_type = st.radio(
        "chart_type",
        ["🗺️ World Map", "📈 Line Chart", "📊 Bar Chart"],
        label_visibility="collapsed",
    )

    st.markdown('<div class="section-label" style="margin-top:16px">Customise</div>', unsafe_allow_html=True)

    chart_title = st.text_input("Title", value=indicator["name"])
    log_scale = st.checkbox("Logarithmic scale")
    color_scale = st.selectbox(
        "Color palette",
        ["Blues", "Viridis", "RdYlGn", "Plasma", "YlOrRd",
         "Oranges", "Greens", "Cividis", "Turbo", "Reds"],
    )

    # Always define these — only show widgets when relevant
    map_year = year_range[1]
    bar_year = year_range[1]
    top_n = 20
    if "Map" in chart_type:
        map_year = st.number_input(
            "Map year", min_value=year_min, max_value=year_max, value=year_range[1]
        )
    if "Bar" in chart_type:
        bar_year = st.number_input(
            "Bar year", min_value=year_range[0], max_value=year_range[1], value=year_range[1]
        )
        top_n = st.slider("Top N countries", 5, 50, 20)

# ── Build & display chart ─────────────────────────────────────────────────────

with col_chart:
    if "Map" in chart_type:
        map_data = df[df["year"] == map_year]
        fig = make_map(
            map_data,
            title=chart_title,
            color_scale=color_scale,
            indicator=indicator,
            log_scale=log_scale,
        )
    elif "Line" in chart_type:
        fig = make_line(
            filtered,
            title=chart_title,
            indicator=indicator,
            log_scale=log_scale,
        )
    else:  # Bar
        bar_data = (
            filtered[filtered["year"] == bar_year]
            .sort_values("value", ascending=False)
        )
        fig = make_bar(
            bar_data,
            title=f"{chart_title} ({bar_year})",
            indicator=indicator,
            log_scale=log_scale,
            color_scale=color_scale,
            top_n=top_n,
        )

    st.plotly_chart(fig, use_container_width=True)

# ── Downloads ─────────────────────────────────────────────────────────────────

st.divider()
st.markdown("**Download**")

dl1, dl2, dl3, dl4 = st.columns(4)

with dl1:
    st.download_button(
        "⬇️ Data (CSV)",
        filtered.to_csv(index=False),
        f"{indicator['id']}.csv",
        "text/csv",
        use_container_width=True,
        help="Download the filtered dataset as CSV",
    )

with dl2:
    try:
        buf = io.BytesIO()
        fig.write_image(buf, format="png", scale=2, width=1400, height=800)
        st.download_button(
            "⬇️ Chart (PNG)",
            buf.getvalue(),
            f"{indicator['id']}.png",
            "image/png",
            use_container_width=True,
            help="High-resolution PNG (2×)",
        )
    except Exception:
        st.button(
            "⬇️ PNG (install kaleido)",
            disabled=True,
            use_container_width=True,
            help="Run: pip install kaleido",
        )

with dl3:
    html_export = fig.to_html(full_html=True, include_plotlyjs="cdn")
    st.download_button(
        "⬇️ Chart (HTML)",
        html_export,
        f"{indicator['id']}.html",
        "text/html",
        use_container_width=True,
        help="Interactive HTML — embed anywhere",
    )

with dl4:
    try:
        svg_buf = io.BytesIO()
        fig.write_image(svg_buf, format="svg")
        st.download_button(
            "⬇️ Chart (SVG)",
            svg_buf.getvalue(),
            f"{indicator['id']}.svg",
            "image/svg+xml",
            use_container_width=True,
            help="Vector graphic — ideal for papers",
        )
    except Exception:
        st.button(
            "⬇️ SVG (install kaleido)",
            disabled=True,
            use_container_width=True,
            help="Run: pip install kaleido",
        )

# ── Reproduce this chart ──────────────────────────────────────────────────────

st.divider()

with st.expander("👩‍💻 Reproduce this chart — get the code"):
    _code_kwargs = dict(
        indicator          = indicator,
        selected_countries = _countries,
        year_range         = year_range,
        chart_type         = chart_type,
        map_year           = map_year,
        bar_year           = bar_year,
        top_n              = top_n,
        log_scale          = log_scale,
        color_scale        = color_scale,
        chart_title        = chart_title,
    )

    tab_py, tab_r = st.tabs(["🐍 Python", "📦 R"])

    with tab_py:
        py_script = python_code(**_code_kwargs)
        st.code(py_script, language="python")
        st.download_button(
            "⬇️ Download .py",
            py_script,
            f"{indicator['id']}_chart.py",
            "text/x-python",
        )

    with tab_r:
        r_script = r_code(**_code_kwargs)
        st.code(r_script, language="r")
        st.download_button(
            "⬇️ Download .R",
            r_script,
            f"{indicator['id']}_chart.R",
            "text/plain",
        )

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    "<br><p style='text-align:center;color:#94A3B8;font-size:0.78rem'>"
    "Data: <a href='https://ourworldindata.org' target='_blank'>Our World in Data</a> · "
    "<a href='https://data.worldbank.org' target='_blank'>World Bank WDI</a> · "
    "Built with <a href='https://streamlit.io' target='_blank'>Streamlit</a> + "
    "<a href='https://plotly.com' target='_blank'>Plotly</a>"
    "</p>",
    unsafe_allow_html=True,
)
