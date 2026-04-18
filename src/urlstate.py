"""
URL query-param helpers for bookmarking and embedding EasyViz.

Two related features share this file:

  1. **Full-state serialisation** — key filter/chart choices round-trip
     through the URL so a view can be bookmarked, shared by link, or
     cited in a paper. We stay conservative about what goes in — only
     short, stable settings — to keep URLs short.

  2. **Embed mode** — when `?embed=1` is present, `is_embed()` returns
     True and the page-level CSS collapses the sidebar, back-button,
     and footer. Designed for iframe embedding in Quarto blogs.

All encoding is deliberately simple (comma-separated, no JSON) so the
URLs remain human-inspectable.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# ── Embed mode ────────────────────────────────────────────────────────────────

def is_embed() -> bool:
    """True when the app was loaded with `?embed=1`."""
    val = st.query_params.get("embed")
    return str(val).lower() in ("1", "true", "yes")


def embed_css() -> str:
    """CSS that hides navigation chrome for iframe embeds."""
    return """
    <style>
      [data-testid="stSidebar"] { display: none !important; }
      [data-testid="collapsedControl"] { display: none !important; }
      header { display: none !important; }
      footer { display: none !important; }
      .block-container { padding-top: 1rem !important; }
    </style>
    """


# ── Generic helpers ───────────────────────────────────────────────────────────

def set_param(key: str, value: Any) -> None:
    """Write a scalar to the URL query string. Empty values clear the key."""
    if value in (None, "", []):
        if key in st.query_params:
            del st.query_params[key]
        return
    st.query_params[key] = str(value)


def set_list(key: str, values: list[str]) -> None:
    """Encode a list as a comma-separated query param. Empty list clears."""
    if not values:
        if key in st.query_params:
            del st.query_params[key]
        return
    st.query_params[key] = ",".join(str(v) for v in values)


def get_list(key: str) -> list[str]:
    """Decode a comma-separated list param, returning [] if absent."""
    raw = st.query_params.get(key, "")
    if not raw:
        return []
    return [p for p in str(raw).split(",") if p]


def get_int_pair(key: str) -> tuple[int, int] | None:
    """Decode 'a-b' → (a, b). Returns None if absent or malformed."""
    raw = st.query_params.get(key, "")
    if not raw or "-" not in str(raw):
        return None
    try:
        a, b = str(raw).split("-", 1)
        return int(a), int(b)
    except (ValueError, AttributeError):
        return None


def set_int_pair(key: str, pair: tuple[int, int] | None) -> None:
    """Encode (a, b) as 'a-b'."""
    if pair is None:
        if key in st.query_params:
            del st.query_params[key]
        return
    a, b = pair
    st.query_params[key] = f"{int(a)}-{int(b)}"


def get_bool(key: str) -> bool:
    """Return True for ?key=1 / true / yes; False otherwise."""
    val = st.query_params.get(key, "")
    return str(val).lower() in ("1", "true", "yes")


def set_bool(key: str, value: bool) -> None:
    if value:
        st.query_params[key] = "1"
    elif key in st.query_params:
        del st.query_params[key]
