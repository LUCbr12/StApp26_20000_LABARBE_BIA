"""Section 3 – Regional comparisons, distributions, seasonality; Section 4 – what-if."""
import streamlit as st

from utils import viz
from utils.prep import METRIC_UNITS, group_summary, summarize, what_if


def render(ctx: dict) -> None:
    df, label, col = ctx["df"], ctx["metric_label"], ctx["metric"]
    unit = METRIC_UNITS[col]
    st.markdown("## 3 · Regions side by side")
    by_reg = group_summary(df, ["region_code", "region"])
    if by_reg.empty:
        st.warning("No production data for this selection.")
        return
    top, bot = by_reg.loc[by_reg[col].idxmax()], by_reg.loc[by_reg[col].idxmin()]
    st.markdown(
        f"**Headline:** on *{label}*, **{top['region']}** leads with {top[col]:.1f} {unit} while "
        f"**{bot['region']}** trails at {bot[col]:.1f} {unit} — a gap of {top[col] - bot[col]:.1f} {unit}."
    )

    left, right = st.columns([3, 2])
    with left:
        viz.show(viz.map_bubbles(by_reg, col, f"{label} by region (bubble size = production, TWh)"),
                 "Map of France with one bubble per region. Bubble size is total production in TWh and colour is the "
                 f"selected metric ({label}). Hover for exact values.", modebar=False)
    with right:
        nat = summarize(df)[col]
        viz.show(viz.bar_rank(by_reg, col, f"Ranking – {label}", ref=nat, ref_label=f"selection avg {nat:.1f}"),
                 f"Horizontal bar ranking of regions by {label}, with a dotted line at the selection average.")

    st.markdown("### Same data, different mixes")
    viz.show(viz.small_multiples_mix(df),
             "Small multiples: one panel per region, each showing stacked bars of the production mix (share of output) "
             "for every year. Compare how the mix shifts from year to year inside each region.")

    st.markdown("### How variable is each region day to day?")
    dist_col = "co2_intensity_day" if col == "co2_intensity" else "low_carbon_share_day"
    dist_title = ("Daily CO₂ intensity by region (gCO₂/kWh)" if col == "co2_intensity"
                  else "Daily low-carbon share by region (%)")
    viz.show(viz.box_distribution(df.dropna(subset=[dist_col]), dist_col, dist_title),
             "Box plots of daily values per region, sorted by median. Wide boxes mean a volatile mix; "
             "whiskers show the range of typical days.")
    st.caption("The distribution view uses CO₂ intensity when that metric is selected and the low-carbon share otherwise.")

    st.markdown("### Seasons shape the story")
    viz.show(viz.heatmap_month_region(df, col, f"{label} – month of year × region"),
             f"Heatmap of {label} for each region (rows) and calendar month (columns), averaged over the selected period. "
             "Darker/brighter cells mark seasonal highs and lows.")


def render_what_if(ctx: dict) -> None:
    df = ctx["df"]
    st.markdown("## 4 · What if…?")
    st.markdown("**Headline:** a few sliders show where extra wind and solar — or less thermal generation — "
                "would move each region the most.")
    c1, c2, c3 = st.columns(3)
    solar = c1.slider("Solar output change (%)", 0, 300, 50, step=10,
                      help="Scales historical solar output of every selected region by (1 + x %).")
    wind = c2.slider("Wind output change (%)", 0, 300, 50, step=10,
                     help="Scales historical wind output of every selected region by (1 + x %).")
    thermal = c3.slider("Thermal output cut (%)", 0, 100, 25, step=5,
                        help="Removes x % of historical thermal output (no replacement is assumed).")
    res = what_if(df, solar, wind, thermal, ctx["thermal_factor"])
    def _w(case):  # production-weighted selection totals (consistent with the headline KPIs)
        r = res[res["case"] == case]
        return ((r["co2_intensity"] * r["prod_twh"]).sum() / r["prod_twh"].sum(),
                100 * r["prod_twh"].sum() / r["conso_twh"].sum())
    base, cov_b = _w("Baseline")
    scen, cov_s = _w("Scenario")
    k1, k2 = st.columns(2)
    k1.metric("CO₂ intensity (selection)", f"{scen:.0f} g/kWh", f"{scen - base:+.0f} g/kWh vs baseline", delta_color="inverse")
    k2.metric("Coverage rate (selection)", f"{cov_s:.0f} %", f"{cov_s - cov_b:+.0f} pts vs baseline")
    a, b = st.columns(2)
    with a:
        viz.show(viz.before_after(res, "co2_intensity", "CO₂ intensity: baseline vs scenario (gCO₂/kWh)"),
                 "Grouped bars per region comparing CO₂ intensity before and after the scenario.")
    with b:
        viz.show(viz.before_after(res, "coverage", "Coverage rate: baseline vs scenario (%)"),
                 "Grouped bars per region comparing production÷consumption before and after the scenario.")
    st.warning(
        "**Assumptions & limits.** Historical daily output is scaled linearly; demand is unchanged; "
        "no curtailment, storage, grid-capacity or investment-cost constraints; other sources unchanged; "
        "selection totals are production-weighted, like the headline KPIs. This is an exploration tool, **not a forecast**."
    )
