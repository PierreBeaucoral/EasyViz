"""
File upload, format detection, column mapping, and normalisation
for user-supplied CSV / XLSX datasets.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

# ── File reading ───────────────────────────────────────────────────────────────

def read_uploaded_file(uploaded_file) -> pd.DataFrame | None:
    """Read CSV or XLSX/XLS from a Streamlit UploadedFile object."""
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()
    try:
        if name.endswith(".csv"):
            # Try Python engine with sep=None for auto-detection (comma, semicolon, tab, pipe)
            for enc in ("utf-8", "latin-1", "cp1252"):
                try:
                    df = pd.read_csv(
                        io.BytesIO(raw), sep=None, engine="python", encoding=enc
                    )
                    if df.shape[1] > 1:
                        return df
                except Exception:
                    continue
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(raw))
    except Exception:
        return None
    return None


# ── Format detection ───────────────────────────────────────────────────────────

def detect_format(df: pd.DataFrame) -> str:
    """Return 'wide' if many column headers look like years, else 'long'."""
    year_cols = [
        c for c in df.columns
        if str(c).strip().isdigit() and 1900 <= int(str(c).strip()) <= 2030
    ]
    return "wide" if len(year_cols) >= 4 else "long"


def detect_columns(df: pd.DataFrame) -> dict:
    """Heuristic auto-detection of entity, year, and value columns."""
    cols = list(df.columns)

    _entity_kw = ["country", "entity", "nation", "region", "name", "pays",
                  "iso", "code", "area", "location", "territory"]
    _year_kw   = ["year", "date", "time", "period", "an", "annee", "année", "yr"]

    entity_col = next(
        (c for c in cols if any(k in str(c).lower() for k in _entity_kw)), None
    )
    year_col = next(
        (c for c in cols if any(k in str(c).lower() for k in _year_kw)), None
    )
    # Fallback: an integer column whose values look like years
    if year_col is None:
        for c in cols:
            try:
                vals = pd.to_numeric(df[c], errors="coerce").dropna()
                if len(vals) > 0 and vals.between(1900, 2030).mean() > 0.8:
                    year_col = c
                    break
            except Exception:
                pass

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    value_candidates = [c for c in numeric_cols if c not in (entity_col, year_col)]

    return {
        "entity": entity_col,
        "year":   year_col,
        "value":  value_candidates[0] if value_candidates else None,
        "value_candidates": value_candidates,
    }


# ── ISO3 resolution ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _build_iso3_map(entities: tuple[str, ...]) -> dict[str, str]:
    """Map entity strings → ISO3 codes. Tries pycountry fuzzy search."""
    result: dict[str, str] = {}
    try:
        import pycountry

        for name in entities:
            s = str(name).strip()
            # Already ISO3?
            if len(s) == 3 and s.upper() == s:
                result[name] = s
                continue
            # Already ISO2?
            if len(s) == 2 and s.upper() == s:
                try:
                    c = pycountry.countries.get(alpha_2=s.upper())
                    result[name] = c.alpha_3 if c else ""
                    continue
                except Exception:
                    pass
            # Fuzzy name match
            try:
                hits = pycountry.countries.search_fuzzy(s)
                result[name] = hits[0].alpha_3 if hits else ""
            except Exception:
                result[name] = ""
    except ImportError:
        # pycountry not available — leave ISO3 empty; maps still show data
        # if user's data already has ISO3 codes in the entity column
        for name in entities:
            s = str(name).strip()
            result[name] = s if (len(s) == 3 and s.upper() == s) else ""
    return result


# ── Normalisation ──────────────────────────────────────────────────────────────

def normalise(
    df: pd.DataFrame,
    entity_col: str,
    year_col: str | None,
    value_col: str,
    fmt: str = "long",       # "long" | "wide"
    entity_is_iso3: bool = False,
) -> pd.DataFrame:
    """
    Normalise an arbitrary DataFrame to the standard
    entity / iso3 / year / value format used by the viz layer.
    """
    df = df.copy()

    if fmt == "wide":
        year_value_cols = [
            c for c in df.columns
            if str(c).strip().isdigit() and 1900 <= int(str(c).strip()) <= 2030
        ]
        id_cols = [entity_col]
        df = df.melt(
            id_vars=id_cols,
            value_vars=year_value_cols,
            var_name="_year",
            value_name="value",
        )
        df["year"]   = pd.to_numeric(df["_year"], errors="coerce")
        df["entity"] = df[entity_col]
        df = df[["entity", "year", "value"]]
    else:
        rename = {entity_col: "entity", value_col: "value"}
        if year_col:
            rename[year_col] = "year"
        df = df.rename(columns=rename)
        keep = ["entity", "value"] + (["year"] if year_col else [])
        df = df[keep]
        if year_col:
            df["year"] = pd.to_numeric(df["year"], errors="coerce")
        else:
            df["year"] = 0          # single-period data
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["value"]).reset_index(drop=True)

    # ISO3 resolution
    if entity_is_iso3:
        df["iso3"] = df["entity"].str.strip().str.upper()
    else:
        iso3_map = _build_iso3_map(tuple(df["entity"].dropna().unique()))
        df["iso3"] = df["entity"].map(iso3_map).fillna("")

    df["year"] = df["year"].astype(int)
    return df[["entity", "iso3", "year", "value"]]
