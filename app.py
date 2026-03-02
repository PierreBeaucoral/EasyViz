"""
DevViz — Development Data Explorer
Landing page + data explorer with OWID and World Bank data.
"""

import io

import streamlit as st

from src.catalog import INDICATORS
from src.codegen import python_code, quarto_code, r_code
from src.fetcher import fetch_data
from src.search import fuzzy_search
from src.uploader import detect_columns, detect_format, normalise, read_uploaded_file
from src.viz import (
    MAP_SCOPES, make_bar, make_box, make_corr_heatmap,
    make_histogram, make_line, make_map, make_scatter_matrix,
)

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

if "page" not in st.session_state:
    # Restore from URL query params on first load
    _qp = st.query_params
    _ind_id = _qp.get("ind")
    if _ind_id and any(r["id"] == _ind_id for r in INDICATORS):
        st.session_state.selected_id = _ind_id
        st.session_state.page = "data"
    else:
        st.session_state.selected_id = None
        st.session_state.page = "home"  # "home" | "about" | "data" | "upload" | "compare"
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

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        _, btn1, btn2, btn3, _ = st.columns([1, 1, 1, 1, 1])
        with btn1:
            if st.button("📤  Upload data", use_container_width=True):
                st.session_state.page = "upload"
                st.rerun()
        with btn2:
            if st.button("🔗  Compare", use_container_width=True):
                st.session_state.page = "compare"
                st.rerun()
        with btn3:
            if st.button("ℹ️  How it works", use_container_width=True):
                st.session_state.page = "about"
                st.rerun()

        st.markdown(
            "<p style='text-align:center;color:#CBD5E1;font-size:0.75rem;margin-top:24px'>"
            "Data: World Bank WDI</p>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# DATA PAGE
# ══════════════════════════════════════════════════════════════════════════════

def data_page():

    # ── Resolve indicator FIRST ───────────────────────────────────────────────
    current_id = st.session_state.selected_id
    is_custom  = (current_id == "__custom__")

    if is_custom:
        indicator = st.session_state.get("custom_indicator", {
            "id": "__custom__", "name": "Custom dataset",
            "category": "Custom", "source": "upload", "unit": "value", "tags": [],
        })
    else:
        indicator = next((r for r in INDICATORS if r["id"] == current_id), None)
        if indicator is None:
            st.error("Indicator not found — please go back and search again.")
            if st.button("← Back to home"):
                st.session_state.page = "home"
                st.session_state.selected_id = None
                st.rerun()
            return

    if indicator["source"] == "upload":
        src_label = "Your dataset"
        src_color = "#8B5CF6"
    elif indicator["source"] == "owid":
        src_label = "Our World in Data"
        src_color = "#10B981"
    else:
        src_label = "World Bank"
        src_color = "#3B82F6"

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<h1 style='color:#F1F5F9;font-size:1.4rem;margin-bottom:8px'>🌍 DevViz</h1>",
            unsafe_allow_html=True,
        )
        if st.button("← New search", use_container_width=True):
            st.session_state.selected_id = None
            st.session_state.page = "home"
            st.query_params.clear()
            st.rerun()
        if st.button("🔗 Compare indicators", use_container_width=True):
            st.session_state.page = "compare"
            st.rerun()

        st.divider()
        if is_custom:
            st.caption("📤 Custom uploaded dataset")
            if st.button("↑ Upload another file", use_container_width=True):
                st.session_state.page = "upload"
                st.session_state.selected_id = None
                st.rerun()
        else:
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
                st.query_params["ind"] = selected_id
                st.rerun()

        st.divider()
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
    if is_custom:
        df = st.session_state.get("custom_df")
    else:
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
    _yr_min, _yr_max = int(df["year"].min()), int(df["year"].max())
    m4.metric("Year range", "Cross-sectional" if _yr_min == _yr_max == 0 else f"{_yr_min} – {_yr_max}")
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
        if year_min < year_max:
            year_range = st.slider(
                "Year range",
                min_value=year_min, max_value=year_max,
                value=(max(year_min, year_max - 20), year_max),
            )
        else:
            year_range = (year_min, year_max)
            if year_min == 0:
                st.caption("No year column — cross-sectional data")
            else:
                st.caption(f"Year: **{year_min}**")

    _countries = selected_countries if selected_countries else all_countries
    filtered = df[
        df["entity"].isin(_countries)
        & df["year"].between(year_range[0], year_range[1])
    ]

    st.divider()

    # ── Chart controls ────────────────────────────────────────────────────────
    col_ctrl, col_chart = st.columns([1, 3])

    with col_ctrl:
        is_cross_sectional = (year_min == year_max)
        st.markdown('<div class="section-label">What to show?</div>', unsafe_allow_html=True)
        wizard = st.radio(
            "wizard",
            ["📍 Distribution", "📊 Ranking / Map", "📈 Trend over time"] if not is_cross_sectional
            else ["📍 Distribution", "📊 Ranking / Map"],
            label_visibility="collapsed",
            horizontal=True,
            key="chart_wizard",
        )
        st.markdown('<div class="section-label" style="margin-top:12px">Chart type</div>', unsafe_allow_html=True)
        if "Distribution" in wizard:
            _chart_opts = ["📊 Histogram", "📦 Box Plot"]
        elif "Trend" in wizard:
            _chart_opts = ["📈 Line Chart"]
        else:
            _chart_opts = ["🗺️ World Map", "📊 Bar Chart"]
        chart_type = st.radio(
            "chart_type",
            _chart_opts,
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

        # Always-defined vars (widgets shown conditionally)
        _AGG_OPTS = ["Mean", "Sum", "Median", "Min", "Max"]
        map_year       = year_range[1]
        map_mode       = "Single year"
        map_agg        = "Mean"
        map_scope_label = "🌍 World"
        bar_year       = year_range[1]
        bar_mode       = "Single year"
        bar_agg        = "Mean"
        top_n          = 20

        if "Map" in chart_type:
            map_scope_label = st.selectbox("Region", list(MAP_SCOPES.keys()), key="map_scope")
            map_mode = st.radio(
                "Map period", ["Single year", "Aggregate over range"],
                horizontal=True, key="map_mode",
            )
            if map_mode == "Single year":
                map_year = st.number_input(
                    "Year", min_value=year_min, max_value=year_max, value=year_range[1]
                )
            else:
                map_agg = st.selectbox("Aggregation", _AGG_OPTS, key="map_agg")

        if "Bar" in chart_type or "Histogram" in chart_type:
            bar_mode = st.radio(
                "Period", ["Single year", "Aggregate over range"],
                horizontal=True, key="bar_mode",
            )
            if bar_mode == "Single year":
                bar_year = st.number_input(
                    "Year",
                    min_value=year_range[0], max_value=year_range[1], value=year_range[1],
                )
            else:
                bar_agg = st.selectbox("Aggregation", _AGG_OPTS, key="bar_agg")
            if "Bar" in chart_type:
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

    # ── Period aggregation helper ─────────────────────────────────────────────
    _AGG_FUNCS = {"Mean": "mean", "Sum": "sum", "Median": "median",
                  "Min": "min", "Max": "max"}

    def _aggregate(data, agg_label):
        """Collapse all years into one row per country using the chosen function."""
        return (
            data.dropna(subset=["value"])
            .groupby(["entity", "iso3"], as_index=False)["value"]
            .agg(_AGG_FUNCS[agg_label])
        )

    def _period_label(agg_label):
        return f"{agg_label} {year_range[0]}–{year_range[1]}"

    # ── Build & display chart ─────────────────────────────────────────────────
    with col_chart:
        shared_kw = dict(
            log_scale=log_scale,
            subtitle=chart_subtitle,
            source=chart_source,
            xlabel=x_label,
            ylabel=y_label,
        )

        if "Map" in chart_type:
            if map_mode == "Single year":
                map_data  = df[df["year"] == map_year]
                map_title = chart_title
            else:
                map_data  = _aggregate(df[df["year"].between(*year_range)], map_agg)
                map_title = f"{chart_title} ({_period_label(map_agg)})"
            fig = make_map(
                map_data,
                title=map_title,
                color_scale=color_scale,
                indicator=indicator,
                log_scale=log_scale,
                subtitle=chart_subtitle,
                source=chart_source,
                scope=MAP_SCOPES[map_scope_label],
            )
        elif "Line" in chart_type:
            fig = make_line(filtered_t, title=chart_title, indicator=indicator_t, **shared_kw)
        elif "Histogram" in chart_type:
            if bar_mode == "Single year":
                hist_data  = filtered_t[filtered_t["year"] == bar_year]
                hist_title = f"{chart_title} — distribution ({bar_year})"
            else:
                hist_data  = _aggregate(filtered_t, bar_agg)
                hist_title = f"{chart_title} — distribution ({_period_label(bar_agg)})"
            fig = make_histogram(
                hist_data, title=hist_title, indicator=indicator_t,
                subtitle=chart_subtitle, source=chart_source,
                xlabel=x_label, ylabel=y_label,
            )
        elif "Box" in chart_type:
            fig = make_box(
                filtered_t, title=f"{chart_title} — distribution",
                indicator=indicator_t,
                subtitle=chart_subtitle, source=chart_source,
                xlabel=x_label, ylabel=y_label,
            )
        else:
            if bar_mode == "Single year":
                bar_data  = filtered_t[filtered_t["year"] == bar_year].sort_values("value", ascending=False)
                bar_title = f"{chart_title} ({bar_year})"
            else:
                bar_data  = _aggregate(filtered_t, bar_agg).sort_values("value", ascending=False)
                bar_title = f"{chart_title} ({_period_label(bar_agg)})"
            fig = make_bar(
                bar_data,
                title=bar_title,
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
    if not is_custom:
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
            tab_py, tab_r, tab_qmd = st.tabs(["🐍 Python", "📦 R", "📄 Quarto"])
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
            with tab_qmd:
                qmd_script = quarto_code(**_code_kw)
                st.code(qmd_script, language="markdown")
                st.download_button(
                    "⬇️ Download .qmd", qmd_script,
                    f"{indicator['id']}_chart.qmd", "text/plain",
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
# UPLOAD PAGE
# ══════════════════════════════════════════════════════════════════════════════

def upload_page():
    st.markdown("""
    <style>
    section[data-testid="stSidebar"]  { display: none !important; }
    [data-testid="collapsedControl"]   { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 3, 1])
    with col:
        if st.button("← Back to home"):
            st.session_state.page = "home"
            st.rerun()

        st.markdown(
            "<h1 style='font-size:2rem;margin-top:20px'>📤 Upload your data</h1>"
            "<p style='color:#64748B'>CSV or Excel — any structure. "
            "The app detects columns automatically; you confirm the mapping.</p>",
            unsafe_allow_html=True,
        )

        # ── Step 1: file upload ───────────────────────────────────────────────
        uploaded = st.file_uploader(
            "Drop your file here",
            type=["csv", "xlsx", "xls"],
            label_visibility="collapsed",
        )
        if not uploaded:
            st.info("Accepted formats: **CSV** (any separator) · **XLSX / XLS**")
            return

        df_raw = read_uploaded_file(uploaded)
        if df_raw is None or df_raw.empty:
            st.error("Could not read the file. Check that it is a valid CSV or Excel file.")
            return

        st.success(f"File read: **{df_raw.shape[0]:,}** rows × **{df_raw.shape[1]}** columns.")

        with st.expander("Preview (first 10 rows)", expanded=True):
            st.dataframe(df_raw.head(10), use_container_width=True)

        st.divider()

        # ── Step 2: format & column mapping ──────────────────────────────────
        st.markdown("### Column mapping")

        auto = detect_columns(df_raw)
        fmt  = detect_format(df_raw)

        col_a, col_b = st.columns(2)
        with col_a:
            fmt_choice = st.radio(
                "Data format",
                ["Long (one row per country-year)", "Wide (years as columns)"],
                index=0 if fmt == "long" else 1,
                help="**Long**: each row is one country × one year.  \n"
                     "**Wide**: each row is one country, years are column headers.",
            )
        is_wide = "Wide" in fmt_choice

        all_cols = list(df_raw.columns)

        with col_b:
            entity_is_iso3 = st.checkbox(
                "Country column already contains ISO3 codes",
                value=False,
                help="Tick this if your country column has codes like FRA, NGA, USA…",
            )

        c1, c2, c3 = st.columns(3)
        with c1:
            entity_col = st.selectbox(
                "Country / Entity column",
                all_cols,
                index=all_cols.index(auto["entity"]) if auto["entity"] in all_cols else 0,
            )
        with c2:
            if not is_wide:
                year_options = ["(none — single period)"] + all_cols
                year_default = auto["year"] if auto["year"] in all_cols else "(none — single period)"
                year_sel = st.selectbox("Year column", year_options,
                                        index=year_options.index(year_default))
                year_col = None if year_sel.startswith("(none") else year_sel
            else:
                st.info("Wide format: year columns are auto-detected from headers.")
                year_col = None

        with c3:
            if not is_wide:
                val_opts = auto["value_candidates"] or [c for c in all_cols
                                                         if c not in (entity_col, year_col)]
                value_col = st.selectbox(
                    "Value column",
                    val_opts if val_opts else all_cols,
                    index=0,
                )
            else:
                value_col = entity_col  # placeholder; wide path ignores this

        st.divider()

        # ── Step 3: indicator metadata ────────────────────────────────────────
        st.markdown("### Indicator info")
        m1, m2 = st.columns(2)
        with m1:
            ind_name = st.text_input("Indicator name", value=uploaded.name.rsplit(".", 1)[0])
        with m2:
            ind_unit = st.text_input("Unit", placeholder="e.g. % of population, USD per capita")

        st.divider()

        # ── Step 4: normalise & plot ──────────────────────────────────────────
        if st.button("📊  Plot it", type="primary", use_container_width=True):
            with st.spinner("Processing…"):
                df_norm = normalise(
                    df_raw,
                    entity_col=entity_col,
                    year_col=year_col,
                    value_col=value_col,
                    fmt="wide" if is_wide else "long",
                    entity_is_iso3=entity_is_iso3,
                )

            if df_norm.empty:
                st.error("No valid rows after processing. Check the column mapping.")
                return

            # Store in session state and navigate to data page
            st.session_state.custom_df = df_norm
            st.session_state.custom_indicator = {
                "id":        "__custom__",
                "name":      ind_name or "Custom dataset",
                "category":  "Custom",
                "source":    "upload",
                "unit":      ind_unit or "value",
                "tags":      [],
            }
            st.session_state.selected_id = "__custom__"
            st.session_state.page = "data"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ABOUT PAGE
# ══════════════════════════════════════════════════════════════════════════════

def about_page():
    # Hide sidebar
    st.markdown("""
    <style>
    section[data-testid="stSidebar"]  { display: none !important; }
    [data-testid="collapsedControl"]   { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 3, 1])
    with col:
        if st.button("← Back to home"):
            st.session_state.page = "home"
            st.rerun()

        st.markdown(
            "<h1 style='font-size:2.2rem;margin-top:24px'>🌍 DevViz</h1>"
            "<p style='color:#64748B;font-size:1.05rem;margin-bottom:32px'>"
            "A lightweight development data explorer — search, visualise, customise, download.</p>",
            unsafe_allow_html=True,
        )

        # ── How to use ───────────────────────────────────────────────────────
        st.markdown("## How to use it")
        steps = [
            ("🔍", "Search", "Type any topic on the home page — *child mortality*, *GDP*, *CO₂*, *poverty*. Results are ranked by relevance."),
            ("📤", "Or upload your own data", "Click **Upload data** to bring a CSV or Excel file. The app detects the structure automatically (long vs wide format, country and year columns). Cross-sectional data (no year column) is also supported."),
            ("📊", "Pick a chart", "Choose between a **World Map**, a **Line Chart** (countries over time), or a **Bar Chart** (country ranking for a given period). Line charts are hidden for cross-sectional data."),
            ("🌍", "Select countries & years", "Use the multiselect to choose which countries appear in Line and Bar charts. The year range slider filters all charts."),
            ("⚙️", "Customise", "Edit the title, add a subtitle, change the colour palette, toggle log scale, or relabel the axes."),
            ("🔄", "Transform", "Apply transformations to your data before plotting: normalise to % of max, compute % change vs first year, cumulative sum, rolling average, or rank."),
            ("📅", "Aggregate over periods", "For maps and bar charts, instead of picking a single year you can aggregate the whole selected period using mean, sum, median, min, or max."),
            ("⬇️", "Download", "Export the underlying data as **CSV**, the chart as **PNG**, **SVG** (vector, ideal for papers), or **HTML** (interactive, embeddable)."),
            ("👩‍💻", "Get the code", "Every built-in indicator comes with a ready-to-run **Python** and **R** script — open the *Reproduce this chart* panel at the bottom."),
        ]
        for icon, title, desc in steps:
            st.markdown(
                f"<div style='display:flex;gap:16px;margin-bottom:20px;align-items:flex-start'>"
                f"<div style='font-size:1.6rem;min-width:36px'>{icon}</div>"
                f"<div><strong>{title}</strong><br>"
                f"<span style='color:#475569'>{desc}</span></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Available indicators ──────────────────────────────────────────────
        st.markdown("## Available indicators")
        from src.catalog import INDICATORS, CATEGORIES

        for cat in CATEGORIES:
            icon = CAT_ICON.get(cat, "📊")
            inds = [i for i in INDICATORS if i["category"] == cat]
            with st.expander(f"{icon} {cat} — {len(inds)} indicators"):
                rows = []
                for ind in inds:
                    rows.append(f"**{ind['name']}** · *{ind['unit']}* · `{ind['indicator']}`")
                st.markdown("  \n".join(f"- {r}" for r in rows))

        st.divider()

        # ── Data sources ─────────────────────────────────────────────────────
        st.markdown("## Data sources")
        st.markdown("""
All built-in indicators come from the **World Bank World Development Indicators (WDI)** —
the most comprehensive cross-country development database, updated annually.

| Source | Coverage | Access |
|---|---|---|
| World Bank WDI | ~220 countries · 1960–2024 | Free, open API |
| Your own file | Any country · any year | CSV or Excel upload |

Data is fetched live on first use and cached for **1 hour** to keep the app responsive.
        """)

        st.divider()

        # ── Upload reference ──────────────────────────────────────────────────
        st.markdown("## Uploading your own data")
        st.markdown("""
Click **Upload data** on the home page to bring any CSV or Excel file. The app handles most real-world structures automatically.

**Supported formats**

| Format | Description | Example |
|---|---|---|
| **Long** | One row per country × year | `country, year, value` |
| **Wide** | One row per country, years as column headers | `country, 2000, 2001, …` |
| **Cross-sectional** | One row per country, no year column | `country, value` |

**Column mapping** is detected automatically but can be overridden. You can also tick *"Country column already contains ISO3 codes"* to skip name resolution entirely.

**Country name resolution** works in four steps, in order:

1. **ISO3 exact** — `FRA`, `NGA`, `USA` are used directly.
2. **ISO2 exact** — `FR`, `NG`, `US` are converted to ISO3.
3. **Normalised exact match** — accents, commas, and punctuation are stripped before matching, so `"Côte d'Ivoire"`, `"Korea, Rep."`, `"Lao PDR"` and `"Congo, Dem. Rep."` all resolve correctly.
4. **Fuzzy match** — remaining names are matched against the full country name database with a similarity threshold, catching typos and alternate spellings.

Countries that cannot be resolved are kept in Line and Bar charts but will be invisible on the map (no ISO3 code to place them).
        """)
        st.markdown("""
Available under *Transform data* in the Customise panel. Applied before plotting to Line and Bar charts.

| Transform | What it does | When to use it |
|---|---|---|
| **% of max** | Rescales all values 0–100, where 100 = the global maximum | Compare countries on different scales |
| **% change vs first year** | Growth relative to the first year in range | Track progress or divergence over time |
| **Cumulative sum** | Running total per country | Useful for flow variables (ODA, CO₂) |
| **Rolling avg (3 yr)** | 3-year moving average | Smooth out noisy annual data |
| **Rank** | 1 = highest value that year | Compare relative positions over time |
        """)

        st.divider()

        # ── Period aggregation reference ──────────────────────────────────────
        st.markdown("## Period aggregation (Map & Bar)")
        st.markdown("""
Instead of picking a single year, you can summarise across the whole selected period.

| Method | Formula | When to use it |
|---|---|---|
| **Mean** | Average value across years | Most indicators (stock variables) |
| **Sum** | Total accumulated over years | Flow variables (ODA, emissions) |
| **Median** | Middle value — robust to outliers | When a few extreme years skew the mean |
| **Min / Max** | Lowest or highest observed value | Identify best/worst periods |
        """)

        st.markdown(
            "<br><p style='text-align:center;color:#94A3B8;font-size:0.78rem'>"
            "Data: <a href='https://data.worldbank.org' target='_blank'>World Bank WDI</a> · "
            "Built with <a href='https://streamlit.io' target='_blank'>Streamlit</a> + "
            "<a href='https://plotly.com' target='_blank'>Plotly</a></p>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# COMPARE PAGE
# ══════════════════════════════════════════════════════════════════════════════

def compare_page():
    st.markdown("""
    <style>
    section[data-testid="stSidebar"]  { display: none !important; }
    [data-testid="collapsedControl"]   { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 4, 1])
    with col:
        if st.button("← Back to home"):
            st.session_state.page = "home"
            st.rerun()

        st.markdown(
            "<h1 style='font-size:2rem;margin-top:20px'>🔗 Compare indicators</h1>"
            "<p style='color:#64748B'>Select 2–5 indicators to explore correlations "
            "across countries — no equations, just patterns.</p>",
            unsafe_allow_html=True,
        )

        # ── Indicator multiselect ──────────────────────────────────────────────
        ind_by_name = {r["name"]: r for r in INDICATORS}
        default_names = [
            n for n in ["GDP per Capita, PPP (constant 2017 USD)", "Life Expectancy at Birth"]
            if n in ind_by_name
        ]
        selected_names = st.multiselect(
            "Choose 2–5 indicators to compare",
            options=list(ind_by_name.keys()),
            default=default_names,
            max_selections=5,
        )

        if len(selected_names) < 2:
            st.info("Pick at least 2 indicators to compare.")
            return

        selected_inds = [ind_by_name[n] for n in selected_names]

        # ── Fetch data ─────────────────────────────────────────────────────────
        dfs = {}
        with st.spinner("Loading data…"):
            for ind in selected_inds:
                df_i = fetch_data(ind)
                if df_i is not None and not df_i.empty:
                    df_i = df_i[df_i["iso3"].notna() & (df_i["iso3"].str.len() == 3)]
                    dfs[ind["id"]] = (df_i, ind)

        if len(dfs) < 2:
            st.error("Could not load enough data. Try different indicators.")
            return

        # ── Filters ────────────────────────────────────────────────────────────
        all_years = sorted({
            y for df_i, _ in dfs.values() for y in df_i["year"].unique() if y > 0
        })

        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            all_countries = sorted({
                c for df_i, _ in dfs.values() for c in df_i["entity"].unique()
            })
            default_sel = [c for c in DEFAULT_COUNTRIES if c in all_countries]
            selected_countries = st.multiselect(
                "Countries",
                options=all_countries,
                default=default_sel[:30],
            )

        # defaults so variables are always defined
        year_mode = "Single year"
        sel_year  = all_years[-1] if all_years else 0
        yr_range  = (all_years[max(0, len(all_years) - 20)], all_years[-1]) if all_years else (0, 0)
        yr_label  = str(sel_year)

        with col_f2:
            if all_years:
                year_mode = st.radio(
                    "Period", ["Single year", "Average over range"],
                    horizontal=True,
                )
                if year_mode == "Single year":
                    sel_year = st.selectbox("Year", sorted(all_years, reverse=True))
                    yr_label = str(sel_year)
                else:
                    yr_range = st.select_slider(
                        "Year range",
                        options=all_years,
                        value=(
                            all_years[max(0, len(all_years) - 20)],
                            all_years[-1],
                        ),
                    )
                    yr_label = f"avg {yr_range[0]}–{yr_range[1]}"

        # ── Build wide dataframe ───────────────────────────────────────────────
        _countries = selected_countries if selected_countries else all_countries
        col_ids, col_labels = [], []
        merged = None

        for ind_id, (df_i, ind) in dfs.items():
            df_i = df_i[df_i["entity"].isin(_countries)].copy()
            if year_mode == "Single year":
                df_i = df_i[df_i["year"] == sel_year][["entity", "iso3", "value"]].copy()
            else:
                df_i = (
                    df_i[df_i["year"].between(*yr_range)]
                    .groupby(["entity", "iso3"], as_index=False)["value"]
                    .mean()
                )
            df_i = df_i.rename(columns={"value": ind_id})
            col_ids.append(ind_id)
            col_labels.append(ind["name"])

            if merged is None:
                merged = df_i[["entity", "iso3", ind_id]]
            else:
                merged = merged.merge(
                    df_i[["entity", "iso3", ind_id]], on=["entity", "iso3"], how="inner"
                )

        if merged is None or merged.empty:
            st.warning("No data available for the selected combination.")
            return

        merged = merged.dropna(subset=col_ids, how="all")
        n_complete = merged.dropna(subset=col_ids).shape[0]
        st.caption(
            f"{n_complete} countries with complete data across all indicators · {yr_label}"
        )

        if n_complete < 3:
            st.warning(
                "Too few countries with complete data. Try a different year or fewer indicators."
            )
            return

        # ── Short labels for chart axes ────────────────────────────────────────
        short_labels = [n[:28] + "…" if len(n) > 28 else n for n in col_labels]

        # ── Three tabs: scatter matrix | heatmap | table ───────────────────────
        tab1, tab2, tab3 = st.tabs(
            ["📊 Scatter matrix", "🌡️ Correlation heatmap", "📋 Data table"]
        )

        with tab1:
            st.caption(
                "Each dot is a country. Axes show indicator values. "
                "Look for clusters and patterns — no equation needed."
            )
            fig1 = make_scatter_matrix(
                merged,
                indicator_cols=col_ids,
                col_labels=short_labels,
                title=f"Scatter matrix — {yr_label}",
                subtitle=" · ".join(short_labels),
                source="World Bank WDI",
            )
            st.plotly_chart(fig1, use_container_width=True)

        with tab2:
            st.caption(
                "Pearson r: +1 = perfect positive, –1 = perfect negative, 0 = no linear association."
            )
            fig2 = make_corr_heatmap(
                merged,
                indicator_cols=col_ids,
                col_labels=short_labels,
                title=f"Correlation matrix — {yr_label}",
                subtitle=" · ".join(short_labels),
                source="World Bank WDI",
            )
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            display_df = merged.rename(columns=dict(zip(col_ids, col_labels)))
            display_df = display_df.sort_values(col_labels[0])
            st.dataframe(
                display_df[["entity"] + col_labels].rename(columns={"entity": "Country"}),
                use_container_width=True,
                height=420,
            )
            st.download_button(
                "⬇️ Download data (CSV)",
                display_df.to_csv(index=False),
                "comparison.csv",
                "text/csv",
            )

        st.markdown(
            "<br><p style='text-align:center;color:#94A3B8;font-size:0.78rem'>"
            "Data: <a href='https://data.worldbank.org' target='_blank'>World Bank WDI</a> · "
            "Built with Streamlit + Plotly</p>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.page == "about":
    about_page()
elif st.session_state.page == "upload":
    upload_page()
elif st.session_state.page == "compare":
    compare_page()
elif st.session_state.selected_id is not None:
    st.session_state.page = "data"
    data_page()
else:
    st.session_state.page = "home"
    home_page()
