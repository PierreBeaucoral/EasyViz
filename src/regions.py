"""
Regional country groupings for one-click sample selection.

Design note: we deliberately hard-code the most-used groups (OECD,
EU27, SSA, LMIC, LDC, BRICS, G7) rather than hitting the WB country
endpoint at start-up. This keeps the app responsive offline and
guarantees the groupings match a recent, frozen reference — which is
exactly what a research user wants (stable samples across sessions).

If this ever needs to be kept current, the WB country-groups endpoint
`https://api.worldbank.org/v2/country?format=json&per_page=500` returns
each country's region / incomeLevel, which covers the WB-defined
groups. OECD / G7 / BRICS are editorial and must remain hand-curated.

All lists use the country's English name as it appears in the WDI
response (so multiselects can pre-fill without name resolution).
"""

from __future__ import annotations

# ── Core groups ───────────────────────────────────────────────────────────────

# OECD members as of 2024 (Costa Rica joined 2021, Colombia 2020).
OECD = [
    "Australia", "Austria", "Belgium", "Canada", "Chile", "Colombia",
    "Costa Rica", "Czechia", "Denmark", "Estonia", "Finland", "France",
    "Germany", "Greece", "Hungary", "Iceland", "Ireland", "Israel",
    "Italy", "Japan", "Korea, Rep.", "Latvia", "Lithuania", "Luxembourg",
    "Mexico", "Netherlands", "New Zealand", "Norway", "Poland", "Portugal",
    "Slovak Republic", "Slovenia", "Spain", "Sweden", "Switzerland",
    "Turkiye", "United Kingdom", "United States",
]

EU27 = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece",
    "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg",
    "Malta", "Netherlands", "Poland", "Portugal", "Romania",
    "Slovak Republic", "Slovenia", "Spain", "Sweden",
]

# Sub-Saharan Africa as defined by the WB (49 economies).
SSA = [
    "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cabo Verde",
    "Cameroon", "Central African Republic", "Chad", "Comoros",
    "Congo, Dem. Rep.", "Congo, Rep.", "Cote d'Ivoire", "Equatorial Guinea",
    "Eritrea", "Eswatini", "Ethiopia", "Gabon", "Gambia, The", "Ghana",
    "Guinea", "Guinea-Bissau", "Kenya", "Lesotho", "Liberia", "Madagascar",
    "Malawi", "Mali", "Mauritania", "Mauritius", "Mozambique", "Namibia",
    "Niger", "Nigeria", "Rwanda", "Sao Tome and Principe", "Senegal",
    "Seychelles", "Sierra Leone", "Somalia", "South Africa", "South Sudan",
    "Sudan", "Tanzania", "Togo", "Uganda", "Zambia", "Zimbabwe",
]

# WB Low- and Middle-Income economies (excluding High-Income), 2024 classification.
# Truncated to the most-cited 40 to keep the multiselect readable — full list on demand.
LMIC = [
    "Angola", "Bangladesh", "Benin", "Bolivia", "Burkina Faso", "Cambodia",
    "Cameroon", "Colombia", "Cote d'Ivoire", "Egypt, Arab Rep.", "Ethiopia",
    "Ghana", "Guatemala", "Honduras", "India", "Indonesia", "Kenya",
    "Kyrgyz Republic", "Lao PDR", "Madagascar", "Malawi", "Mali", "Mauritania",
    "Moldova", "Mongolia", "Morocco", "Myanmar", "Nepal", "Nicaragua",
    "Nigeria", "Pakistan", "Philippines", "Rwanda", "Senegal", "Sri Lanka",
    "Tanzania", "Togo", "Tunisia", "Uganda", "Uzbekistan", "Vietnam",
    "Zambia", "Zimbabwe",
]

# UN-designated Least Developed Countries (2024).
LDC = [
    "Afghanistan", "Angola", "Bangladesh", "Benin", "Burkina Faso", "Burundi",
    "Cambodia", "Central African Republic", "Chad", "Comoros",
    "Congo, Dem. Rep.", "Djibouti", "Eritrea", "Ethiopia", "Gambia, The",
    "Guinea", "Guinea-Bissau", "Haiti", "Kiribati", "Lao PDR", "Lesotho",
    "Liberia", "Madagascar", "Malawi", "Mali", "Mauritania", "Mozambique",
    "Myanmar", "Nepal", "Niger", "Rwanda", "Sao Tome and Principe",
    "Senegal", "Sierra Leone", "Solomon Islands", "Somalia", "South Sudan",
    "Sudan", "Tanzania", "Timor-Leste", "Togo", "Tuvalu", "Uganda", "Yemen, Rep.",
    "Zambia",
]

BRICS = ["Brazil", "Russian Federation", "India", "China", "South Africa"]

G7 = ["Canada", "France", "Germany", "Italy", "Japan", "United Kingdom", "United States"]

# Default convenience set used when no preset is selected.
DEFAULT = [
    "United States", "China", "Germany", "Brazil", "India", "Nigeria",
    "France", "United Kingdom", "South Africa", "Indonesia", "Mexico",
    "Bangladesh", "Ethiopia", "Kenya", "Colombia", "Vietnam", "Egypt, Arab Rep.",
    "Pakistan", "Tanzania", "Ghana",
]


# ── Registry ──────────────────────────────────────────────────────────────────

ALL_COUNTRIES_KEY = "All countries"

PRESETS: dict[str, list[str]] = {
    "Default (20 diverse)": DEFAULT,
    ALL_COUNTRIES_KEY:      [],  # sentinel — resolved to the full dataset at runtime
    "OECD (38)":            OECD,
    "EU27":                 EU27,
    "Sub-Saharan Africa":   SSA,
    "Low- & Middle-Income": LMIC,
    "LDCs (UN)":            LDC,
    "BRICS":                BRICS,
    "G7":                   G7,
}


def resolve_preset(name: str, all_countries: list[str]) -> list[str]:
    """Return members of `name` that actually appear in `all_countries`.

    `All countries` is a sentinel that expands to whatever the caller
    passes in, so we don't have to maintain a list of every WDI country.
    """
    if name == ALL_COUNTRIES_KEY:
        return list(all_countries)
    members = PRESETS.get(name, [])
    return [c for c in members if c in all_countries]
