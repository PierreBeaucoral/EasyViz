"""
Sub-national page: upload ADM1/ADM2 data for any country, fetch
boundaries from geoBoundaries, render a choropleth.
"""

from __future__ import annotations

import pandas as pd
import pycountry
import streamlit as st

from ..geo import fetch_admin_geojson, get_region_names, match_regions
from ..ui import download_buttons, hide_sidebar
from ..uploader import read_uploaded_file
from ..viz import make_admin_map


def render() -> None:
    hide_sidebar()

    _, col, _ = st.columns([1, 4, 1])
    with col:
        if st.button("← Back to home"):
            st.session_state.page = "home"
            st.rerun()

        st.markdown(
            "<h1 style='font-size:2rem;margin-top:20px'>🗺️ Sub-national Map</h1>"
            "<p style='color:#64748B'>Map any indicator at province / state / district level. "
            "Upload your data and the app fetches boundaries automatically.</p>",
            unsafe_allow_html=True,
        )

        # ── 1. Country & admin level ──────────────────────────────────────────
        st.markdown("### 1 · Select country and admin level")
        col_a, col_b = st.columns(2)

        with col_a:
            country_query = st.text_input(
                "Country name",
                placeholder="e.g. France, Nigeria, Brazil…",
            )
            country_obj = None
            iso3 = None
            if country_query:
                try:
                    country_obj = pycountry.countries.search_fuzzy(country_query)[0]
                    iso3 = country_obj.alpha_3
                    st.success(f"**{country_obj.name}** — ISO3: `{iso3}`")
                except LookupError:
                    st.error("Country not found. Try a different spelling.")

        with col_b:
            adm_level = st.radio(
                "Admin level",
                ["ADM1 — State / Province / Region", "ADM2 — District / County"],
                horizontal=False,
            )
            level = 1 if "ADM1" in adm_level else 2

        if not iso3:
            st.info("Enter a country name to continue.")
            return

        # ── 2. Fetch boundaries ───────────────────────────────────────────────
        st.markdown("### 2 · Fetch boundaries")
        with st.spinner(f"Downloading ADM{level} boundaries for **{country_obj.name}**…"):
            geojson = fetch_admin_geojson(iso3, level)

        if geojson is None:
            st.error(
                f"Could not download boundaries for **{country_obj.name}** ADM{level}. "
                "This country or level may not be available in geoBoundaries. "
                "Try ADM1 instead, or a different country."
            )
            return

        geojson_names = get_region_names(geojson)
        n_regions = len(geojson_names)
        st.success(f"**{n_regions}** regions found.")

        with st.expander(f"Available region names ({n_regions})", expanded=False):
            st.write(", ".join(geojson_names))

        # ── 3. Upload data ────────────────────────────────────────────────────
        st.markdown("### 3 · Upload your data")
        st.caption(
            f"Your CSV / Excel needs at least two columns: "
            f"an **ADM{level} name** column (just the region name) "
            f"and a **value** column. An optional **year** column is also supported."
        )

        uploaded = st.file_uploader(
            "Drop your file here",
            type=["csv", "xlsx", "xls"],
            key="subnational_upload",
            label_visibility="collapsed",
        )
        if not uploaded:
            st.info("Accepted formats: **CSV** · **XLSX / XLS**")
            return

        df_raw = read_uploaded_file(uploaded)
        if df_raw is None or df_raw.empty:
            st.error("Could not read the file.")
            return

        st.success(f"File read: **{df_raw.shape[0]:,}** rows × **{df_raw.shape[1]}** columns.")

        # ── 3b. Country filter ────────────────────────────────────────────────
        _country_kw = {"country", "pays", "nation", "countryname", "country_name"}
        _country_col = next(
            (c for c in df_raw.columns if c.lower().strip() in _country_kw), None,
        )
        if _country_col:
            available = sorted(df_raw[_country_col].dropna().unique().tolist())
            _preselect = country_obj.name if country_obj else None
            _default_idx = (
                available.index(_preselect)
                if _preselect and _preselect in available
                else 0
            )
            selected_country_filter = st.selectbox(
                f"Filter by country (`{_country_col}` column detected)",
                options=available,
                index=_default_idx,
            )
            df_raw = df_raw[df_raw[_country_col] == selected_country_filter].copy()
            st.caption(f"{len(df_raw):,} rows for **{selected_country_filter}**.")

        with st.expander("Preview (first 10 rows)", expanded=False):
            st.dataframe(df_raw.head(10), width="stretch")

        # ── 4. Column mapping ─────────────────────────────────────────────────
        st.markdown("### 4 · Map columns")
        st.caption(
            f"The **region column** should contain ADM{level} names. "
            "Fuzzy matching handles spelling variations automatically."
        )
        all_cols = list(df_raw.columns)

        _region_keywords = {"adm1", "adm2", "adm3", "region", "district",
                            "province", "state", "county", "municipality",
                            "department", "zone", "area", "name"}
        _auto_region = next(
            (c for c in all_cols if c.lower().strip() in _region_keywords),
            all_cols[0],
        )

        col_r, col_v, col_y = st.columns(3)
        with col_r:
            region_col = st.selectbox(
                f"ADM{level} name column", all_cols,
                index=all_cols.index(_auto_region),
            )
        with col_v:
            val_options = [c for c in all_cols if c != region_col]
            value_col = st.selectbox("Value column", val_options, index=0)
        with col_y:
            year_options = ["(none)"] + [c for c in all_cols if c not in (region_col, value_col)]
            year_col_sel = st.selectbox("Year column (optional)", year_options)
            year_col = None if year_col_sel == "(none)" else year_col_sel

        sel_year = None
        if year_col:
            years = sorted(df_raw[year_col].dropna().unique().tolist())
            if years:
                sel_year = st.select_slider(
                    "Select year to display",
                    options=years, value=years[-1],
                )

        # ── 5. Chart settings ─────────────────────────────────────────────────
        st.markdown("### 5 · Chart settings")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            ind_name = st.text_input("Indicator name", value=uploaded.name.rsplit(".", 1)[0])
            ind_unit = st.text_input("Unit", placeholder="e.g. % of population")
        with col_m2:
            color_scale = st.selectbox(
                "Color palette",
                ["Blues", "Viridis", "RdYlGn", "Plasma", "YlOrRd",
                 "Oranges", "Greens", "Cividis", "Turbo", "Reds"],
            )
            log_scale = st.checkbox("Logarithmic scale")

        if not st.button("📊  Build map", type="primary", width="stretch"):
            return

        # ── 6. Build ──────────────────────────────────────────────────────────
        df_work = df_raw[[region_col, value_col]].copy()
        df_work.columns = ["region", "value"]
        df_work["value"] = pd.to_numeric(df_work["value"], errors="coerce")

        if year_col and sel_year is not None:
            mask = df_raw[year_col] == sel_year
            df_work = df_work[mask.values]

        df_work = df_work.dropna(subset=["value"])

        user_regions = df_work["region"].unique().tolist()
        with st.spinner("Matching region names…"):
            mapping = match_regions(user_regions, geojson_names)

        matched = {k: v for k, v in mapping.items() if v is not None}
        unmatched = [k for k, v in mapping.items() if v is None]

        if unmatched:
            st.warning(
                f"**{len(unmatched)}** region(s) could not be matched and will be excluded: "
                + ", ".join(f"`{u}`" for u in unmatched[:10])
                + ("…" if len(unmatched) > 10 else "")
            )

        df_work["region"] = df_work["region"].map(matched)
        df_work = df_work.dropna(subset=["region"])

        if df_work.empty:
            st.error("No regions matched. Check that region names match the country's admin units.")
            return

        n_matched = df_work["region"].nunique()
        st.caption(
            f"Showing **{n_matched}** of {n_regions} regions · "
            + (f"Year: **{sel_year}**" if sel_year else "all years aggregated")
        )

        title_str = ind_name or "Sub-national Map"
        if sel_year:
            title_str += f" ({sel_year})"

        fig = make_admin_map(
            df_work, geojson=geojson,
            title=title_str, color_scale=color_scale,
            unit=ind_unit or "value", log_scale=log_scale,
            subtitle=country_obj.name, source=uploaded.name,
        )
        st.plotly_chart(fig, width="stretch")

        st.divider()
        download_buttons(fig, df_work, slug="subnational_map", include_svg=False)

        st.markdown(
            "<br><p style='text-align:center;color:#94A3B8;font-size:0.78rem'>"
            "Boundaries: <a href='https://www.geoboundaries.org' target='_blank'>geoBoundaries</a> · "
            "Built with Streamlit + Plotly</p>",
            unsafe_allow_html=True,
        )
