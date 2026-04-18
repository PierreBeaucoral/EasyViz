"""
Home / landing page: search bar + popular indicator pills + shortcuts.
"""

from __future__ import annotations

import streamlit as st

from ..catalog import INDICATORS
from ..search import fuzzy_search
from ..ui import hide_sidebar
from ..wdi_taxonomy import load_all as load_full_wdi

CAT_ICON = {
    "Health": "🏥", "Economy": "💰", "Education": "📚",
    "Environment": "🌿", "Demographics": "👥", "Governance": "🏛️",
}

POPULAR_IDS = [
    "under5_mortality", "gdp_per_capita_ppp", "co2_per_capita",
    "extreme_poverty", "life_expectancy", "literacy_rate",
    "access_electricity", "fertility_rate",
]


def _home_css() -> None:
    st.markdown("""
    <style>
    div[data-testid="stTextInput"] input {
        font-size: 1.1rem !important;
        padding: 14px 22px !important;
        border-radius: 50px !important;
        border: 2px solid #E2E8F0 !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.07) !important;
        transition: all 0.2s;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #2563EB !important;
        box-shadow: 0 4px 24px rgba(37,99,235,0.14) !important;
        outline: none !important;
    }
    div[data-testid="stHorizontalBlock"] .stButton button,
    .result-btn .stButton button {
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        background: white;
        color: #1E293B;
        text-align: left;
        padding: 10px 14px;
        font-size: 0.95rem;
        transition: all 0.15s;
    }
    div[data-testid="stHorizontalBlock"] .stButton button:hover,
    .result-btn .stButton button:hover {
        border-color: #2563EB;
        color: #1E40AF;
        background: #EFF6FF;
    }
    </style>
    """, unsafe_allow_html=True)


def render() -> None:
    hide_sidebar()
    _home_css()

    st.markdown("<div style='padding-top:9vh'></div>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            "<h1 style='text-align:center;font-size:3rem;margin-bottom:6px'>🌍 EasyViz</h1>"
            "<p style='text-align:center;color:#64748B;font-size:1.05rem;margin-bottom:36px'>"
            "Explore development data, reproducibly.</p>",
            unsafe_allow_html=True,
        )

        query = st.text_input(
            "search",
            placeholder="🔍   child mortality, GDP, CO₂, poverty, literacy…",
            label_visibility="collapsed",
        )
        use_full = st.checkbox(
            "Search full World Bank catalogue (~1,500 indicators)",
            value=False,
            help="Curated list shows ~80 hand-picked indicators with clean tags. "
                 "Full catalogue covers every WDI series — slower search, less curated.",
        )

        if query:
            search_space = INDICATORS
            if use_full:
                extra = load_full_wdi()
                # Deduplicate: curated entries win over raw-imported ones.
                seen_codes = {r.get("indicator") for r in INDICATORS if r.get("source") == "wdi"}
                extra_unique = [r for r in extra if r["indicator"] not in seen_codes]
                search_space = INDICATORS + extra_unique
            results = fuzzy_search(query, search_space, limit=7)
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            for r in results:
                icon = CAT_ICON.get(r["category"], "📊")
                if st.button(
                    f"{icon}  {r['name']}   ·   {r['category']}  —  {r['unit']}",
                    key=f"home_{r['id']}",
                    width="stretch",
                ):
                    st.session_state.selected_id = r["id"]
                    st.session_state.page = "data"
                    st.query_params["ind"] = r["id"]
                    st.rerun()
        else:
            st.markdown(
                "<p style='text-align:center;color:#94A3B8;font-size:0.82rem;"
                "margin:28px 0 14px;letter-spacing:0.08em'>POPULAR INDICATORS</p>",
                unsafe_allow_html=True,
            )
            popular = [r for r in INDICATORS if r["id"] in POPULAR_IDS]
            for row in [popular[:4], popular[4:]]:
                if not row:
                    continue
                cols = st.columns(len(row))
                for i, ind in enumerate(row):
                    with cols[i]:
                        icon = CAT_ICON.get(ind["category"], "📊")
                        if st.button(
                            f"{icon}  {ind['name']}",
                            key=f"pop_{ind['id']}",
                            width="stretch",
                        ):
                            st.session_state.selected_id = ind["id"]
                            st.session_state.page = "data"
                            st.query_params["ind"] = ind["id"]
                            st.rerun()

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        btn1, btn2, btn3, btn4, btn5 = st.columns(5)
        with btn1:
            if st.button("📤  Upload data", width="stretch"):
                st.session_state.page = "upload"
                st.rerun()
        with btn2:
            if st.button("🔗  Compare", width="stretch"):
                st.session_state.page = "compare"
                st.rerun()
        with btn3:
            if st.button("🗺️  Sub-national", width="stretch"):
                st.session_state.page = "subnational"
                st.rerun()
        with btn4:
            if st.button("⚔️  Conflict data", width="stretch"):
                st.session_state.page = "conflict"
                st.rerun()
        with btn5:
            if st.button("ℹ️  How it works", width="stretch"):
                st.session_state.page = "about"
                st.rerun()

        st.markdown(
            "<p style='text-align:center;color:#CBD5E1;font-size:0.75rem;margin-top:24px'>"
            "Data: World Bank WDI · Our World in Data</p>",
            unsafe_allow_html=True,
        )
