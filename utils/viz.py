"""Chart helpers: one consistent style, labelled axes with units, colour-blind-safe palette."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.prep import LABELS, METRIC_UNITS, REGIONS, SOURCES

# Okabe-Ito based palette: distinguishable for the common colour-vision deficiencies.
SOURCE_COLORS = {
    LABELS["thermique"]: "#555555",
    LABELS["nucleaire"]: "#E69F00",
    LABELS["eolien"]: "#56B4E9",
    LABELS["solaire"]: "#F0E442",
    LABELS["hydraulique"]: "#0072B2",
    LABELS["bioenergies"]: "#009E73",
}
SOURCE_ORDER = [LABELS[s] for s in SOURCES]
SEQ_SCALE = "Viridis"
FONT = dict(family="Inter, Arial, sans-serif", size=14, color="#1a1a1a")


def style(fig: go.Figure, title: str, xtitle: str | None = None, ytitle: str | None = None,
          height: int = 420) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=16)),
        font=FONT, height=height, margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    if xtitle is not None:
        fig.update_xaxes(title=xtitle)
    if ytitle is not None:
        fig.update_yaxes(title=ytitle)
    fig.update_xaxes(showline=True, linecolor="#888", gridcolor="#eee")
    fig.update_yaxes(showline=True, linecolor="#888", gridcolor="#eee")
    return fig


def show(fig: go.Figure, alt: str, modebar: bool = True) -> None:
    """Render a Plotly figure with a text alternative shown below it."""
    cfg = {"displayModeBar": modebar}
    try:
        st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError:  # Streamlit < 1.50
        st.plotly_chart(fig, use_container_width=True, config=cfg)
    st.caption(f"♿ Chart description: {alt}")


# --------------------------------------------------------------------------- #
def area_mix(long: pd.DataFrame, title="Monthly electricity production by source") -> go.Figure:
    fig = px.area(long, x="month_start", y="twh", color="source",
                  category_orders={"source": SOURCE_ORDER}, color_discrete_map=SOURCE_COLORS,
                  labels={"month_start": "Month", "twh": "Production (TWh)", "source": "Source"})
    fig.update_traces(hovertemplate="%{x|%b %Y}<br>%{fullData.name}: %{y:.2f} TWh<extra></extra>")
    return style(fig, title, "Month", "Production (TWh per month)")


def line_metric(monthly: pd.DataFrame, col: str, title: str, color="#0072B2",
                annotate_extremes=True, ref: float | None = None, ref_label: str = "") -> go.Figure:
    unit = METRIC_UNITS[col]
    fig = go.Figure(go.Scatter(x=monthly["month_start"], y=monthly[col], mode="lines+markers",
                               line=dict(color=color, width=2.5), marker=dict(size=5),
                               hovertemplate=f"%{{x|%b %Y}}<br>%{{y:.1f}} {unit}<extra></extra>",
                               name=title))
    if ref is not None:
        fig.add_hline(y=ref, line_dash="dot", line_color="#D55E00",
                      annotation_text=ref_label, annotation_position="top left",
                      annotation_font_color="#D55E00", annotation_bgcolor="rgba(255,255,255,0.85)")
    if annotate_extremes and len(monthly) > 2:
        hi = monthly.loc[monthly[col].idxmax()]
        lo = monthly.loc[monthly[col].idxmin()]
        for r, tag in ((hi, "peak"), (lo, "low")):
            fig.add_annotation(x=r["month_start"], y=r[col], text=f"{tag}: {r[col]:.1f}",
                               showarrow=True, arrowhead=2, ax=0, ay=-30 if tag == "peak" else 30,
                               font=dict(size=12))
    lo_v, hi_v = float(monthly[col].min()), float(monthly[col].max())
    pad = max((hi_v - lo_v) * 0.25, 1e-6)
    fig.update_yaxes(range=[lo_v - pad, hi_v + pad])
    fig.update_layout(showlegend=False)
    return style(fig, title, "Month", f"{unit}", height=360)


def bar_rank(df: pd.DataFrame, col: str, title: str, ref: float | None = None, ref_label="") -> go.Figure:
    unit = METRIC_UNITS[col]
    d = df.sort_values(col, ascending=True)
    fig = px.bar(d, x=col, y="region", orientation="h", color=col, color_continuous_scale=SEQ_SCALE,
                 labels={col: f"{unit}", "region": "Region"}, text=d[col].round(1))
    fig.update_traces(hovertemplate=f"%{{y}}<br>%{{x:.1f}} {unit}<extra></extra>", textposition="outside")
    if ref is not None:
        fig.add_vline(x=ref, line_dash="dot", line_color="#D55E00", annotation_text=ref_label,
                      annotation_position="top", annotation_font_color="#D55E00")
    fig.update_coloraxes(showscale=False)
    return style(fig, title, unit, "Region", height=max(360, 32 * len(d) + 120))


def map_bubbles(df: pd.DataFrame, col: str, title: str) -> go.Figure:
    unit = METRIC_UNITS[col]
    d = df.copy()
    d["lat"] = d["region_code"].map(lambda c: REGIONS.get(c, (None, None, None))[1])
    d["lon"] = d["region_code"].map(lambda c: REGIONS.get(c, (None, None, None))[2])
    d = d.dropna(subset=["lat", "lon"])
    fig = px.scatter_map(d, lat="lat", lon="lon", size="prod_twh", color=col, hover_name="region",
                         hover_data={"lat": False, "lon": False, "prod_twh": ":.1f", col: ":.1f"},
                         color_continuous_scale=SEQ_SCALE, size_max=48, zoom=4.6,
                         center=dict(lat=46.6, lon=2.5), map_style="carto-positron",
                         labels={col: unit, "prod_twh": "Production (TWh)"})
    fig.update_layout(coloraxis_colorbar=dict(title=unit))
    fig = style(fig, title, height=520)
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=30))
    return fig


def small_multiples_mix(df: pd.DataFrame, title="Production mix by region and year (share of output, %)") -> go.Figure:
    g = df.groupby(["region", "year"])[SOURCES].sum().reset_index()
    long = g.melt(["region", "year"], var_name="source", value_name="mwh")
    tot = long.groupby(["region", "year"])["mwh"].transform("sum")
    long["share"] = 100 * long["mwh"] / tot.where(tot > 0)
    long["source"] = long["source"].map(LABELS)
    fig = px.bar(long, x="year", y="share", color="source", facet_col="region", facet_col_wrap=4,
                 category_orders={"source": SOURCE_ORDER}, color_discrete_map=SOURCE_COLORS,
                 labels={"share": "Share (%)", "year": "Year", "source": "Source"}, height=200 * (1 + len(g["region"].unique()) // 4) + 160)
    fig.update_traces(hovertemplate="%{x}<br>%{fullData.name}: %{y:.1f} %<extra></extra>")
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title=None)
    fig.update_layout(barmode="stack", bargap=0.15)
    fig = style(fig, title, height=200 * (1 + len(g["region"].unique()) // 4) + 200)
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.06, x=0, title=None),
                      margin=dict(l=40, r=10, t=60, b=70))
    return fig


def box_distribution(daily: pd.DataFrame, col: str, title: str) -> go.Figure:
    unit = "gCO₂/kWh" if col == "co2_intensity_day" else "%"
    order = daily.groupby("region")[col].median().sort_values().index.tolist()
    fig = px.box(daily, x="region", y=col, category_orders={"region": order}, points=False,
                 labels={col: unit, "region": "Region"}, color_discrete_sequence=["#0072B2"])
    fig.update_xaxes(tickangle=-35)
    return style(fig, title, "Region (sorted by median)", unit, height=460)


def heatmap_month_region(df: pd.DataFrame, col: str, title: str) -> go.Figure:
    unit = METRIC_UNITS[col]
    # compute metric per (region, month-of-year) from sums
    g = df.groupby(["region", "month"])[["production", "conso", "low_carbon", "renewable", "solaire", "eolien", "co2_kg"]].sum()
    g = g[g["production"] > 0]
    vals = {
        "low_carbon_share": 100 * g["low_carbon"] / g["production"],
        "renewable_share": 100 * g["renewable"] / g["production"],
        "solar_share": 100 * g["solaire"] / g["production"],
        "wind_share": 100 * g["eolien"] / g["production"],
        "co2_intensity": g["co2_kg"] / g["production"],
        "coverage": 100 * g["production"] / g["conso"].replace(0, float("nan")),
    }[col]
    pv = vals.unstack("month").reindex(columns=range(1, 13))
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(go.Heatmap(z=pv.values, x=months, y=pv.index, colorscale=SEQ_SCALE,
                               colorbar=dict(title=unit),
                               hovertemplate=f"%{{y}} – %{{x}}<br>%{{z:.1f}} {unit}<extra></extra>"))
    return style(fig, title, "Month of year", "Region", height=max(360, 30 * len(pv) + 140))


def before_after(res: pd.DataFrame, col: str, title: str) -> go.Figure:
    unit = METRIC_UNITS.get(col, "%")
    fig = px.bar(res, x="region", y=col, color="case", barmode="group",
                 color_discrete_map={"Baseline": "#999999", "Scenario": "#009E73"},
                 labels={col: unit, "region": "Region", "case": ""})
    fig.update_xaxes(tickangle=-35)
    fig.update_traces(hovertemplate=f"%{{x}}<br>%{{fullData.name}}: %{{y:.1f}} {unit}<extra></extra>")
    return style(fig, title, "Region", unit, height=420)


def missing_heatmap(miss_pct: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure(go.Heatmap(z=miss_pct.values, x=list(miss_pct.columns), y=list(miss_pct.index),
                               colorscale="Reds", zmin=0, zmax=max(5, float(miss_pct.max().max() or 0)),
                               colorbar=dict(title="% missing"),
                               hovertemplate="%{y} – %{x}<br>%{z:.1f} % missing<extra></extra>"))
    return style(fig, title, "Raw column", "Region", height=max(340, 28 * len(miss_pct) + 140))
