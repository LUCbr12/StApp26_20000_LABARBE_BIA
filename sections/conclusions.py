"""Section 6 – Insights (computed from the data) and implications."""
import streamlit as st

from utils.prep import group_summary, summarize


def render(ctx: dict) -> None:
    df = ctx["df"]
    st.markdown("## 6 · Insights & next steps")
    by_reg = group_summary(df, "region")
    if by_reg.empty:
        return
    lc_hi, lc_lo = by_reg.loc[by_reg["low_carbon_share"].idxmax()], by_reg.loc[by_reg["low_carbon_share"].idxmin()]
    co_hi = by_reg.loc[by_reg["co2_intensity"].idxmax()]
    cov_hi, cov_lo = by_reg.loc[by_reg["coverage"].idxmax()], by_reg.loc[by_reg["coverage"].idxmin()]
    exporters = int((by_reg["coverage"] > 100).sum())

    years = sorted(df["year"].unique())
    trend = ""
    if len(years) >= 2:
        a, b = summarize(df[df["year"] == years[0]]), summarize(df[df["year"] == years[-1]])
        trend = (f"Between {years[0]} and {years[-1]}, solar + wind went from "
                 f"{a['solar_share'] + a['wind_share']:.1f} % to {b['solar_share'] + b['wind_share']:.1f} % of production "
                 f"and CO₂ intensity moved from {a['co2_intensity']:.0f} to {b['co2_intensity']:.0f} gCO₂/kWh "
                 f"(partial years can bias this comparison).")

    st.success(
        f"""
**Key insights (for the current selection)**

1. **Low-carbon is nearly universal, but not equal:** from **{lc_lo['low_carbon_share']:.1f} %** in {lc_lo['region']} to **{lc_hi['low_carbon_share']:.1f} %** in {lc_hi['region']}.
2. **Carbon intensity hinges on thermal plants:** {co_hi['region']} is the most carbon-intensive producer at {co_hi['co2_intensity']:.0f} gCO₂/kWh.
3. **Self-sufficiency is very uneven:** {exporters} of {len(by_reg)} regions produce more than they consume; coverage ranges from {cov_lo['coverage']:.0f} % ({cov_lo['region']}) to {cov_hi['coverage']:.0f} % ({cov_hi['region']}).
4. **Seasons matter:** solar peaks in summer, wind in winter, nuclear and hydro form the base (see heatmap and area chart).
5. {trend}
        """
    )
    st.info(
        """
**Implications & next steps**
- Target decarbonisation effort where thermal output still dominates the mix.
- Strengthen inter-regional grid links and storage where coverage is structurally low or high.
- Next steps for this analysis: add hourly profiles (peak vs off-peak), real inter-regional flows, regional installed capacity (load factors), and consumption-based CO₂ intensity.
        """
    )
