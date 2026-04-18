"""
Shared Streamlit UI helpers used by every page.

Everything here is presentational: injecting CSS, rendering standard
download button rows, printing a citation panel. Kept small and
deliberately free of business logic.
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .metadata import IndicatorMetadata

# ── CSS blobs ─────────────────────────────────────────────────────────────────

_HIDE_SIDEBAR_CSS = """
<style>
section[data-testid="stSidebar"]  { display: none !important; }
[data-testid="collapsedControl"]   { display: none !important; }
</style>
"""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark sidebar */
section[data-testid="stSidebar"] { background: #0F172A; }
section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
section[data-testid="stSidebar"] .stTextInput input {
    background: #1E293B; border: 1px solid #334155;
    color: #F1F5F9 !important; border-radius: 8px;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #F8FAFC; border-radius: 10px;
    padding: 12px 16px; border: 1px solid #E2E8F0;
}

/* Download buttons */
.stDownloadButton button {
    background: #1E40AF; color: white; border: none;
    border-radius: 8px; font-weight: 500;
}
.stDownloadButton button:hover { background: #1D4ED8; }

.section-label {
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #64748B; margin-bottom: 4px;
}
</style>
"""


def inject_global_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def hide_sidebar() -> None:
    """Hide sidebar for full-width landing / workflow pages."""
    st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)


# ── Download helpers ──────────────────────────────────────────────────────────

def download_buttons(
    fig: go.Figure,
    df: pd.DataFrame,
    slug: str,
    include_svg: bool = True,
) -> None:
    """
    Render the standard 4-button download row (CSV / PNG / HTML / SVG).

    PNG/SVG require kaleido; we show a disabled button if it's missing
    rather than hiding the option, because users need to see that the
    export exists once the dependency is installed.
    """
    cols = st.columns(4 if include_svg else 3)

    with cols[0]:
        st.download_button(
            "⬇️ Data (CSV)", df.to_csv(index=False),
            f"{slug}.csv", "text/csv", width="stretch",
        )

    with cols[1]:
        try:
            buf = io.BytesIO()
            fig.write_image(buf, format="png", scale=2, width=1400, height=800)
            st.download_button(
                "⬇️ Chart (PNG)", buf.getvalue(),
                f"{slug}.png", "image/png", width="stretch",
            )
        except Exception as e:  # kaleido specific errors aren't typed
            st.button(f"⬇️ PNG unavailable ({type(e).__name__})", disabled=True, width="stretch")

    with cols[2]:
        st.download_button(
            "⬇️ Chart (HTML)", fig.to_html(full_html=True, include_plotlyjs="cdn"),
            f"{slug}.html", "text/html", width="stretch",
        )

    if include_svg:
        with cols[3]:
            try:
                svg_buf = io.BytesIO()
                fig.write_image(svg_buf, format="svg")
                st.download_button(
                    "⬇️ Chart (SVG)", svg_buf.getvalue(),
                    f"{slug}.svg", "image/svg+xml", width="stretch",
                )
            except Exception as e:
                st.button(
                    f"⬇️ SVG unavailable ({type(e).__name__})",
                    disabled=True, width="stretch",
                )


# ── Citation panel ────────────────────────────────────────────────────────────

def citation_panel(meta: IndicatorMetadata) -> None:
    """
    Render the per-indicator citation expander.

    Shows the live WB definition, the formatted citation, the BibTeX
    key, and the fetch timestamp so the user can pin the snapshot in
    their manuscript.
    """
    with st.expander("📚 How to cite this indicator"):
        st.markdown(f"**Definition** — {meta.definition}")
        st.markdown(
            f"**Source** — [{meta.source_name}]({meta.source_url})  \n"
            f"**Organisation** — {meta.organisation}  \n"
            f"**Fetched** — {meta.snapshot_str} (UTC)"
        )
        st.markdown("**Citation (APA-like)**")
        st.code(meta.citation_plain(), language="text")
        st.markdown("**BibTeX**")
        st.code(meta.citation_bibtex(), language="bibtex")


# ── Misc ──────────────────────────────────────────────────────────────────────

SOURCE_BADGE = {
    "upload": ("#8B5CF6", "Your dataset"),
    "owid":   ("#10B981", "Our World in Data"),
    "wdi":    ("#3B82F6", "World Bank WDI"),
}


def source_pill(source_key: str) -> str:
    """Return an HTML span suitable for `st.markdown(..., unsafe_allow_html=True)`."""
    color, label = SOURCE_BADGE.get(source_key, ("#3B82F6", "World Bank"))
    return (
        f"<span style='background:{color};color:white;padding:3px 10px;"
        f"border-radius:20px;font-size:0.78rem;font-weight:600'>{label}</span>"
    )
