"""
About page: how to use EasyViz, catalog of indicators by category,
data-source table, upload reference, transforms & period aggregation reference.

Rendered from a single pure function `render()` so the router in
`app.py` can dispatch without knowing implementation details.
"""

from __future__ import annotations

import streamlit as st

from ..catalog import CATEGORIES, INDICATORS
from ..ui import hide_sidebar

CAT_ICON = {
    "Health": "🏥", "Economy": "💰", "Education": "📚",
    "Environment": "🌿", "Demographics": "👥", "Governance": "🏛️",
}

_STEPS = [
    ("🔍", "Search",
     "Type any topic on the home page — *child mortality*, *GDP*, *CO₂*, *poverty*. "
     "Results are ranked by relevance."),
    ("📤", "Or upload your own data",
     "Click **Upload data** to bring a CSV or Excel file. The app detects the structure "
     "automatically (long vs. wide format, country and year columns). Cross-sectional "
     "data (no year column) is also supported."),
    ("📊", "Pick a chart",
     "Choose between a **World Map**, a **Line Chart** (countries over time), or a "
     "**Bar Chart** (country ranking for a given period). Line charts are hidden for "
     "cross-sectional data."),
    ("🌍", "Select countries & years",
     "Use the multiselect to choose which countries appear in Line and Bar charts. "
     "The year range slider filters all charts."),
    ("⚙️", "Customise",
     "Edit the title, add a subtitle, change the colour palette, toggle log scale, "
     "or relabel the axes."),
    ("🔄", "Transform",
     "Apply transformations to your data before plotting: normalise to % of max, "
     "compute % change vs. first year, cumulative sum, rolling average, or rank."),
    ("📅", "Aggregate over periods",
     "For maps and bar charts, instead of picking a single year you can aggregate the "
     "whole selected period using mean, sum, median, min, or max."),
    ("⬇️", "Download",
     "Export the underlying data as **CSV**, the chart as **PNG**, **SVG** (vector, "
     "ideal for papers), or **HTML** (interactive, embeddable)."),
    ("👩‍💻", "Reproduce the analysis",
     "Every built-in indicator comes with ready-to-run **Python**, **R (ggplot2)**, "
     "**R (plotly)** and **Quarto** scripts that replicate the chart from the raw "
     "World Bank / OWID API — open the *Reproduce this chart* panel."),
]


