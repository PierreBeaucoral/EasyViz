"""
EasyViz — Development Data Explorer.

Thin router. All page logic lives in `src/pages/<name>.py`, each
exposing a single `render()` function. This module is responsible for
three things only:

    1. Streamlit page configuration + global CSS injection.
    2. Session-state bootstrap (including URL query-param restoration).
    3. Dispatch to the correct page module.
"""

from __future__ import annotations

import streamlit as st

from src.catalog import INDICATORS
from src.pages import about, compare, conflict, data, home, subnational, upload
from src.ui import inject_global_css
from src.urlstate import embed_css, is_embed

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="EasyViz — Development Data Explorer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()

# Embed mode: hide sidebar / header / footer when loaded via iframe.
if is_embed():
    st.markdown(embed_css(), unsafe_allow_html=True)


# ── Session-state bootstrap ───────────────────────────────────────────────────

def _init_state() -> None:
    """Initialise session state on the first run of a session.

    Honours a `?ind=<indicator_id>` query param so that permalinks to
    specific indicators work after the user has bookmarked / shared them.
    """
    if "page" in st.session_state:
        return

    qp = st.query_params
    ind_id = qp.get("ind")
    # Accept curated indicator ids; deep-links to auto-imported WDI codes
    # (prefix `wdi_`) are resolved lazily on the data page.
    curated_ids = {r["id"] for r in INDICATORS}
    if ind_id and (ind_id in curated_ids or ind_id.startswith("wdi_")):
        st.session_state.selected_id = ind_id
        st.session_state.page = "data"
    else:
        st.session_state.selected_id = None
        st.session_state.page = "home"


_init_state()


# ── Router ────────────────────────────────────────────────────────────────────

# Explicit page → render() lookup. Keeping this as a plain dict (not a
# match/case or class registry) makes the control flow visible at a
# glance and keeps new-page onboarding one-line.
_ROUTES = {
    "home":        home.render,
    "about":       about.render,
    "data":        data.render,
    "upload":      upload.render,
    "compare":     compare.render,
    "subnational": subnational.render,
    "conflict":    conflict.render,
}

_page = st.session_state.get("page", "home")

# If an indicator is selected but page state is stale, coerce to the
# data page — this mirrors the original app behaviour for deep links
# and ensures the indicator detail view is always reachable.
if st.session_state.get("selected_id") and _page not in _ROUTES:
    _page = "data"
    st.session_state.page = _page

_ROUTES.get(_page, home.render)()
