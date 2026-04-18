# Changelog

All notable changes to EasyViz are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CHANGELOG following Keep a Changelog.
- GitHub Actions CI running pytest + ruff on push/PR.
- Shared `requests.Session` with HTTP connection pooling, reused across
  `fetcher`, `metadata`, and `geo` for a measurable cold-start speedup.
- Confirmed lazy import of `statsmodels.lowess` inside `_fit_overlay`
  (was already deferred); documented as a boot-time guarantee.
- Disk-persistent fetch cache under `~/.cache/easyviz/` (parquet, TTL-checked),
  surviving container restarts on Streamlit Cloud.
- Full-state URL serialisation: country list, year range, chart type,
  transform, and log-scale are round-tripped via query params.
- Embed mode (`?embed=1`) that hides the navigation chrome for clean
  iframe embeds in blogs / Quarto reports.
- Animated Gapminder-style scatter: X / Y / optional size indicators,
  year slider, colour by region.
- Auto-imported WDI taxonomy (~1,500 indicators) grouped by topic via
  the World Bank metadata endpoint.
- UCDP GED conflict-events loader (no API key required).
- HDX CSV paste loader for ad-hoc humanitarian datasets.

## [0.2.0] — 2026-04-18

### Added
- Full project rebrand from DevViz to **EasyViz**.
- Academic-grade features: Pearson/Spearman correlation captions,
  OLS + LOESS trend overlays with R², BibTeX + APA citation export.
- Sub-national choropleths via geoBoundaries (ADM1 / ADM2) with
  automatic region-name fuzzy matching.
- Typed `GeoFetchError` with `reason` ∈ `{timeout, http, parse, unavailable}`
  for actionable user-facing error messages.
- ADM2 payload reduction: `subset_geojson` (keep only user-matched features)
  + `simplify_geojson` (Douglas–Peucker via shapely). Cuts 100 MB payloads
  to ~2 MB for interactive rendering.
- Upload + Compare + Sub-national pages; about page with full indicator
  catalogue grouped by category.
- Reproducible code export (Python + R) matching in-app semantics,
  including client-side year filtering so R output matches Python.
- Thin-router architecture (`app.py`) dispatching to `src/pages/<name>.py`
  `render()` functions.
- 101 pytest tests covering pure logic: transforms, search, uploader,
  codegen, regions, metadata, geo.

### Changed
- `pyproject.toml` → name `easyviz`, version `0.2.0`, homepage
  `https://github.com/PierreBeaucoral/EasyViz`.
- HTTP User-Agent standardised to
  `EasyViz/0.2 (+https://github.com/PierreBeaucoral/EasyViz)`.
- `transforms.py`: replaced deprecated `groupby().apply()` with an explicit
  per-group loop to silence pandas 2.2 DeprecationWarning.

### Fixed
- ADM2 intensive-rendering error: payload subsetting + simplification
  prevents browser-freeze for large countries.
- R code export now fetches the full WDI range then filters client-side
  so output matches Python semantics.

## [0.1.0] — initial release

### Added
- Streamlit explorer for World Bank WDI and OWID indicators.
- In-app line / bar charts, transforms, period aggregation,
  PNG / SVG / CSV download.
