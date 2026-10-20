"""Data-storytelling dashboard – regional electricity mix in France (éCO2mix, RTE).

Run:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="One grid, twelve energy stories", page_icon="⚡", layout="wide")

from sections import conclusions, deep_dives, intro, overview, quality  # noqa: E402
from utils.io import load_data  # noqa: E402
from utils.prep import EMISSION_FACTORS, METRICS, make_tables  # noqa: E402


@st.cache_data(show_spinner="Loading data…")
def get_data():
    daily, quality_report, is_sample = load_data()
    return daily, quality_report, is_sample


@st.cache_data(show_spinner=False)
def get_tables(daily, thermal_factor: float):
    return make_tables(daily, thermal_factor)["daily"]


try:
    daily_all, quality_report, is_sample = get_data()
except Exception as exc:  # friendly failure instead of a stack trace
    st.error("The processed data is missing and could not be downloaded.")
    st.code(f"{type(exc).__name__}: {exc}")
    st.markdown("Run `python scripts/fetch_data.py` once from the project folder, then reload this page.")
    st.stop()

region_names = daily_all.drop_duplicates("region_code").set_index("region_code")["region"].to_dict()

# --------------------------------------------------------------------------- #
# Sidebar controls
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Filters")
    all_regions = sorted(daily_all["region"].unique())
    regions = st.multiselect("Regions", all_regions, default=all_regions,
                             help="Pick one or several regions. Everything on the page updates.")
    dmin, dmax = daily_all["date"].min().date(), daily_all["date"].max().date()
    date_range = st.date_input("Date range", value=(dmin, dmax), min_value=dmin, max_value=dmax,
                               help="Period used by every chart and KPI.")
    metric_label = st.selectbox("Metric for map, ranking & heatmap", list(METRICS), index=0,
                                help="Changes the map, ranking, distribution and seasonal heatmap.")
    with st.expander("Assumptions"):
        thermal_factor = st.slider("Thermal emission factor (gCO₂eq/kWh)", 300, 1000,
                                   int(EMISSION_FACTORS["thermique"]), step=10,
                                   help="Gas ≈ 430, oil ≈ 780, coal ≈ 980. Default is a gas-heavy mix.")
        st.caption("Other factors (g/kWh): nuclear 6, wind 12, solar 30, hydro 6, bioenergy 230.")
    st.divider()
    st.caption("Source: RTE – éCO2mix régional (consolidé & définitif), Licence Ouverte 2.0.")

if not regions:
    st.warning("Select at least one region in the sidebar.")
    st.stop()
if not isinstance(date_range, (list, tuple)) or len(date_range) != 2:
    st.info("Pick an end date to complete the date range.")
    st.stop()

start, end = (str(d) for d in date_range)
tbl = get_tables(daily_all, float(thermal_factor))
df = tbl[(tbl["region"].isin(regions)) & (tbl["date"] >= start) & (tbl["date"] <= end)]
if df.empty:
    st.warning("No data for this selection.")
    st.stop()

ctx = {
    "df": df, "daily_all": daily_all, "quality": quality_report, "is_sample": is_sample,
    "metric_label": metric_label, "metric": METRICS[metric_label],
    "thermal_factor": float(thermal_factor), "region_names": region_names,
}

# --------------------------------------------------------------------------- #
# Narrative
# --------------------------------------------------------------------------- #
intro.render(ctx)
st.divider()
overview.render(ctx)
st.divider()
deep_dives.render(ctx)
st.divider()
deep_dives.render_what_if(ctx)
st.divider()
quality.render(ctx)
st.divider()
conclusions.render(ctx)
