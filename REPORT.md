# Report — "One grid, twelve energy stories"

**EFREI Paris · Individual Student Project #EFREIDataStories2026 · Group BIA · Luc Labarbe**

| | |
|---|---|
| Live app | <https://efrei-eco2mix.streamlit.app> |
| Code | <https://github.com/LUCbr12/StApp26_20000_LABARBE_BIA> |
| Storyboard | <https://github.com/LUCbr12/StApp26_20000_LABARBE_BIA/blob/main/docs/STORYBOARD.md> |
| Demo video | <https://youtu.be/ecqtkjvG8gA> |

## 1. Question and audience

France's electricity is usually summarised by one national number, but regions produce very different things.
The dashboard asks: **is low-carbon electricity the same story in every French region?** It targets regional
planners, energy-transition advisers and curious citizens, and answers three questions:

1. How low-carbon is each region's electricity production?
2. Which regions cover their own consumption, and which depend on others?
3. How fast are wind and solar growing, and what would happen if they grew faster?

Narrative pattern: *compare regions (map + small multiples)* combined with *before/after change over time* and a
*what-if* exploration. Story arc: hook → context → overview → deep dives → what-if → data quality → insights and next steps.

## 2. Data

- **Dataset:** *Données éCO2mix régionales consolidées et définitives* — RTE, published through Open Data Réseaux
  Énergies (ODRE) on data.gouv.fr: <https://www.data.gouv.fr/datasets/donnees-eco2mix-regionales-consolidees-et-definitives>
- **Licence:** Licence Ouverte / Open Licence 2.0 (Etalab). Attribution to RTE / ODRE is shown in the app. The code is mine; the data keeps its own licence.
- **Content:** half-hourly consumption and production by source (thermal, nuclear, wind, solar, hydro, bioenergy), pumping and
  exchanges, per region, from January 2013 to August 2026 in the file I used. Corsica is not in the file, so **12 regions**.
- **Size:** 2,874,816 half-hourly rows.
- **Known limits (from the publisher):** values come from metering completed with flat-rate estimates, mainly for small producers.

## 3. Method

1. **Download once** (`scripts/fetch_data.py`): the CSV is streamed and cached locally; the raw file is not committed.
2. **Aggregate in chunks** to one row per region per day, in MWh (`utils/prep.py`). Daily energy = *mean power over the
   valid half-hours × 24 h*, which is robust to missing and duplicated rows. Result: **59,892 region-days**, stored in a small
   compressed CSV (`data/eco2mix_daily.csv.gz`) so the app starts quickly.
3. **Cleaning rules:** column names are matched by meaning (accent- and case-insensitive); blank production (e.g. nuclear in a region
   without reactors) is treated as 0; negative production values are clipped to 0; region labels are harmonised from the INSEE code.
4. **Feature engineering:** production, low-carbon and renewable totals, shares, coverage rate (production ÷ consumption), CO₂ intensity,
   calendar fields, and year-over-year deltas for the KPI header.
5. **CO₂ intensity** uses fixed life-cycle emission factors per source (g/kWh): nuclear 6, wind 12, solar 30, hydro 6, bioenergy 230, thermal 450.
   These are **my own round-number assumptions** in the range of published life-cycle figures, not values taken from one specific table.
   The thermal factor is editable in the app because the gas/coal/oil split is not in the data.
6. **What-if model:** historical solar and wind output scaled by a percentage and thermal output reduced by a percentage; demand unchanged;
   no storage, curtailment or grid constraints. Selection totals are production-weighted.

## 4. Data quality and validation

The app's data-quality section reports (on the full file):

| Check | Result |
|---|---|
| Rows read | 2,874,816 |
| Duplicated (region, timestamp) keys | **336 — check fails** (cause not investigated) |
| Rows with blank date/region | 0 |
| Negative consumption values | 0 |
| Negative production values | **112,835 — check fails** (clipped to 0) |
| Region-days with a full day of data | 100 % |
| Regions present | 12 |
| Gaps in the daily calendar | none |

So 5 of 7 checks pass. Missing values are concentrated in the nuclear column for regions without reactors (expected) and in the
pumping column for some regions; they do not affect the indicators used. Duplicated rows cannot inflate energy because daily energy is a mean.

## 5. Key findings (full period, all regions; values shown by the app at the time of writing)

- About **93 %** of production is low-carbon (≈ 7,177 TWh produced between 2013 and August 2026), with an estimated **≈ 41 gCO₂/kWh** using my assumed factors.
- Large regional gap: from **45 %** low-carbon in Île-de-France to **99.6 %** in Centre-Val de Loire.
- Île-de-France is the most carbon-intensive producer in the selection (≈ 325 gCO₂/kWh under my assumptions).
- Self-sufficiency is very uneven: **6 of 12** regions produce more than they consume; coverage ranges from about **5 %** (Île-de-France) to **407 %** (Centre-Val de Loire).
- Wind + solar rose from about **3.7 %** (2013) to **16.9 %** (2026, partial year) of production, while estimated CO₂ intensity fell from about 44 to 28 g/kWh. The comparison involves a partial 2026 year and fixed emission factors, so it is indicative only.
- Seasonality is clear: solar peaks in summer, wind in winter, and some regions (e.g. Île-de-France) have a much lower low-carbon share in winter.

## 6. Implications and next steps

- Decarbonisation effort matters most where thermal output still dominates the regional mix.
- Inter-regional links and storage matter where coverage is structurally very low or very high.
- Next steps: hourly profiles (peak vs off-peak), real inter-regional flows, installed capacity and load factors,
  and consumption-based carbon intensity.

## 7. Limitations, ethics and uncertainty

- **Production is not consumption:** regions import and export electricity, so the CO₂ intensity describes local production only.
- **Emission factors are assumptions** (fixed over time); results depend most on the thermal factor.
- **Estimates and consolidation:** part of the data is estimated by the publisher; the 2026 values are partial.
- **Map positions** are approximate region centres, not plant locations.
- **No personal data** is used (regional aggregates only), so there is no re-identification risk.
- Results are descriptive; nothing here proves causality, and the what-if scenarios are explorations, not forecasts.

## 8. Engineering and reproducibility

- Modular structure as recommended: `app.py`, `sections/` (intro, overview, deep dives, quality, conclusions), `utils/` (io, prep, viz).
- `st.cache_data` for loading and tables; heavy work (chunked read and aggregation) is done once outside the app.
- Pinned `requirements.txt`, a `Makefile`, a download script with caching, and a `seeds.json` used only by the synthetic test-data generator
  (the real pipeline is deterministic). An automated smoke test runs the app with Streamlit's `AppTest`.
- Accessibility: colour-blind-safe palette, units on all axes, tooltips, and a text description under each chart.

## 9. Tools and AI assistance

I used Claude (Anthropic's AI assistant) to help build the code and documentation of this project. I chose the topic and checked
the results in the running app and the figures reported above. *(Edit or remove this line according to EFREI's policy on AI-assisted work.)*
