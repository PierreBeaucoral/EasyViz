"""
Indicator-level metadata and citation helpers.

This module is the single place in the codebase that knows how to turn
an EasyViz indicator record into a citation. It:

  1. Fetches the **live** World Bank metadata (definition, source
     organisation, topic) from the WB metadata API.
  2. Builds a human-readable citation string + a BibTeX entry.
  3. Surfaces the fetch timestamp so that exported code can pin the
     snapshot date for reproducibility.

All network calls are wrapped in Streamlit's cache with a 24 h TTL
because indicator metadata moves much more slowly than values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests
import streamlit as st

from .http import session as _session

_WB_META_URL = (
    "https://api.worldbank.org/v2/indicator/{code}?format=json"
)
_HEADERS = {
    "User-Agent": "EasyViz/0.2 (+https://github.com/PierreBeaucoral/EasyViz)",
    "Accept": "application/json",
}

# Canonical source URLs used when a live fetch fails.
_SOURCE_PAGE = {
    "wdi":  "https://data.worldbank.org/indicator/{code}",
    "owid": "https://ourworldindata.org/grapher/{slug}",
}


@dataclass
class IndicatorMetadata:
    """Everything a chart footer, citation box, or exported script needs."""

    code: str
    name: str
    source_name: str
    source_url: str
    definition: str               # the 'sourceNote' field from WB or a stub
    organisation: str             # e.g. "World Bank, World Development Indicators"
    snapshot: datetime            # when the values were fetched (UTC)

    # ── Presentation helpers ───────────────────────────────────────────────
    @property
    def snapshot_str(self) -> str:
        return self.snapshot.strftime("%Y-%m-%d")

    def citation_plain(self) -> str:
        """
        APA-style citation string suitable for a chart footnote or a
        manuscript. Example:

            World Bank (accessed 2026-04-18). Under-5 Mortality Rate
            (SH.DYN.MORT). World Development Indicators.
            https://data.worldbank.org/indicator/SH.DYN.MORT
        """
        return (
            f"{self.organisation} (accessed {self.snapshot_str}). "
            f"{self.name} ({self.code}). {self.source_name}. {self.source_url}"
        )

    def citation_bibtex(self, key: str | None = None) -> str:
        """BibTeX entry — auto-keyed if `key` is None."""
        ck = key or f"wdi_{self.code.lower().replace('.', '_')}"
        return (
            f"@misc{{{ck},\n"
            f"  author = {{ {self.organisation} }},\n"
            f"  title  = {{ {self.name} ({self.code}) }},\n"
            f"  year   = {{ {self.snapshot.year} }},\n"
            f"  note   = {{ accessed {self.snapshot_str} }},\n"
            f"  url    = {{ {self.source_url} }}\n"
            f"}}"
        )


# ── Public entry point ────────────────────────────────────────────────────────

def build_metadata(indicator: dict, snapshot: datetime | None = None) -> IndicatorMetadata:
    """
    Build an IndicatorMetadata for a catalog entry.

    `snapshot` should be the timestamp at which the values were fetched;
    passing it explicitly keeps the metadata and the data in sync.
    """
    snapshot = snapshot or datetime.now(timezone.utc)

    if indicator["source"] == "wdi":
        code = indicator["indicator"]
        live = _fetch_wdi_metadata(code)
        return IndicatorMetadata(
            code        = code,
            name        = live.get("name") or indicator["name"],
            source_name = "World Development Indicators",
            source_url  = _SOURCE_PAGE["wdi"].format(code=code),
            definition  = live.get("sourceNote", "") or _DEF_STUB,
            organisation = live.get("sourceOrganization", "World Bank"),
            snapshot    = snapshot,
        )

    if indicator["source"] == "owid":
        slug = indicator["slug"]
        return IndicatorMetadata(
            code        = slug,
            name        = indicator["name"],
            source_name = "Our World in Data",
            source_url  = _SOURCE_PAGE["owid"].format(slug=slug),
            definition  = indicator.get("definition", _DEF_STUB),
            organisation = "Our World in Data",
            snapshot    = snapshot,
        )

    # Custom / uploaded dataset — there is nothing to cite.
    return IndicatorMetadata(
        code        = indicator.get("id", "custom"),
        name        = indicator.get("name", "Custom dataset"),
        source_name = "User upload",
        source_url  = "",
        definition  = "User-supplied dataset. Provenance is not tracked by EasyViz.",
        organisation = "User",
        snapshot    = snapshot,
    )


_DEF_STUB = (
    "Definition not available from the upstream source. "
    "Refer to the source URL for the authoritative methodology."
)


@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_wdi_metadata(code: str) -> dict:
    """
    Hit the World Bank *indicator* endpoint (not the value endpoint) and
    return the first record. Returns an empty dict on any failure so the
    caller can fall back to catalog-provided defaults.
    """
    try:
        r = _session.get(_WB_META_URL.format(code=code), headers=_HEADERS, timeout=15)
        r.raise_for_status()
        body = r.json()
        if not body or len(body) < 2 or not body[1]:
            return {}
        rec = body[1][0]
        return {
            "name": rec.get("name", ""),
            "sourceNote": rec.get("sourceNote", ""),
            "sourceOrganization": rec.get("sourceOrganization", ""),
        }
    except (requests.RequestException, ValueError, KeyError, IndexError):
        # Metadata fetch is best-effort. A failure must never block the app.
        return {}