def render() -> None:
    hide_sidebar()

    _, col, _ = st.columns([1, 3, 1])
    with col:
        if st.button("← Back to home"):
            st.session_state.page = "home"
            st.rerun()

        st.markdown(
            "<h1 style='font-size:2.2rem;margin-top:24px'>🌍 EasyViz</h1>"
            "<p style='color:#64748B;font-size:1.05rem;margin-bottom:32px'>"
            "A lightweight development-data explorer — search, visualise, customise, "
            "download, and reproduce.</p>",
            unsafe_allow_html=True,
        )

        # ── How to use ───────────────────────────────────────────────────────
        st.markdown("## How to use it")
        for icon, title, desc in _STEPS:
            st.markdown(
                f"<div style='display:flex;gap:16px;margin-bottom:20px;align-items:flex-start'>"
                f"<div style='font-size:1.6rem;min-width:36px'>{icon}</div>"
                f"<div><strong>{title}</strong><br>"
                f"<span style='color:#475569'>{desc}</span></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Available indicators ─────────────────────────────────────────────
        st.markdown("## Available indicators")
        for cat in CATEGORIES:
            icon = CAT_ICON.get(cat, "📊")
            inds = [i for i in INDICATORS if i["category"] == cat]
            with st.expander(f"{icon} {cat} — {len(inds)} indicators"):
                rows = [
                    f"**{ind['name']}** · *{ind['unit']}* · `{ind['indicator']}`"
                    for ind in inds
                ]
                st.markdown("  \n".join(f"- {r}" for r in rows))

        st.divider()

        # ── Data sources ─────────────────────────────────────────────────────
        st.markdown("## Data sources")
        st.markdown(
            """
Built-in indicators are drawn from two widely-used open databases:

| Source | Coverage | Access | Update cycle |
|---|---|---|---|
| **World Bank — WDI** | ~220 countries · 1960–present | Free, open API (no key) | Annual |
| **Our World in Data** | Harmonised cross-country indicators | Public CSV exports | Rolling |
| Your own file | Any country · any year | CSV or Excel upload | On upload |

Data is fetched live on first use and cached for **1 hour**. Every chart carries the
fetch timestamp and a ready-to-copy APA/BibTeX citation — see the
*How to cite this indicator* panel on any indicator page.
"""
        )

        st.divider()

        # ── Upload reference ─────────────────────────────────────────────────
        st.markdown("## Uploading your own data")
        st.markdown(
            """
Click **Upload data** on the home page to bring any CSV or Excel file. The app handles
most real-world structures automatically.

**Supported formats**

| Format | Description | Example |
|---|---|---|
| **Long** | One row per country × year | `country, year, value` |
| **Wide** | One row per country, years as column headers | `country, 2000, 2001, …` |
| **Cross-sectional** | One row per country, no year column | `country, value` |

**Column mapping** is detected automatically but can be overridden. Tick *"Country
column already contains ISO3 codes"* to skip name resolution entirely.

**Country-name resolution** — four-step pipeline, in order:

1. **ISO3 exact** — `FRA`, `NGA`, `USA` are used directly.
2. **ISO2 exact** — `FR`, `NG`, `US` are converted to ISO3.
3. **Normalised exact match** — accents, commas, and punctuation are stripped so
   `"Côte d'Ivoire"`, `"Korea, Rep."`, `"Lao PDR"`, `"Congo, Dem. Rep."` all resolve.
4. **Fuzzy match** — remaining names matched against the full country database
   with a similarity threshold (catches typos and alternate spellings).

Unresolved countries stay in Line and Bar charts but are invisible on the map
(no ISO3 code to place them).
"""
        )

        st.divider()

        # ── Transforms reference ─────────────────────────────────────────────
        st.markdown("## Transforms (Line & Bar)")
        st.markdown(
            """
Available under *Transform data* in the Customise panel. Applied **before** plotting
to Line and Bar charts; the Map always shows raw values.

| Transform | What it does | When to use it |
|---|---|---|
| **% of max** | Rescales all values 0–100, where 100 = the global maximum | Compare countries on different scales |
| **% change vs. first year** | Growth relative to the first year in range | Track progress or divergence over time |
| **Cumulative sum** | Running total per country | Useful for flow variables (ODA, CO₂) |
| **Rolling avg (3 yr)** | 3-year moving average | Smooth out noisy annual data |
| **Rank** | 1 = highest value that year | Compare relative positions over time |
"""
        )

        st.divider()

        # ── Period aggregation reference ─────────────────────────────────────
        st.markdown("## Period aggregation (Map & Bar)")
        st.markdown(
            """
Instead of picking a single year, you can summarise across the whole selected period.

| Method | Formula | When to use it |
|---|---|---|
| **Mean** | Average value across years | Most indicators (stock variables) |
| **Sum** | Total accumulated over years | Flow variables (ODA, emissions) |
| **Median** | Middle value — robust to outliers | When a few extreme years skew the mean |
| **Min / Max** | Lowest or highest observed value | Identify best/worst periods |
"""
        )

        st.divider()

        # ── Reproducibility notice ───────────────────────────────────────────
        st.markdown("## Reproducibility")
        st.markdown(
            """
EasyViz is built for **academic reuse**. Every chart on the site can be regenerated
offline with the exported Python or R script — the code pins the fetch timestamp
in its header, uses the same client-side filtering as the app, and imports the
same indicator codes from the World Bank / OWID APIs.

- **Citation** — APA-style and BibTeX entries are generated from the live World
  Bank metadata endpoint, so the citation matches the current indicator definition.
- **Snapshots** — the footer of every downloaded script shows the date on which
  the data was fetched; re-running the script later will pull fresh data but keep
  the same code.
- **Sub-national maps** — boundaries come from [geoBoundaries](https://www.geoboundaries.org)
  (CC-BY 4.0); download the map GeoJSON directly from the Sub-national page to
  pin the administrative boundaries you used.
"""
        )

        st.markdown(
            "<br><p style='text-align:center;color:#94A3B8;font-size:0.78rem'>"
            "Data: <a href='https://data.worldbank.org' target='_blank'>World Bank WDI</a> · "
            "<a href='https://ourworldindata.org' target='_blank'>Our World in Data</a> · "
            "Built with <a href='https://streamlit.io' target='_blank'>Streamlit</a> + "
            "<a href='https://plotly.com' target='_blank'>Plotly</a></p>",
            unsafe_allow_html=True,
        )
