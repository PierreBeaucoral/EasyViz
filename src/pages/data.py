"""
Data page: full indicator view with filters, chart, citation, downloads.
"""

from __future__ import annotations

import streamlit as st

from ..catalog import INDICATORS
from ..codegen import python_code, quarto_code, r_code
from ..fetcher import FetchError, fetch_data
from ..metadata import build_metadata
from ..regions import DEFAULT, PRESETS, resolve_preset
from ..search import fuzzy_search
from ..transforms import (
    AGG_CHOICES,
    TRANSFORM_CHOICES,
    aggregate_period,
    apply_transform,
    period_label,
)
from ..ui import citation_panel, download_buttons, source_pill
from ..urlstate import (
    get_bool,
    get_int_pair,
    get_list,
    set_bool,
    set_int_pair,
    set_list,
    set_param,
)
from ..viz import (
    MAP_SCOPES,
    make_bar,
    make_box,
    make_histogram,
    make_line,
    make_map,
)
from ..wdi_taxonomy import load_all as _load_full_wdi

CAT_ICON = {
    "Health": "🏥", "Economy": "💰", "Education": "📚",
    "Environment": "🌿", "Demographics": "👥", "Governance": "🏛️",
    "Custom": "📤",
}


def _resolve_indicator() -> dict | None:
    current_id = st.session_state.get("selected_id")
    if current_id == "__custom__":
        return st.session_state.get("custom_indicator", {
            "id": "__custom__", "name": "Custom dataset",
            "category": "Custom", "source": "upload", "unit": "value", "tags": [],
        })
    hit = next((r for r in INDICATORS if r["id"] == current_id), None)
    if hit is not None:
        return hit
    # Fallback: auto-imported WDI taxonomy entries (ids prefixed with `wdi_`).
    if current_id and current_id.startswith("wdi_"):
        return next((r for r in _load_full_wdi() if r["id"] == current_id), None)
    return None


def _sidebar(indicator: dict, is_custom: bool) -> None:
    with st.sidebar:
        st.markdown(
            "<h1 style='color:#F1F5F9;font-size:1.4rem;margin-bottom:8px'>🌍 EasyViz</h1>",
            unsafe_allow_html=True,
        )
        if st.button("← New search", width="stretch"):
            st.session_state.selected_id = None
            st.session_state.page = "home"
            st.query_params.clear()
            st.rerun()
        if st.button("🔗 Compare indicators", width="stretch"):
            st.session_state.page = "compare"
            st.rerun()

        st.divider()
        if is_custom:
            st.caption("📤 Custom uploaded dataset")
            if st.button("↑ Upload another file", width="stretch"):
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
        st.markdown(source_pill(indicator["source"]), unsafe_allow_html=True)
        st.markdown(f"<br>**Unit:** {indicator['unit']}", unsafe_allow_html=True)
        st.markdown(
            f"**Category:** {CAT_ICON.get(indicator['category'], '📊')} {indicator['category']}"
        )


