"""
Generate copy-pasteable Python and R code that reproduces the chart
currently displayed in the app.
"""

from __future__ import annotations


def _countries_repr(countries: list[str]) -> str:
    items = ", ".join(f'"{c}"' for c in countries)
    return f"[{items}]"


def python_code(
    indicator: dict,
    selected_countries: list[str],
    year_range: tuple[int, int],
    chart_type: str,
    map_year: int | None,
    bar_year: int | None,
    top_n: int,
    log_scale: bool,
    color_scale: str,
    chart_title: str,
) -> str:
    """Return a standalone Python script that reproduces the chart."""

    # ── Data fetch block ──────────────────────────────────────────────────────
    if indicator["source"] == "owid":
        fetch_block = f'''\
import pandas as pd, io, requests

# --- Fetch data (Our World in Data) ---
slug = "{indicator['slug']}"
url = f"https://ourworldindata.org/grapher/{{slug}}.csv"
r = requests.get(url, timeout=30)
df_raw = pd.read_csv(io.StringIO(r.text))

# Normalise columns
value_col = [c for c in df_raw.columns if c not in ("Entity", "Code", "Year")][0]
df = df_raw.rename(columns={{
    "Entity": "entity", "Code": "iso3",
    "Year": "year", value_col: "value",
}})[["entity", "iso3", "year", "value"]].dropna(subset=["value"])
df["year"] = df["year"].astype(int)
'''
    else:
        code = indicator["indicator"]
        fetch_block = f'''\
import pandas as pd, requests

WB_API = (
    "https://api.worldbank.org/v2/country/all/indicator/{{code}}"
    "?format=json&date=1960:2024&per_page=20000&page={{page}}"
)
WB_AGGREGATES = {{
    "AFE","AFW","ARB","CAA","CEB","CSS","EAP","EAR","EAS","ECA","ECS","EMU",
    "EUU","FCS","HIC","HPC","IBD","IBT","IDA","IDX","LAC","LCN","LDC","LIC",
    "LMC","LMY","MEA","MIC","MNA","NAC","OEC","OSS","PRE","PSS","PST","SAR",
    "SAS","SSA","SSF","SST","TEA","TEC","TLA","TMN","TSA","TSS","UMC","WLD",
}}

def fetch_wdi(code):
    records, page = [], 1
    while True:
        r = requests.get(WB_API.format(code=code, page=page), timeout=30)
        resp = r.json()
        if not resp or len(resp) < 2 or resp[1] is None:
            break
        meta, data = resp[0], resp[1]
        for rec in data:
            iso3 = rec.get("countryiso3code", "")
            if rec.get("value") is None or iso3 in WB_AGGREGATES:
                continue
            records.append({{
                "entity": rec["country"]["value"],
                "iso3": iso3,
                "year": int(rec["date"]),
                "value": float(rec["value"]),
            }})
        if meta["page"] >= meta["pages"]:
            break
        page += 1
    return pd.DataFrame(records)

# --- Fetch data (World Bank WDI) ---
df = fetch_wdi("{code}")
'''

    # ── Filter block ──────────────────────────────────────────────────────────
    countries_py = _countries_repr(selected_countries)
    filter_block = f"""\

# --- Filter ---
df = df[df["iso3"].notna() & (df["iso3"].str.len() == 3)]
countries = {countries_py}
filtered = df[
    df["entity"].isin(countries)
    & df["year"].between({year_range[0]}, {year_range[1]})
]
"""

    # ── Log scale block ───────────────────────────────────────────────────────
    log_block = ""
    if log_scale:
        log_block = """\
import numpy as np
filtered = filtered.copy()
filtered["value"] = np.log1p(filtered["value"].clip(lower=0))
"""

    # ── Viz block ─────────────────────────────────────────────────────────────
    unit = indicator["unit"]
    escaped_title = chart_title.replace('"', '\\"')

    if "Map" in chart_type:
        viz_block = f'''\
import plotly.express as px

map_data = df[df["year"] == {map_year}].dropna(subset=["value", "iso3"])
map_data = map_data[map_data["iso3"].str.len() == 3]

fig = px.choropleth(
    map_data,
    locations="iso3",
    color="value",
    hover_name="entity",
    color_continuous_scale="{color_scale}",
    projection="natural earth",
    labels={{"value": "{unit}"}},
    title="{escaped_title}",
    template="plotly_white",
)
fig.update_geos(
    showcoastlines=True, coastlinecolor="#CBD5E1",
    showland=True, landcolor="#F8FAFC",
    showocean=True, oceancolor="#EFF6FF",
    showframe=False, showcountries=True, countrycolor="#E2E8F0",
)
fig.show()
'''
    elif "Line" in chart_type:
        viz_block = f'''\
import plotly.express as px

fig = px.line(
    filtered.sort_values("year"),
    x="year", y="value", color="entity",
    markers=True,
    labels={{"value": "{unit}", "year": "Year", "entity": "Country"}},
    title="{escaped_title}",
    template="plotly_white",
)
fig.update_layout(hovermode="x unified")
fig.show()
'''
    else:  # Bar
        viz_block = f'''\
import plotly.express as px

bar_data = (
    filtered[filtered["year"] == {bar_year}]
    .dropna(subset=["value"])
    .sort_values("value", ascending=False)
    .head({top_n})
    .sort_values("value")  # ascending so highest bar is at top
)

fig = px.bar(
    bar_data,
    x="value", y="entity", orientation="h",
    color="value", color_continuous_scale="{color_scale}",
    labels={{"value": "{unit}", "entity": ""}},
    title="{escaped_title} ({bar_year})",
    template="plotly_white",
)
fig.update_layout(showlegend=False, coloraxis_showscale=False)
fig.show()
'''

    return "\n".join([fetch_block, filter_block, log_block, viz_block])


