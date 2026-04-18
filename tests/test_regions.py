"""
Unit tests for `src.regions` — preset country groupings.
"""

from __future__ import annotations

from src.regions import (
    BRICS, DEFAULT, EU27, G7, LDC, LMIC, OECD, PRESETS, SSA, resolve_preset,
)


def test_presets_registry_covers_all_groups():
    assert set(PRESETS.keys()) >= {
        "Default (20 diverse)", "OECD (38)", "EU27", "Sub-Saharan Africa",
        "Low- & Middle-Income", "LDCs (UN)", "BRICS", "G7",
    }


def test_brics_has_five_members():
    assert len(BRICS) == 5
    assert "Brazil" in BRICS and "China" in BRICS


def test_g7_has_seven_members():
    assert len(G7) == 7


def test_oecd_excludes_non_member_countries():
    assert "China" not in OECD
    assert "Russia" not in OECD and "Russian Federation" not in OECD


def test_eu27_excludes_uk_post_brexit():
    assert "United Kingdom" not in EU27
    assert len(EU27) == 27


def test_ssa_contains_expected_countries():
    for c in ["Nigeria", "Kenya", "Ethiopia", "Ghana", "South Africa"]:
        assert c in SSA


def test_ldc_contains_expected_countries():
    assert "Afghanistan" in LDC
    assert "Haiti" in LDC


def test_default_sample_is_nontrivial():
    assert len(DEFAULT) >= 15
    assert "France" in DEFAULT


def test_resolve_preset_filters_by_availability():
    # Only 'France' and 'Germany' are in the available list → OECD
    # preset should return just those two.
    out = resolve_preset("OECD (38)", ["France", "Germany", "Atlantis"])
    assert set(out) == {"France", "Germany"}


def test_resolve_unknown_preset_returns_empty():
    assert resolve_preset("Nowhere", ["France"]) == []


def test_lmic_does_not_include_high_income_countries():
    # LMIC should be Low- and Middle-Income — high-income G7 members shouldn't appear.
    for c in ["United States", "Germany", "Japan"]:
        assert c not in LMIC
