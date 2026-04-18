"""
Unit tests for `src.metadata` — citation generation from catalog entries.

Network calls to the World Bank metadata API are mocked so tests run
offline in a deterministic order.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from src.metadata import IndicatorMetadata, build_metadata

# ── build_metadata: WDI path ──────────────────────────────────────────────────

def test_build_metadata_wdi_uses_live_when_available():
    live_mock = {
        "name": "Life expectancy at birth, total (years)",
        "sourceNote": "Life expectancy at birth indicates the number of years a newborn would live.",
        "sourceOrganization": "World Bank",
    }
    ind = {"id": "le", "name": "Life Expectancy at Birth", "indicator": "SP.DYN.LE00.IN", "source": "wdi"}

    with patch("src.metadata._fetch_wdi_metadata", return_value=live_mock):
        meta = build_metadata(ind)

    assert meta.code == "SP.DYN.LE00.IN"
    assert "newborn" in meta.definition
    assert meta.organisation == "World Bank"
    assert "data.worldbank.org/indicator/SP.DYN.LE00.IN" in meta.source_url


def test_build_metadata_wdi_falls_back_on_network_failure():
    ind = {"id": "le", "name": "Life Expectancy at Birth", "indicator": "SP.DYN.LE00.IN", "source": "wdi"}

    with patch("src.metadata._fetch_wdi_metadata", return_value={}):
        meta = build_metadata(ind)

    # Name falls back to the catalog value
    assert meta.name == "Life Expectancy at Birth"
    assert meta.organisation == "World Bank"
    assert "Definition not available" in meta.definition


# ── build_metadata: OWID path ─────────────────────────────────────────────────

def test_build_metadata_owid():
    ind = {
        "id": "extreme_poverty", "name": "Extreme Poverty",
        "slug": "share-of-population-in-extreme-poverty", "source": "owid",
    }
    meta = build_metadata(ind)
    assert meta.source_name == "Our World in Data"
    assert meta.organisation == "Our World in Data"
    assert "share-of-population-in-extreme-poverty" in meta.source_url


# ── build_metadata: upload path ───────────────────────────────────────────────

def test_build_metadata_upload_has_no_citable_source():
    ind = {"id": "__custom__", "name": "My upload", "source": "upload"}
    meta = build_metadata(ind)
    assert meta.source_url == ""
    assert meta.organisation == "User"
    assert "User-supplied" in meta.definition


# ── Citation formatting ───────────────────────────────────────────────────────

def _meta() -> IndicatorMetadata:
    return IndicatorMetadata(
        code="SH.DYN.MORT",
        name="Under-5 Mortality Rate",
        source_name="World Development Indicators",
        source_url="https://data.worldbank.org/indicator/SH.DYN.MORT",
        definition="Probability per 1000 that a newborn dies before age 5.",
        organisation="World Bank",
        snapshot=datetime(2026, 4, 18, tzinfo=timezone.utc),
    )


def test_citation_plain_is_apa_style():
    text = _meta().citation_plain()
    assert "World Bank" in text
    assert "2026-04-18" in text
    assert "SH.DYN.MORT" in text
    assert "https://data.worldbank.org/indicator/SH.DYN.MORT" in text


def test_citation_bibtex_has_expected_fields():
    bib = _meta().citation_bibtex()
    assert bib.startswith("@misc{wdi_sh_dyn_mort")
    assert "author" in bib
    assert "title" in bib
    assert "year   = { 2026 }" in bib
    assert "note   = { accessed 2026-04-18 }" in bib


def test_citation_bibtex_custom_key():
    bib = _meta().citation_bibtex(key="mortality_2024")
    assert bib.startswith("@misc{mortality_2024,")


def test_snapshot_str_is_iso_date():
    assert _meta().snapshot_str == "2026-04-18"