def r_code(
    indicator: dict,
    selected_countries: list[str],
    year_range: tuple[int, int],
    chart_type: str,
    map_year: int | None,
    bar_year: int | None,
    top_n: int,
    log_scale: bool,
    color_scale: str,
    chart_title: str,
) -> str:
    """Return a standalone R script (tidyverse + plotly) that reproduces the chart."""

    countries_r = "c(" + ", ".join(f'"{c}"' for c in selected_countries) + ")"

    # ── Data fetch block ──────────────────────────────────────────────────────
    if indicator["source"] == "owid":
        fetch_block = f'''\
library(tidyverse)
library(plotly)

# --- Fetch data (Our World in Data) ---
slug <- "{indicator['slug']}"
url  <- paste0("https://ourworldindata.org/grapher/", slug, ".csv")

df_raw <- read_csv(url, show_col_types = FALSE)

# First non-metadata column is the value
value_col <- setdiff(names(df_raw), c("Entity", "Code", "Year"))[1]
df <- df_raw |>
  rename(entity = Entity, iso3 = Code, year = Year, value = all_of(value_col)) |>
  select(entity, iso3, year, value) |>
  drop_na(value) |>
  filter(nchar(iso3) == 3)
'''
    else:
        code = indicator["indicator"]
        fetch_block = f'''\
library(tidyverse)
library(WDI)
library(plotly)

# --- Fetch data (World Bank WDI) ---
# install.packages("WDI") if needed
df_raw <- WDI(
  indicator = "{code}",
  country   = "all",
  start     = 1960,
  end       = {year_range[1]},
  extra     = FALSE
)

df <- df_raw |>
  rename(entity = country, iso3 = iso3c, value = {code}) |>
  select(entity, iso3, year, value) |>
  drop_na(value) |>
  filter(nchar(iso3) == 3)
'''

    # ── Filter block ──────────────────────────────────────────────────────────
    filter_block = f"""\

# --- Filter ---
countries <- {countries_r}

filtered <- df |>
  filter(
    entity %in% countries,
    year >= {year_range[0]},
    year <= {year_range[1]}
  )
"""

    log_block = ""
    if log_scale:
        log_block = """\
filtered <- filtered |>
  mutate(value = log1p(pmax(value, 0)))
"""

    unit = indicator["unit"]
    escaped_title = chart_title.replace('"', '\\"')
    r_palette = f'"{color_scale}"'

    if "Map" in chart_type:
        viz_block = f'''\
# --- World Map ---
map_data <- df |>
  filter(year == {map_year}, nchar(iso3) == 3) |>
  drop_na(value)

fig <- plot_geo(map_data) |>
  add_trace(
    locations  = ~iso3,
    z          = ~value,
    text       = ~entity,
    colorscale = {r_palette},
    marker     = list(line = list(color = "#E2E8F0", width = 0.5))
  ) |>
  layout(
    title = "{escaped_title}",
    geo   = list(
      showcoastlines = TRUE,
      projection     = list(type = "natural earth")
    ),
    colorbar = list(title = "{unit}")
  )

fig
'''
    elif "Line" in chart_type:
        viz_block = f'''\
# --- Line Chart ---
fig <- filtered |>
  arrange(year) |>
  plot_ly(x = ~year, y = ~value, color = ~entity,
          type = "scatter", mode = "lines+markers") |>
  layout(
    title   = "{escaped_title}",
    xaxis   = list(title = "Year"),
    yaxis   = list(title = "{unit}"),
    hovermode = "x unified"
  )

fig
'''
    else:  # Bar
        viz_block = f'''\
# --- Bar Chart ---
bar_data <- filtered |>
  filter(year == {bar_year}) |>
  drop_na(value) |>
  slice_max(value, n = {top_n}) |>
  arrange(value)

fig <- bar_data |>
  plot_ly(x = ~value, y = ~entity, type = "bar", orientation = "h",
          marker = list(colorscale = {r_palette}, color = ~value,
                        showscale = FALSE)) |>
  layout(
    title  = "{escaped_title} ({bar_year})",
    xaxis  = list(title = "{unit}"),
    yaxis  = list(title = "")
  )

fig
'''

    return "\n".join([fetch_block, filter_block, log_block, viz_block])


def quarto_code(
    indicator: dict,
    selected_countries: list,
    year_range: tuple,
    chart_type: str,
    map_year: int | None,
    bar_year: int | None,
    top_n: int,
    log_scale: bool,
    color_scale: str,
    chart_title: str,
) -> str:
    """Return a Quarto document (.qmd) that embeds the R chart code."""
    r_script = r_code(
        indicator=indicator,
        selected_countries=selected_countries,
        year_range=year_range,
        chart_type=chart_type,
        map_year=map_year,
        bar_year=bar_year,
        top_n=top_n,
        log_scale=log_scale,
        color_scale=color_scale,
        chart_title=chart_title,
    )
    ind_name = indicator.get("name", "")
    safe_title = chart_title.replace('"', '\\"')

    header = f"""---
title: "{safe_title}"
format:
  html:
    self-contained: true
    code-fold: true
execute:
  warning: false
  message: false
---

## {ind_name}

```{{r}}
#| label: fig-chart
#| fig-cap: "{safe_title}"
#| fig-width: 10
#| fig-height: 6
"""
    return header + r_script + "\n```\n"