def render() -> None:
    indicator = _resolve_indicator()
    is_custom = indicator is not None and indicator.get("id") == "__custom__"

    if indicator is None:
        st.error("Indicator not found — please go back and search again.")
        if st.button("← Back to home"):
            st.session_state.page = "home"
            st.session_state.selected_id = None
            st.rerun()
        return

    _sidebar(indicator, is_custom)

    # ── Load data ─────────────────────────────────────────────────────────────
    snapshot = None
    if is_custom:
        df = st.session_state.get("custom_df")
    else:
        try:
            with st.spinner(f"Loading **{indicator['name']}**…"):
                result = fetch_data(indicator)
            df = result.df
            snapshot = result.snapshot
        except FetchError as e:
            _render_fetch_failure(indicator, str(e))
            return

    if df is None or df.empty:
        _render_fetch_failure(indicator, "Upstream returned no data.")
        return

    df = df[df["iso3"].notna() & (df["iso3"].str.len() == 3)]

    # ── Header + metric strip ─────────────────────────────────────────────────
    st.markdown(f"## {CAT_ICON.get(indicator['category'], '📊')} {indicator['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Source", {"wdi": "World Bank", "owid": "OWID", "upload": "Upload"}.get(
        indicator["source"], indicator["source"]))
    m2.metric("Unit", indicator["unit"])
    m3.metric("Countries", df["entity"].nunique())
    _yr_min, _yr_max = int(df["year"].min()), int(df["year"].max())
    m4.metric(
        "Year range",
        "Cross-sectional" if _yr_min == _yr_max == 0 else f"{_yr_min} – {_yr_max}",
    )

    if snapshot is not None:
        st.caption(f"📡 Fetched {snapshot.strftime('%Y-%m-%d %H:%M UTC')} · cached 1 h")

    st.divider()

    # ── Filters (URL-restored defaults) ───────────────────────────────────────
    all_countries = sorted(df["entity"].unique().tolist())
    _url_countries = [c for c in get_list("countries") if c in all_countries]
    _url_years = get_int_pair("years")
    _url_log = get_bool("log")

    col_p, col_c, col_y = st.columns([1, 3, 1])
    with col_p:
        preset = st.selectbox("Preset", list(PRESETS.keys()), index=0)
    with col_c:
        default_sel = _url_countries or resolve_preset(preset, all_countries) or [
            c for c in DEFAULT if c in all_countries
        ][:15]
        selected_countries = st.multiselect(
            "Countries (Line & Bar)",
            options=all_countries,
            default=default_sel,
        )

    year_min, year_max = int(df["year"].min()), int(df["year"].max())
    with col_y:
        if year_min < year_max:
            _default_range = (max(year_min, year_max - 20), year_max)
            if _url_years and year_min <= _url_years[0] <= _url_years[1] <= year_max:
                _default_range = _url_years
            year_range = st.slider(
                "Year range",
                min_value=year_min, max_value=year_max,
                value=_default_range,
            )
        else:
            year_range = (year_min, year_max)
            st.caption(
                "No year column — cross-sectional data" if year_min == 0
                else f"Year: **{year_min}**"
            )

    _countries = selected_countries or all_countries
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
        st.markdown(
            '<div class="section-label" style="margin-top:12px">Chart type</div>',
            unsafe_allow_html=True,
        )
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
            options=TRANSFORM_CHOICES,
        )

        st.markdown(
            '<div class="section-label" style="margin-top:16px">Customise</div>',
            unsafe_allow_html=True,
        )
        chart_title = st.text_input("Title", value=indicator["name"])
        chart_subtitle = st.text_input("Subtitle", placeholder="e.g. 2000–2023, Sub-Saharan Africa")
        chart_source = st.text_input(
            "Source note",
            value={"wdi": "World Bank WDI", "owid": "Our World in Data",
                   "upload": "Your dataset"}.get(indicator["source"], "Source"),
            help="Footnote shown at the bottom of the chart",
        )
        ax1, ax2 = st.columns(2)
        with ax1:
            x_label = st.text_input("X label", placeholder="Year")
        with ax2:
            y_label = st.text_input("Y label", placeholder=indicator["unit"])
        log_scale = st.checkbox("Logarithmic scale", value=_url_log)
        color_scale = st.selectbox(
            "Color palette",
            ["Blues", "Viridis", "RdYlGn", "Plasma", "YlOrRd",
             "Oranges", "Greens", "Cividis", "Turbo", "Reds"],
        )

        map_year = year_range[1]
        map_mode = "Single year"
        map_agg = "Mean"
        map_scope_label = "🌍 World"
        bar_year = year_range[1]
        bar_mode = "Single year"
        bar_agg = "Mean"
        top_n = 20

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
                map_agg = st.selectbox("Aggregation", AGG_CHOICES, key="map_agg")

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
                bar_agg = st.selectbox("Aggregation", AGG_CHOICES, key="bar_agg")
            if "Bar" in chart_type:
                top_n = st.slider("Top N countries", 5, 50, 20)

    # ── Apply transform ───────────────────────────────────────────────────────
    filtered_t, unit_label = apply_transform(filtered, transform, indicator["unit"])
    indicator_t = {**indicator, "unit": unit_label}

    # ── Build chart ───────────────────────────────────────────────────────────
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
                map_data = df[df["year"] == map_year]
                map_title = chart_title
            else:
                map_data = aggregate_period(df[df["year"].between(*year_range)], map_agg)
                map_title = f"{chart_title} ({period_label(map_agg, *year_range)})"
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
                hist_data = filtered_t[filtered_t["year"] == bar_year]
                hist_title = f"{chart_title} — distribution ({bar_year})"
            else:
                hist_data = aggregate_period(filtered_t, bar_agg)
                hist_title = f"{chart_title} — distribution ({period_label(bar_agg, *year_range)})"
            fig = make_histogram(
                hist_data, title=hist_title, indicator=indicator_t,
                color_scale=color_scale,
                subtitle=chart_subtitle, source=chart_source,
                xlabel=x_label, ylabel=y_label,
            )
        elif "Box" in chart_type:
            fig = make_box(
                filtered_t, title=f"{chart_title} — distribution",
                indicator=indicator_t,
                color_scale=color_scale,
                subtitle=chart_subtitle, source=chart_source,
                xlabel=x_label, ylabel=y_label,
            )
        else:  # Bar
            if bar_mode == "Single year":
                bar_data = filtered_t[filtered_t["year"] == bar_year].sort_values(
                    "value", ascending=False)
                bar_title = f"{chart_title} ({bar_year})"
            else:
                bar_data = aggregate_period(filtered_t, bar_agg).sort_values(
                    "value", ascending=False)
                bar_title = f"{chart_title} ({period_label(bar_agg, *year_range)})"
            fig = make_bar(
                bar_data, title=bar_title, color_scale=color_scale,
                top_n=top_n, indicator=indicator_t, **shared_kw,
            )
        st.plotly_chart(fig, width="stretch")

    # ── Persist view state to URL (bookmarkable) ──────────────────────────────
    set_param("ind", indicator["id"])
    set_list("countries", selected_countries)
    if year_min < year_max:
        set_int_pair("years", (int(year_range[0]), int(year_range[1])))
    set_param("chart", chart_type.split(" ", 1)[-1] if " " in chart_type else chart_type)
    set_param("tf", transform)
    set_bool("log", bool(log_scale))

    # ── Citation panel ────────────────────────────────────────────────────────
    if not is_custom:
        st.divider()
        meta = build_metadata(indicator, snapshot=snapshot)
        citation_panel(meta)

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Download**")
    download_buttons(fig, filtered, slug=indicator["id"])

    # ── Reproduce this chart ──────────────────────────────────────────────────
    if not is_custom:
        st.divider()
        with st.expander("👩‍💻 Reproduce this chart — get the code"):
            code_kw = dict(
                indicator=indicator,
                selected_countries=_countries,
                year_range=year_range,
                chart_type=chart_type,
                map_year=int(map_year),
                bar_year=int(bar_year),
                top_n=top_n,
                log_scale=log_scale,
                color_scale=color_scale,
                chart_title=chart_title,
                snapshot=snapshot,
            )
            tab_py, tab_r_gg, tab_r_pl, tab_qmd = st.tabs(
                ["🐍 Python", "📦 R (ggplot2)", "📦 R (plotly)", "📄 Quarto"]
            )
            with tab_py:
                py_script = python_code(**code_kw)
                st.code(py_script, language="python")
                st.download_button(
                    "⬇️ Download .py", py_script,
                    f"{indicator['id']}_chart.py", "text/x-python",
                )
            with tab_r_gg:
                r_script_gg = r_code(**code_kw, flavour="ggplot2")
                st.code(r_script_gg, language="r")
                st.download_button(
                    "⬇️ Download .R", r_script_gg,
                    f"{indicator['id']}_chart_ggplot.R", "text/plain",
                )
            with tab_r_pl:
                r_script_pl = r_code(**code_kw, flavour="plotly")
                st.code(r_script_pl, language="r")
                st.download_button(
                    "⬇️ Download .R", r_script_pl,
                    f"{indicator['id']}_chart_plotly.R", "text/plain",
                )
            with tab_qmd:
                qmd_script = quarto_code(**code_kw, flavour="ggplot2")
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


def _render_fetch_failure(indicator: dict, detail: str) -> None:
    st.error(
        f"**{indicator['name']}** could not be loaded.  \n"
        f"Reason: `{detail}`"
    )
    st.markdown("**Try a related indicator:**")
    alts = [
        r for r in INDICATORS
        if r["category"] == indicator["category"] and r["id"] != indicator["id"]
    ][:4]
    if alts:
        cols = st.columns(len(alts))
        for i, alt in enumerate(alts):
            with cols[i]:
                if st.button(
                    f"{CAT_ICON.get(alt['category'], '📊')} {alt['name']}",
                    width="stretch",
                    key=f"alt_{alt['id']}",
                ):
                    st.session_state.selected_id = alt["id"]
                    st.query_params["ind"] = alt["id"]
                    st.rerun()
