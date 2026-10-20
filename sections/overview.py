"""Section 2 – KPI header and national / selection trends."""
import numpy as np
import streamlit as st

from utils import viz
from utils.prep import monthly_kpis, monthly_mix, summarize


def _delta(df, key):
    """Latest 12 months of the selection vs the 12 months before (None if not enough data)."""
    end = df["date"].max()
    cut1 = end - np.timedelta64(365, "D")
    cut0 = cut1 - np.timedelta64(365, "D")
    last, prev = df[df["date"] > cut1], df[(df["date"] > cut0) & (df["date"] <= cut1)]
    if len(prev) < 300 * max(1, df["region"].nunique()) * 0.9:
        return None
    return summarize(last)[key] - summarize(prev)[key]


def render(ctx: dict) -> None:
    df = ctx["df"]
    st.markdown("## 2 · The big picture")
    kp = summarize(df)
    m = monthly_kpis(df)
    n_reg = df["region"].nunique()
    st.markdown(
        f"**Headline:** across **{n_reg} region(s)** between {df['date'].min():%b %Y} and {df['date'].max():%b %Y}, "
        f"**{kp['low_carbon_share']:.0f} %** of production was low-carbon, emitting about "
        f"**{kp['co2_intensity']:.0f} gCO₂/kWh**."
    )

    def metric(col, label, value, fmt, key, unit, inverse=False, help_=None):
        d = _delta(df, key)
        col.metric(label, fmt.format(value), None if d is None else f"{d:+.1f} {unit} YoY",
                   delta_color="inverse" if inverse else "normal",
                   help=(help_ or "") + " Δ = latest 12 months vs the 12 months before (YoY).")

    c1, c2, c3, c4, c5 = st.columns(5)
    metric(c1, "Production", kp["prod_twh"], "{:.1f} TWh", "prod_twh", "TWh",
           help_="Total electricity produced in the selected regions and period.")
    metric(c2, "Low-carbon share", kp["low_carbon_share"], "{:.1f} %", "low_carbon_share", "pts",
           help_="Nuclear + wind + solar + hydro + bioenergy, as a share of production.")
    metric(c3, "Renewable share", kp["renewable_share"], "{:.1f} %", "renewable_share", "pts",
           help_="Wind + solar + hydro + bioenergy, as a share of production.")
    metric(c4, "CO₂ intensity", kp["co2_intensity"], "{:.0f} g/kWh", "co2_intensity", "g", inverse=True,
           help_="Life-cycle emissions of the regional production mix. Lower is better.")
    metric(c5, "Coverage rate", kp["coverage"], "{:.0f} %", "coverage", "pts",
           help_="Production ÷ consumption. Above 100 % the selection is a net exporter.")

    st.markdown("")
    viz.show(viz.area_mix(monthly_mix(df)),
             "Stacked area chart of monthly electricity production in TWh by source (thermal, nuclear, wind, solar, "
             "hydro, bioenergy) for the selected regions. Nuclear and hydro form the base; solar peaks in summer and wind in winter.")

    a, b = st.columns(2)
    with a:
        ref = kp["co2_intensity"]
        viz.show(viz.line_metric(m, "co2_intensity", "CO₂ intensity of production (gCO₂/kWh)", color="#D55E00",
                                 ref=ref, ref_label=f"period average {ref:.0f}"),
                 "Monthly line of the CO₂ intensity of regional production with peak and low annotated and a dotted line "
                 "at the period average.")
    with b:
        ref = kp["low_carbon_share"]
        viz.show(viz.line_metric(m, "low_carbon_share", "Low-carbon share of production (%)", color="#009E73",
                                 ref=ref, ref_label=f"period average {ref:.0f} %"),
                 "Monthly line of the low-carbon share of production with peak and low annotated and a dotted line at the "
                 "period average.")
