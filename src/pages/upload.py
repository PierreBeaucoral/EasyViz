"""
Upload page: drag-and-drop CSV / XLSX, auto-detect column mapping,
normalise to the canonical schema, send the user to the data page.
"""

from __future__ import annotations

import streamlit as st

from ..ui import hide_sidebar
from ..uploader import detect_columns, detect_format, normalise, read_uploaded_file


def render() -> None:
    hide_sidebar()

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
            st.dataframe(df_raw.head(10), width="stretch")

        st.divider()

        st.markdown("### Column mapping")
        auto = detect_columns(df_raw)
        fmt = detect_format(df_raw)

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
                val_opts = auto["value_candidates"] or [
                    c for c in all_cols if c not in (entity_col, year_col)
                ]
                value_col = st.selectbox(
                    "Value column",
                    val_opts if val_opts else all_cols,
                    index=0,
                )
            else:
                value_col = entity_col

        st.divider()

        st.markdown("### Indicator info")
        m1, m2 = st.columns(2)
        with m1:
            ind_name = st.text_input("Indicator name", value=uploaded.name.rsplit(".", 1)[0])
        with m2:
            ind_unit = st.text_input("Unit", placeholder="e.g. % of population, USD per capita")

        st.divider()

        if st.button("📊  Plot it", type="primary", width="stretch"):
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

            st.session_state.custom_df = df_norm
            st.session_state.custom_indicator = {
                "id": "__custom__",
                "name": ind_name or "Custom dataset",
                "category": "Custom",
                "source": "upload",
                "unit": ind_unit or "value",
                "tags": [],
            }
            st.session_state.selected_id = "__custom__"
            st.session_state.page = "data"
            st.rerun()
