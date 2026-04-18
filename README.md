# EasyViz — Academic Development Data Explorer

A lightweight, reproducible explorer for **World Bank WDI** and **Our World in Data** indicators.
Built for researchers: every chart ships with a proper citation block, a fetch timestamp,
and one-click export of runnable Python / R / Quarto code that reproduces the result.

![python](https://img.shields.io/badge/python-3.10%2B-blue) ![license](https://img.shields.io/badge/license-MIT-green)

---

## What it is for

EasyViz is designed for applied economists, public-policy researchers and students who need to:

- Search across ~100 curated development indicators by keyword, not code
- Produce publication-quality charts (PNG / SVG / HTML) with a consistent academic layout
- Export a standalone **R** (tidyverse + WDI + ggplot2/plotly) or **Python** (pandas + plotly) script that
  reproduces the exact chart, with the data snapshot date pinned
- Upload their own CSV / XLSX (long or wide, any separator, any country-naming convention)
  and get the same viz / export tooling — including sub-national ADM1 / ADM2 maps
- Compare 2–5 indicators across countries with scatter, scatter-matrix, and correlation
  (Pearson **and** Spearman)

This is **not** a statistical platform. It does no inference, no causal claims, no model fitting
beyond descriptive overlays (OLS / LOESS). It is a *figure factory* for exploration and teaching.

---

## Install & run

```bash
# From source
git clone https://github.com/PierreBeaucoral/EasyViz
cd EasyViz
pip install -e .
streamlit run app.py
```

Or, just to run the app without installing:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Python ≥ 3.10 required.

---

## Academic features

| Feature | Where | Why it matters |
|---|---|---|
| Per-indicator citation panel with source URL, definition, WDI code, fetch date | Data page footer | Every number is citable; fetched metadata is live from WB API |
| Fetch timestamp embedded in all exported code | Exported `.py`, `.R`, `.qmd` | Reproducibility: re-running years later still targets the same snapshot |
| `connectgaps = FALSE` on line charts + observation markers | Line charts | Missing observations are visible, not masked by line interpolation |
| Pearson **and** Spearman correlation toggle | Compare page | Non-normal variables (GDP, population) need rank correlation |
| WGI standard-error bands | Governance indicators | WGI ships point estimates with uncertainty; defaults now show both |
| OLS / LOESS overlay with R² | Scatter pages | Easy visual check of functional form |
| Regional presets (OECD, EU27, SSA, LMIC, LDC) | Country filters | Matches common paper samples |
| Package versions pinned in exported code | `sessionInfo()` / pip freeze | Reproducibility auditable |

---

## Project layout

```
EasyViz/
├── app.py                  # Thin router — routes pages, reads query params
├── src/
│   ├── catalog.py          # Indicator catalog (~100 entries, WDI + OWID)
│   ├── fetcher.py          # WDI + OWID fetch with typed errors and snapshot dates
│   ├── metadata.py         # WB indicator metadata + citation helpers
│   ├── geo.py              # Sub-national boundaries via geoBoundaries
│   ├── regions.py          # Regional country groups (OECD, SSA, EU27, …)
│   ├── search.py           # Fuzzy indicator search
│   ├── transforms.py       # Pure data transforms (% of max, rolling avg, rank, …)
│   ├── uploader.py         # CSV / XLSX ingestion + ISO3 resolution
│   ├── viz.py              # Plotly chart builders
│   ├── codegen.py          # R / Python / Quarto code export
│   ├── ui.py               # Shared Streamlit UI helpers
│   └── pages/
│       ├── home.py
│       ├── data.py
│       ├── upload.py
│       ├── compare.py
│       ├── subnational.py
│       └── about.py
└── tests/                  # pytest suite (transforms, uploader, search, codegen)
```

---

## Data sources and licences

- **World Bank World Development Indicators (WDI)** — free, CC-BY-4.0.
  API: `https://api.worldbank.org/v2/`
- **Our World in Data (OWID)** — mostly CC-BY; individual series may carry upstream licences.
  Grapher CSVs: `https://ourworldindata.org/grapher/{slug}.csv`
- **geoBoundaries** — CC-BY-4.0 for ADM1 / ADM2 boundaries (sub-national page).
  API: `https://www.geoboundaries.org/api/`

The app fetches on demand and caches locally (1 h for values, 24 h for boundaries).

---

## Citation

If EasyViz contributed to a published figure, please cite:

```bibtex
@software{beaucoral_easyviz_2026,
  author = {Beaucoral, Pierre},
  title  = {EasyViz: a reproducible explorer for development indicators},
  year   = {2026},
  url    = {https://github.com/PierreBeaucoral/EasyViz}
}
```

…and always cite the underlying data source (WDI / OWID / geoBoundaries) separately. The per-chart
citation panel inside the app gives you the exact string.

---

## Licence

MIT — see `LICENSE`.
