"""
Unit tests for `src.search`.

The catalog is loaded once; we test that fuzzy search ranks relevant
indicators above irrelevant ones and handles empty queries correctly.
"""

from __future__ import annotations

import pytest

from src.catalog import INDICATORS
from src.search import fuzzy_search


def _first_name(query: str, limit: int = 5) -> list[str]:
    return [r["name"] for r in fuzzy_search(query, INDICATORS, limit=limit)]


def test_search_empty_query_returns_catalog_head():
    out = fuzzy_search("", INDICATORS, limit=3)
    assert len(out) == 3
    assert all("id" in r for r in out)


def test_search_ranks_mortality_query():
    names = _first_name("child mortality")
    # At least one result must contain either 'mortality' or 'child'.
    assert any("mortality" in n.lower() or "child" in n.lower() for n in names[:3])


def test_search_ranks_gdp_query_above_others():
    names = _first_name("gdp", limit=3)
    assert any("gdp" in n.lower() for n in names)


def test_search_ranks_co2_query():
    names = _first_name("co2", limit=5)
    joined = " ".join(names).lower()
    assert "co2" in joined or "co₂" in joined or "carbon" in joined


def test_search_limit_respected():
    out = fuzzy_search("poverty", INDICATORS, limit=2)
    assert len(out) <= 2


def test_search_is_case_insensitive():
    lower = fuzzy_search("literacy", INDICATORS, limit=1)
    upper = fuzzy_search("LITERACY", INDICATORS, limit=1)
    assert lower[0]["id"] == upper[0]["id"]
