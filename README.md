# One grid, twelve energy stories — Streamlit data-storytelling dashboard

**EFREI Paris · Individual Student Project #EFREIDataStories2026 · Group BIA**
Author: Luc Labarbe

An interactive Streamlit app that tells how the **electricity mix, carbon intensity and
self-sufficiency differ across French regions** (2013 → present), using the public
éCO2mix regional data published by RTE.

**Live app:** <https://efrei-eco2mix.streamlit.app> · **Code:** <https://github.com/LUCbr12/StApp26_20000_LABARBE_BIA> · **Demo video:** <https://youtu.be/ecqtkjvG8gA>

Narrative: **Hook → Context → Overview (KPIs, trends) → Deep dives (map, ranking, small multiples,
distribution, seasonality) → What-if → Data quality → Insights & next steps.**

## Dataset

| | |
|---|---|
| Title | *Données éCO2mix régionales consolidées et définitives* |
| Portal | data.gouv.fr — <https://www.data.gouv.fr/datasets/donnees-eco2mix-regionales-consolidees-et-definitives> |
| Publisher | RTE, via Open Data Réseaux Énergies (ODRE) |
| License | Licence Ouverte / Open Licence 2.0 (Etalab) — attribution required |
| Grain | half-hourly, per region (12 regions of mainland France; Corsica is absent), from Jan 2013, refreshed daily |
| CSV link | <https://www.data.gouv.fr/api/1/datasets/r/4c308634-d76e-40b0-a777-ab99a8871564> |

The code was written for this course project; **the data keeps its own licence** (attribution to RTE / ODRE required).

## Run it (clean checkout)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/fetch_data.py     # ONCE: downloads the CSV (cached) and builds data/eco2mix_daily.csv.gz
streamlit run app.py
```

(or `make install data run`).

- `fetch_data.py` streams the ~1 M-row CSV in chunks and pre-aggregates it to **one row per region per day**
  (MWh). The two small output files (`data/eco2mix_daily.csv.gz`, `data/quality.json`) are what the app loads,
  so the deployed app starts instantly and needs no download. **Commit them** before deploying.
- Offline test mode (synthetic, clearly flagged by a red banner, never for the report):
  `make sample` then `ECO2MIX_SAMPLE=1 streamlit run app.py`.
- Automated smoke test: `make test` (Streamlit `AppTest`, no browser needed).

## Project structure

```
app.py                 # page config, sidebar filters, narrative order, caching
sections/
  intro.py             # hook, audience, questions, definitions
  overview.py          # KPI header (tied to filters) + trends
  deep_dives.py        # map, ranking, small multiples, distribution, heatmap + what-if
  quality.py           # missingness, duplicates, validation checks, limitations
  conclusions.py       # data-driven insights + implications
utils/
  io.py                # download (cached), build processed files, load_data()
  prep.py              # schema matching, cleaning, features, KPIs, scenario logic, validation
  viz.py               # chart functions: one palette/style, labelled axes + alt-text captions
  sample.py            # synthetic test data generator (offline only)
scripts/fetch_data.py  # CLI for the data pipeline
data/                  # processed CSV.gz + quality.json (raw CSV is git-ignored)
docs/                  # storyboard + demo-video script
seeds.json             # seed for the synthetic sample (real pipeline is deterministic)
```

## Requirements checklist

- Sidebar controls: regions, date range, metric, thermal emission factor ✔
- ≥ 3 interactive visuals with tooltips: stacked area, lines, map, ranking, small multiples, box plots, heatmaps, scenario bars ✔
- Map: bubble map of regions (approximate centroids, keyed by INSEE code) ✔
- KPI header tied to filters, with Δ vs previous 12 months ✔
- Data quality section: missingness heatmap, duplicates, validation checks ✔
- Performance: `st.cache_data`, chunked read + pre-aggregation to daily, small compressed CSV ✔
- Accessibility: colour-blind-safe palette, axis titles with units, text description under each chart ✔
- Reproducibility: pinned `requirements.txt`, fetch script with caching, `Makefile` ✔

## Key methodological choices & assumptions

- **Daily energy** = mean power over *valid* half-hours × 24 h (robust to missing rows and to duplicated rows).
- **Blank production** (e.g. no reactors in a region) → 0 MWh; negative production clipped to 0.
- **CO₂ intensity** uses fixed life-cycle factors (g/kWh): nuclear 6, wind 12, solar 30, hydro 6, bioenergy 230,
  thermal 450 (editable in the sidebar). These are **my own round-number assumptions in the range of published
  life-cycle figures (IPCC / ADEME), not values taken from a specific table**; the thermal fleet split is not in the data. It describes **local production**, not the electricity consumed in the region.
- **What-if** scales historical output linearly; demand unchanged; no storage, curtailment or grid limits; not a forecast.

## Limitations

Regional production ≠ regional consumption mix; flat-rate estimates for small producers; approximate map positions;
the emission factors are assumptions; correlation is not causation. No personal data is used (regional aggregates only).

## Deployment (Streamlit Community Cloud)

1. Push this folder to a GitHub repo, **including `data/eco2mix_daily.csv.gz` and `data/quality.json`**.
2. On <https://share.streamlit.io>, create an app: repo → branch `main` → main file `app.py`.
3. Add the URL, repo link and demo-video link to the submission.

## Demo video & storyboard

See `docs/STORYBOARD.md` and `docs/VIDEO_SCRIPT.md` (2–4 min walkthrough).

## Credits

Data: RTE / ODRE, Licence Ouverte 2.0. Tools: Streamlit, Plotly, pandas.
