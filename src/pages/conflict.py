"""
Conflict & humanitarian data page.

Two loaders:
  * UCDP GED event-level data for a chosen country / period.
  * HDX CSV URL paste for ad-hoc humanitarian datasets.

Both sit behind the same page so users have a single entry point for
"quick-look conflict and humanitarian panels".
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..conflict import ConflictFetchError, fetch_hdx_csv, fetch_ucdp
from ..ui import hide_sidebar


def render() -> None:
    hide_sidebar()

    _, col, _ = st.columns([1, 4, 1])
    with col:
        if st.button("← Back to home"):
            st.session_state.page = "home"
            st.rerun()

        st.markdown(
            "<h1 style='font-size:2rem;margin-top:20px'>⚔️ Conflict & humanitarian data</h1>"
            "<p style='color:#64748B'>Two sources, no API key needed: "
            "UCDP Georeferenced Events and HDX CSV resources.</p>",
            unsafe_allow_html=True,
        )

        tab_ucdp, tab_hdx = st.tabs(["📍 UCDP GED", "📦 HDX CSV paste"])

        # ── UCDP ──────────────────────────────────────────────────────────────
        with tab_ucdp:
            st.caption(
                "Uppsala Conflict Data Program — Georeferenced Event Dataset. "
                "Every event has a date, country, estimated fatalities, and "
                "latitude/longitude. Source: "
                "[ucdp.uu.se](https://ucdp.uu.se)."
            )
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                country = st.text_input(
                    "Country (exact name, as UCDP uses it)",
                    placeholder="e.g. Nigeria, Mali, Afghanistan",
                )
            with c2:
                yr_from = st.number_input("From year", min_value=1989,
                                          max_value=2025, value=2015)
            with c3:
                yr_to = st.number_input("To year", min_value=1989,
                                        max_value=2025, value=2023)

            if not country:
                st.info("Enter a country to fetch UCDP events.")
            elif yr_from > yr_to:
                st.error("`From` year must be ≤ `To` year.")
            else:
                try:
                    with st.spinner(f"Fetching UCDP events for {country}…"):
                        res = fetch_ucdp(country=country,
                                         year_from=int(yr_from),
                                         year_to=int(yr_to))
                except ConflictFetchError as e:
                    st.error(f"UCDP fetch failed: {e}")
                else:
                    _render_ucdp(res.df, country, int(yr_from), int(yr_to))

        # ── HDX CSV ───────────────────────────────────────────────────────────
        with tab_hdx:
            st.caption(
                "Paste a direct CSV URL from "
                "[data.humdata.org](https://data.humdata.org). "
                "Right-click a resource → Copy Link."
            )
            url = st.text_input(
                "HDX CSV URL",
                placeholder="https://data.humdata.org/dataset/…/download/…csv",
            )
            if url:
                try:
                    with st.spinner("Fetching CSV from HDX…"):
                        df = fetch_hdx_csv(url)
                except ConflictFetchError as e:
                    st.error(f"HDX fetch failed: {e}")
                else:
                    st.success(f"Loaded **{df.shape[0]:,}** rows · "
                               f"**{df.shape[1]}** columns.")
                    st.dataframe(df.head(100), width="stretch", height=420)
                    st.download_button(
                        "⬇️ Download as CSV",
                        df.to_csv(index=False),
                        "hdx_extract.csv",
                        "text/csv",
                    )


def _render_ucdp(df: pd.DataFrame, country: str,
                 yr_from: int, yr_to: int) -> None:
    st.success(f"**{len(df):,}** events in **{country}**, {yr_from}–{yr_to}.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Events", f"{len(df):,}")
    if "best" in df.columns:
        m2.metric("Fatalities (best est.)", f"{int(df['best'].sum()):,}")
    if "year" in df.columns:
        m3.metric("Years covered", df["year"].nunique())

    st.markdown("#### Yearly fatalities")
    if "year" in df.columns and "best" in df.columns:
        yearly = (
            df.dropna(subset=["year"])
              .groupby("year", as_index=False)["best"].sum()
              .sort_values("year")
        )
        st.bar_chart(yearly, x="year", y="best", height=280)

    if "latitude" in df.columns and "longitude" in df.columns:
        st.markdown("#### Event map")
        pts = df.rename(columns={"latitude": "lat", "longitude": "lon"})
        pts = pts.dropna(subset=["lat", "lon"])
        if not pts.empty:
            st.map(pts[["lat", "lon"]], zoom=4, size=4)

    st.markdown("#### Raw events (first 100 rows)")
    st.dataframe(df.head(100), width="stretch", height=420)
    st.download_button(
        "⬇️ Download full event set (CSV)",
        df.to_csv(index=False),
        f"ucdp_{country.lower().replace(' ', '_')}_{yr_from}_{yr_to}.csv",
        "text/csv",
    )
