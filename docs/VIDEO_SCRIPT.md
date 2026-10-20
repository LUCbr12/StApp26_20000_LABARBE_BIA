# Demo video script (target 3:15 — limit 2–4 min)

Record the screen (OBS, Loom or Windows+G) with the real data loaded. Speak in English. Keep the mouse slow.

| Time | On screen | Say (suggested) |
|---|---|---|
| 0:00–0:20 | Top of the app, title | "Hi, I'm Luc. France talks about its electricity as one number, but the grid is made of very different regions. This dashboard shows how different, using RTE's éCO2mix regional data from data.gouv.fr." |
| 0:20–0:40 | Scroll intro cards, open the definitions expander | "It's for planners and curious citizens. Three questions: how low-carbon is each region, who covers its own demand, and what if wind and solar grew faster. Definitions are here." |
| 0:40–1:20 | Overview: KPIs, area chart, the two lines | "Across all regions, this share of production is low-carbon, and the arrows compare the last 12 months with the 12 before. Nuclear and hydro are the base, solar peaks in summer, wind in winter. The CO₂ line shows the seasonal rhythm; I annotated the peak and the low." |
| 1:20–1:35 | Sidebar: untick regions, change dates | "Everything is driven by the sidebar. If I keep only two regions and shorten the period, the KPIs and charts update." (Then restore all regions.) |
| 1:35–2:20 | Deep dives: switch metric, map, ranking, small multiples, boxplot, heatmap | "On the map, bubble size is production and colour is the metric I choose. The ranking shows the gap between leader and laggard. Small multiples show each region's mix by year, the box plots show day-to-day volatility, and the heatmap shows seasonality." |
| 2:20–2:50 | What-if sliders | "Here I raise solar and wind and cut thermal. Bars compare baseline and scenario. The assumptions are listed: linear scaling, same demand, no storage or grid limits — it's an exploration tool, not a forecast." |
| 2:50–3:10 | Data quality section | "Data quality: duplicates, missing values by region and column, and validation checks. Limits: production is not consumption, emission factors are assumptions, and map positions are approximate." |
| 3:10–3:25 | Insights + next steps | "The insights are computed from the current selection. Next steps: hourly profiles, real inter-regional flows and consumption-based carbon intensity. Thanks for watching." |

**Before recording:** `python scripts/fetch_data.py`, `streamlit run app.py`, browser at 100–110 % zoom, close other tabs, check the red "SYNTHETIC" banner is NOT shown.
