"""Section 1 – Hook, context, audience, questions."""
import streamlit as st

from utils.io import DATASET_PAGE, DATASET_TITLE, LICENSE, PUBLISHER


def render(ctx: dict) -> None:
    st.title("⚡ One grid, twelve energy stories")
    st.caption(f"Source: {DATASET_TITLE} — {PUBLISHER} — {LICENSE} · "
               f"[dataset page]({DATASET_PAGE})")
    if ctx["is_sample"]:
        st.error("⚠️ SYNTHETIC DEMO DATA — numbers are invented for offline testing. "
                 "Run `python scripts/fetch_data.py` and restart the app to use the real RTE data.")

    st.markdown("## 1 · Why this matters")
    st.markdown(
        "France's electricity is often described with a single national number. But the "
        "grid is made of **regions that produce very different things**: some are nuclear "
        "strongholds, others lean on hydro, wind or solar, and some produce far less than "
        "they consume. The energy transition therefore **does not look the same "
        "everywhere** — and neither do the decisions it calls for."
    )
    c1, c2, c3 = st.columns(3)
    c1.info("**Audience**  \nRegional planners, energy-transition advisers, curious citizens.")
    c2.info("**Questions**  \n1. How low-carbon is each region's production?  \n"
            "2. Who covers its own demand, and who depends on others?  \n"
            "3. How fast are wind and solar growing, and what if they grew faster?")
    c3.info("**Take-aways**  \nThe mix, the carbon intensity and the self-sufficiency of regions "
            "diverge strongly; renewables reshape the seasons; scenarios show where effort pays off most.")

    with st.expander("📖 Context, definitions & how to read this dashboard"):
        st.markdown(
            """
            **Data.** Half-hourly *consolidated and definitive* regional éCO2mix data published by RTE
            (metered values completed with flat-rate estimates), from January 2013 (Corsica is not in the file, so 12 regions). We aggregate it to
            *daily energy per region* (MWh) once, outside the app, for speed.

            **Story arc.** Hook → Context → Overview (KPIs & trends) → Deep dives (map, ranking, mix, distribution,
            seasonality) → What-if → Data quality → Insights & next steps.

            **Definitions.**
            - *Low-carbon share* = (nuclear + wind + solar + hydro + bioenergy) / total production.
            - *Renewable share* = (wind + solar + hydro + bioenergy) / total production.
            - *Coverage rate* = regional production / regional consumption (>100 % ⇒ net exporter of electricity).
            - *CO₂ intensity* = life-cycle emissions of the regional production mix (gCO₂eq per kWh produced),
              using fixed emission factors per source (see sidebar › Assumptions). It describes **local
              production**, not the electricity actually consumed (imports from other regions are ignored).

            **Use the sidebar** to filter regions, change the period, choose the metric shown on the map /
            ranking / heatmap, or change the thermal emission factor.
            """
        )
