"""
Compare page: select 2–5 indicators, cross-tabulate across countries,
render scatter / scatter-matrix / correlation heatmap / data table.

Fetches indicators in parallel via `fetch_many`. Correlation method
toggles between Pearson (default) and Spearman (rank).
"""

from __future__ import annotations

import streamlit as st

from ..catalog import INDICATORS
from ..fetcher import fetch_many
from ..regions import DEFAULT, PRESETS, resolve_preset
from ..ui import hide_sidebar
from ..viz import make_corr_heatmap, make_gapminder, make_scatter, make_scatter_matrix


def render() -> None:
    hide_sidebar()

    _, col, _ = st.columns([1, 4, 1])
    with col:
        if st.button("← Back to home"):
            st.session_state.page = "home"
            st.rerun()

        st.markdown(
            "<h1 style='font-size:2rem;margin-top:20px'>🔗 Compare indicators</h1>"
            "<p style='color:#64748B'>Select 2–5 indicators to explore patterns across countries.</p>",
            unsafe_allow_html=True,
        )

        # ── Select indicators ─────────────────────────────────────────────────
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

        # ── Parallel fetch ────────────────────────────────────────────────────
        with st.spinner(f"Loading {len(selected_inds)} indicators in parallel…"):
            results = fetch_many(selected_inds)

        if len(results) < 2:
            st.error(
                "Could not load enough data. The following indicators failed: "
                + ", ".join(ind["name"] for ind in selected_inds if ind["id"] not in results)
            )
            return

        # Attach the catalog dict + snapshot to each fetched frame for convenience
        dfs: dict[str, tuple] = {}
        snapshots = []
        for ind in selected_inds:
            if ind["id"] not in results:
                st.warning(f"Skipped **{ind['name']}** — fetch failed.")
                continue
            res = results[ind["id"]]
            df_i = res.df[res.df["iso3"].notna() & (res.df["iso3"].str.len() == 3)]
            dfs[ind["id"]] = (df_i, ind)
            snapshots.append(res.snapshot)

        if snapshots:
            st.caption(
                f"📡 Data fetched {min(snapshots).strftime('%Y-%m-%d')} "
                f"(earliest of {len(snapshots)} series)"
            )

        # ── Filters ───────────────────────────────────────────────────────────
        all_years = sorted({
            y for df_i, _ in dfs.values() for y in df_i["year"].unique() if y > 0
        })
        all_countries = sorted({c for df_i, _ in dfs.values() for c in df_i["entity"].unique()})

        col_f1, col_f2, col_f3 = st.columns([1, 2, 1])
        with col_f1:
            preset = st.selectbox("Preset", list(PRESETS.keys()), index=0)
        with col_f2:
            default_sel = resolve_preset(preset, all_countries) or [
                c for c in DEFAULT if c in all_countries
            ][:30]
            selected_countries = st.multiselect(
                "Countries", options=all_countries, default=default_sel,
            )

        year_mode = "Single year"
        sel_year = all_years[-1] if all_years else 0
        yr_range = (all_years[max(0, len(all_years) - 20)], all_years[-1]) if all_years else (0, 0)
        yr_label = str(sel_year)

        with col_f3:
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
                        "Year range", options=all_years,
                        value=(all_years[max(0, len(all_years) - 20)], all_years[-1]),
                    )
                    yr_label = f"avg {yr_range[0]}–{yr_range[1]}"

        # ── Build wide DataFrame ──────────────────────────────────────────────
        _countries = selected_countries or all_countries
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
                    df_i[["entity", "iso3", ind_id]],
                    on=["entity", "iso3"], how="inner",
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
            st.warning("Too few countries with complete data. Try a different year or fewer indicators.")
            return

        short_labels = [n[:28] + "…" if len(n) > 28 else n for n in col_labels]

        # ── Tabs ──────────────────────────────────────────────────────────────
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Scatter", "🌡️ Correlation heatmap", "📋 Data table", "🎞️ Gapminder"]
        )

        with tab1:
            st.caption("Each dot is a country. Optional log axes and fit line below.")
            if len(col_ids) == 2:
                c1, c2, c3 = st.columns(3)
                with c1:
                    log_x = st.checkbox("log-X")
                with c2:
                    log_y = st.checkbox("log-Y")
                with c3:
                    fit = st.selectbox("Fit", ["None", "OLS", "LOESS"])
                fig1 = make_scatter(
                    merged, indicator_cols=col_ids, col_labels=short_labels,
                    title=f"Scatter — {yr_label}",
                    subtitle=" · ".join(short_labels),
                    source="World Bank WDI",
                    log_x=log_x, log_y=log_y, fit=fit,
                )
            else:
                fig1 = make_scatter_matrix(
                    merged, indicator_cols=col_ids, col_labels=short_labels,
                    title=f"Scatter matrix — {yr_label}",
                    subtitle=" · ".join(short_labels),
                    source="World Bank WDI",
                )
            st.plotly_chart(fig1, width="stretch")

        with tab2:
            method_label = st.radio(
                "Correlation method",
                ["Pearson (linear)", "Spearman (rank — robust to skew)"],
                horizontal=True,
                index=0,
            )
            method = "spearman" if method_label.startswith("Spearman") else "pearson"
            fig2 = make_corr_heatmap(
                merged, indicator_cols=col_ids, col_labels=short_labels,
                title=f"Correlation matrix — {yr_label}",
                subtitle=" · ".join(short_labels) + f" · method: {method}",
                source="World Bank WDI",
                method=method,
            )
            st.plotly_chart(fig2, width="stretch")
            st.caption(
                "Pearson measures linear association; Spearman measures monotonic "
                "(rank) association. Cross-country indicators are often skewed — "
                "Spearman is usually the safer default."
            )

        with tab3:
            display_df = merged.rename(columns=dict(zip(col_ids, col_labels, strict=False)))
            display_df = display_df.sort_values(col_labels[0])
            st.dataframe(
                display_df[["entity"] + col_labels].rename(columns={"entity": "Country"}),
                width="stretch", height=420,
            )
            st.download_button(
                "⬇️ Download data (CSV)",
                display_df.to_csv(index=False),
                "comparison.csv",
                "text/csv",
            )

        with tab4:
            st.caption(
                "Animated bubble chart: X / Y / optional bubble-size indicators. "
                "Hit ▶ to animate across years. Best with 2–3 indicators and 10–30 countries."
            )
            if len(col_ids) < 2:
                st.info("Pick at least 2 indicators to build a Gapminder view.")
            else:
                # Build panel (long) merged across years for the Gapminder view.
                panel = None
                for ind_id, (df_i, _ind) in dfs.items():
                    df_p = df_i[df_i["entity"].isin(_countries)][
                        ["entity", "iso3", "year", "value"]
                    ].rename(columns={"value": ind_id})
                    panel = df_p if panel is None else panel.merge(
                        df_p, on=["entity", "iso3", "year"], how="inner",
                    )
                panel = panel.dropna(subset=[col_ids[0], col_ids[1]])
                if panel.empty:
                    st.warning("No overlapping years across the selected indicators.")
                else:
                    g1, g2, g3, g4 = st.columns(4)
                    with g1:
                        x_axis = st.selectbox(
                            "X axis", options=col_ids,
                            format_func=lambda x: col_labels[col_ids.index(x)],
                            index=0, key="gap_x",
                        )
                    with g2:
                        _y_idx = 1 if len(col_ids) > 1 else 0
                        y_axis = st.selectbox(
                            "Y axis", options=col_ids,
                            format_func=lambda x: col_labels[col_ids.index(x)],
                            index=_y_idx, key="gap_y",
                        )
                    with g3:
                        size_choices = ["(none)"] + [c for c in col_ids if c not in (x_axis, y_axis)]
                        size_label = st.selectbox(
                            "Bubble size", options=size_choices,
                            format_func=lambda x: (
                                "None" if x == "(none)"
                                else col_labels[col_ids.index(x)]
                            ),
                            key="gap_size",
                        )
                        size_col = None if size_label == "(none)" else size_label
                    with g4:
                        log_x_gap = st.checkbox("log-X", key="gap_log_x")
                        log_y_gap = st.checkbox("log-Y", key="gap_log_y")

                    fig_gap = make_gapminder(
                        panel,
                        x_col=x_axis, y_col=y_axis, size_col=size_col,
                        x_label=col_labels[col_ids.index(x_axis)],
                        y_label=col_labels[col_ids.index(y_axis)],
                        size_label=(
                            "" if size_col is None
                            else col_labels[col_ids.index(size_col)]
                        ),
                        title="Gapminder-style animated scatter",
                        subtitle=f"{panel['year'].min()}–{panel['year'].max()} "
                                 f"· {panel['entity'].nunique()} countries",
                        source="World Bank WDI",
                        log_x=log_x_gap, log_y=log_y_gap,
                    )
                    st.plotly_chart(fig_gap, width="stretch")

        st.markdown(
            "<br><p style='text-align:center;color:#94A3B8;font-size:0.78rem'>"
            "Data: <a href='https://data.worldbank.org' target='_blank'>World Bank WDI</a> · "
            "Built with Streamlit + Plotly</p>",
            unsafe_allow_html=True,
        )
