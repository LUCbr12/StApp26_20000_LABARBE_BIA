"""Section 5 – Data quality, validation and limitations."""
import pandas as pd
import streamlit as st

from utils import viz
from utils.prep import validation_checks

PRETTY = {"conso": "Consumption", "thermique": "Thermal", "nucleaire": "Nuclear", "eolien": "Wind",
          "solaire": "Solar", "hydraulique": "Hydro", "bioenergies": "Bioenergy",
          "pompage": "Pumping", "echanges": "Exchanges"}


def render(ctx: dict) -> None:
    daily, q = ctx["daily_all"], ctx["quality"]
    st.markdown("## 5 · Can we trust the data?")
    checks = validation_checks(daily, q)
    n_ok = int(checks["Passed"].sum())
    st.markdown(f"**Headline:** {n_ok}/{len(checks)} validation checks pass; the issues below are small but explained.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Half-hourly rows read", f"{q['rows_read']:,}")
    c2.metric("Duplicated keys", f"{q['duplicate_keys']:,}", help="Same region + timestamp appearing more than once.")
    c3.metric("Region-days", f"{len(daily):,}")
    c4.metric("Period", f"{daily['date'].min():%Y} → {daily['date'].max():%Y}")

    show = checks.assign(Passed=checks["Passed"].map({True: "✅", False: "⚠️"}))
    st.dataframe(show, hide_index=True)

    miss = pd.DataFrame(q["missing_by_region"]).set_index("region_code")
    rows = miss.pop("rows")
    pct = 100 * miss.div(rows, axis=0)
    pct.index = [ctx["region_names"].get(c, c) for c in pct.index]
    pct = pct.rename(columns=PRETTY)
    viz.show(viz.missing_heatmap(pct, "Missing values in the raw file (% of half-hourly rows)"),
             "Heatmap of the share of missing half-hourly values for each region (rows) and raw column (columns). "
             "Dark red marks columns that are blank for most of the period.")

    st.markdown("### Cleaning decisions")
    st.markdown(
        """
        - **Aggregation:** half-hours → daily energy as *mean power × 24 h* over **valid** half-hours, so a few missing
          rows do not understate the day. Duplicated rows therefore do not inflate energy.
        - **Blank production** (e.g. nuclear in a region without reactors) is treated as **0 MWh**. Production < 0 is clipped to 0.
        - **Region names** are harmonised from the INSEE region code.
        - **Not used:** TCO/TCH ratios and detailed wind/battery sub-columns (we recompute shares ourselves for transparency).
        """
    )
    st.markdown("### Limitations & ethics")
    st.markdown(
        """
        - **Production ≠ consumption mix:** regions import/export electricity; CO₂ intensity here describes *local production only*.
        - **Emission factors are assumptions** (life-cycle, fixed over time), especially for thermal plants — editable in the sidebar.
        - **Estimates:** the dataset mixes metering and flat-rate estimates, mostly for small producers.
        - **Regional centroids** on the map are approximate; bubble position is not a plant location.
        - **No personal data:** only regional aggregates, so there is no re-identification risk. Correlation shown here is not causation.
        """
    )
