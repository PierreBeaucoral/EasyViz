"""
File upload, format detection, column mapping, and normalisation
for user-supplied CSV / XLSX datasets.
"""

from __future__ import annotations

import io
import re
import unicodedata

import pandas as pd
import streamlit as st

# ── File reading ───────────────────────────────────────────────────────────────

def read_uploaded_file(uploaded_file) -> pd.DataFrame | None:
    """Read CSV or XLSX/XLS from a Streamlit UploadedFile object.

    Tries multiple separator / decimal combinations and returns whichever
    produces the most numeric columns (handles both dot and comma decimals).
    """
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()
    try:
        if name.endswith(".csv"):
            best: tuple[int, pd.DataFrame] | None = None
            for enc in ("utf-8", "latin-1", "cp1252"):
                for sep, decimal in [(None, "."), (";", ","), (",", ".")]:
                    try:
                        df = pd.read_csv(
                            io.BytesIO(raw), sep=sep, decimal=decimal,
                            engine="python", encoding=enc,
                        )
                        if df.shape[1] < 2:
                            continue
                        n_numeric = df.select_dtypes(include="number").shape[1]
                        if best is None or n_numeric > best[0]:
                            best = (n_numeric, df)
                    except Exception:
                        continue
            return best[1] if best else None
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

def _norm(s: str) -> str:
    """Lowercase, strip accents, collapse punctuation/whitespace."""
    s = unicodedata.normalize("NFD", s.lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")   # drop combining chars
    s = re.sub(r"[,\.'\"\-\(\)]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Curated aliases that pycountry gets wrong or is slow on.
# Keys are already _norm()-ed; values are ISO3.
_ALIASES: dict[str, str] = {
    # World Bank / IMF comma-style names
    "korea rep":                  "KOR",
    "korea rep.":                 "KOR",
    "south korea":                "KOR",
    "korea dem peoples rep":      "PRK",
    "north korea":                "PRK",
    "congo dem rep":              "COD",
    "congo democratic republic":  "COD",
    "dr congo":                   "COD",
    "drc":                        "COD",
    "democratic republic of congo": "COD",
    "democratic republic of the congo": "COD",
    "congo rep":                  "COG",
    "republic of the congo":      "COG",
    "egypt arab rep":             "EGY",
    "iran islamic rep":           "IRN",
    "venezuela rb":               "VEN",
    "kyrgyz republic":            "KGZ",
    "kyrgyzstan":                 "KGZ",
    "slovak republic":            "SVK",
    "czech republic":             "CZE",
    "czechia":                    "CZE",
    "bahamas the":                "BHS",
    "the bahamas":                "BHS",
    "gambia the":                 "GMB",
    "the gambia":                 "GMB",
    "yemen rep":                  "YEM",
    "micronesia fed sts":         "FSM",
    "micronesia":                 "FSM",
    "federated states of micronesia": "FSM",
    "sao tome and principe":      "STP",
    "sao tome":                   "STP",
    "timor leste":                "TLS",
    "east timor":                 "TLS",
    "cabo verde":                 "CPV",
    "cape verde":                 "CPV",
    "eswatini":                   "SWZ",
    "swaziland":                  "SWZ",
    "north macedonia":            "MKD",
    "fyr macedonia":              "MKD",
    "republic of north macedonia": "MKD",
    "cote d ivoire":              "CIV",
    "ivory coast":                "CIV",
    "lao pdr":                    "LAO",
    "laos":                       "LAO",
    "lao peoples democratic republic": "LAO",
    "russia":                     "RUS",
    "russian federation":         "RUS",
    "syria":                      "SYR",
    "syrian arab republic":       "SYR",
    "bolivia":                    "BOL",
    "tanzania":                   "TZA",
    "united republic of tanzania": "TZA",
    "vietnam":                    "VNM",
    "viet nam":                   "VNM",
    "moldova":                    "MDA",
    "republic of moldova":        "MDA",
    "taiwan":                     "TWN",
    "taiwan china":               "TWN",
    "hong kong":                  "HKG",
    "hong kong sar china":        "HKG",
    "macao":                      "MAC",
    "macau":                      "MAC",
    "macao sar china":            "MAC",
    "usa":                        "USA",
    "united states":              "USA",
    "united states of america":   "USA",
    "uk":                         "GBR",
    "great britain":              "GBR",
    "england":                    "GBR",
    "turkiye":                    "TUR",
    "turkey":                     "TUR",
    "west bank and gaza":         "PSE",
    "palestine":                  "PSE",
    "palestinian territories":    "PSE",
    "kosovo":                     "XKX",
    "sint maarten dutch part":    "SXM",
    "curacao":                    "CUW",
    "brunei":                     "BRN",
    "brunei darussalam":          "BRN",
    "burma":                      "MMR",
    "myanmar":                    "MMR",
}


def _build_pycountry_lookup() -> dict[str, str]:
    """Build a normalised name → ISO3 dict from all pycountry entries."""
    try:
        import pycountry
    except ImportError:
        return {}
    lookup: dict[str, str] = {}
    for c in pycountry.countries:
        iso3 = c.alpha_3
        for attr in ("name", "official_name", "common_name"):
            val = getattr(c, attr, None)
            if val:
                lookup[_norm(val)] = iso3
        # alpha_2 and alpha_3 exact (uppercase) — handle separately in main fn
    return lookup


# Built once per Python process; cheap after first call.
_PYCOUNTRY_LOOKUP: dict[str, str] | None = None


def _get_lookup() -> dict[str, str]:
    global _PYCOUNTRY_LOOKUP
    if _PYCOUNTRY_LOOKUP is None:
        _PYCOUNTRY_LOOKUP = {**_build_pycountry_lookup(), **_ALIASES}
    return _PYCOUNTRY_LOOKUP


@st.cache_data(show_spinner=False)
def _build_iso3_map(entities: tuple[str, ...]) -> dict[str, str]:
    """
    Map entity strings → ISO3 codes.

    Resolution order:
      1. Already ISO3 (3 uppercase letters)
      2. ISO2 → ISO3 via pycountry
      3. Normalised exact match in lookup table (pycountry names + curated aliases)
      4. rapidfuzz token-sort ratio against the lookup table (score ≥ 80)
      5. Empty string (country won't appear on choropleth)
    """
    from rapidfuzz import process, fuzz

    lookup = _get_lookup()
    lookup_keys = list(lookup.keys())

    try:
        import pycountry
        _iso3_set = {c.alpha_3 for c in pycountry.countries}
        _iso2_map = {c.alpha_2: c.alpha_3 for c in pycountry.countries}
    except ImportError:
        _iso3_set = set()
        _iso2_map = {}

    result: dict[str, str] = {}

    for name in entities:
        s = str(name).strip()

        # 1. Already a valid ISO3
        su = s.upper()
        if len(s) == 3 and su == s and su in _iso3_set:
            result[name] = su
            continue

        # 2. ISO2
        if len(s) == 2 and su == s and su in _iso2_map:
            result[name] = _iso2_map[su]
            continue

        # 3. Normalised exact match
        norm = _norm(s)
        if norm in lookup:
            result[name] = lookup[norm]
            continue

        # 4. Fuzzy match (rapidfuzz token_sort_ratio — handles "Korea, Rep." style)
        if lookup_keys:
            match, score, _ = process.extractOne(
                norm, lookup_keys, scorer=fuzz.token_sort_ratio
            )
            if score >= 80:
                result[name] = lookup[match]
                continue

        result[name] = ""

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
        df = df.melt(
            id_vars=[entity_col],
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
            df["year"] = 0
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["value"]).reset_index(drop=True)

    if entity_is_iso3:
        df["iso3"] = df["entity"].str.strip().str.upper()
    else:
        iso3_map = _build_iso3_map(tuple(df["entity"].dropna().unique()))
        df["iso3"] = df["entity"].map(iso3_map).fillna("")

    df["year"] = df["year"].astype(int)
    return df[["entity", "iso3", "year", "value"]]
