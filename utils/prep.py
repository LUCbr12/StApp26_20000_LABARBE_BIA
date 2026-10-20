"""Cleaning, validation and feature engineering for the éCO2mix regional dataset.

The raw file is half-hourly (≈1M rows). We never keep it in memory: it is read in
chunks and pre-aggregated to one row per (region, day) with energy in MWh.

Column names of the raw file are matched *by meaning* (accent / case / punctuation
insensitive) so that small changes in the publisher's headers do not break the app.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Constants / documented assumptions
# --------------------------------------------------------------------------- #
SOURCES = ["thermique", "nucleaire", "eolien", "solaire", "hydraulique", "bioenergies"]
LOW_CARBON = ["nucleaire", "eolien", "solaire", "hydraulique", "bioenergies"]
RENEWABLE = ["eolien", "solaire", "hydraulique", "bioenergies"]

LABELS = {
    "thermique": "Thermal (gas/coal/oil)",
    "nucleaire": "Nuclear",
    "eolien": "Wind",
    "solaire": "Solar",
    "hydraulique": "Hydro",
    "bioenergies": "Bioenergy",
}

# Life-cycle emission factors, gCO2eq per kWh produced.
# ASSUMPTION: round values in the range of IPCC AR5 / ADEME life-cycle figures. The
# thermal factor is the most uncertain (gas vs coal vs oil mix) and is editable in the UI.
EMISSION_FACTORS = {
    "thermique": 450.0,
    "nucleaire": 6.0,
    "eolien": 12.0,
    "solaire": 30.0,
    "hydraulique": 6.0,
    "bioenergies": 230.0,
}

# Approximate region centroids (lat, lon) for the bubble map, keyed by INSEE region code.
REGIONS = {
    "11": ("Île-de-France", 48.71, 2.49),
    "24": ("Centre-Val de Loire", 47.48, 1.68),
    "27": ("Bourgogne-Franche-Comté", 47.24, 4.81),
    "28": ("Normandie", 49.12, 0.11),
    "32": ("Hauts-de-France", 50.00, 2.80),
    "44": ("Grand Est", 48.70, 5.60),
    "52": ("Pays de la Loire", 47.47, -0.82),
    "53": ("Bretagne", 48.20, -2.90),
    "75": ("Nouvelle-Aquitaine", 45.20, 0.30),
    "76": ("Occitanie", 43.70, 2.10),
    "84": ("Auvergne-Rhône-Alpes", 45.50, 4.60),
    "93": ("Provence-Alpes-Côte d'Azur", 43.95, 6.05),
    "94": ("Corse", 42.15, 9.10),
}

HALF_HOUR_TO_DAILY = 24.0  # mean power (MW) over the day x 24 h = energy (MWh)

METRICS = {
    "Low-carbon share (%)": "low_carbon_share",
    "Renewable share (%)": "renewable_share",
    "CO₂ intensity (gCO₂/kWh)": "co2_intensity",
    "Coverage rate (production / consumption, %)": "coverage",
    "Solar share (%)": "solar_share",
    "Wind share (%)": "wind_share",
}
METRIC_UNITS = {
    "low_carbon_share": "%",
    "renewable_share": "%",
    "co2_intensity": "gCO₂/kWh",
    "coverage": "%",
    "solar_share": "%",
    "wind_share": "%",
}


# --------------------------------------------------------------------------- #
# Raw-file parsing
# --------------------------------------------------------------------------- #
def norm(text: str) -> str:
    """Lower-case, strip accents and punctuation: 'Nucléaire (MW)' -> 'nucleaire mw'."""
    t = unicodedata.normalize("NFKD", str(text))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


def resolve_columns(columns: list[str]) -> dict[str, str]:
    """Map canonical names -> actual raw column names. Raises if essentials are missing."""
    n = {c: norm(c) for c in columns}
    found: dict[str, str] = {}

    def pick(key, predicate):
        for col, nc in n.items():
            if predicate(nc):
                found[key] = col
                return

    pick("region_code", lambda s: "code insee" in s and "region" in s)
    pick("region", lambda s: s in ("region", "libelle region", "nom region"))
    pick("datetime", lambda s: s in ("date heure", "date et heure", "datetime"))
    pick("date", lambda s: s == "date")
    pick("conso", lambda s: s.startswith("consommation") and s.endswith("mw"))
    for src in SOURCES:
        pick(src, lambda s, k=src: s == f"{k} mw")
        if src not in found:  # fallback: 'xxx mw' with prefix but not TCO/TCH/sub-types
            pick(src, lambda s, k=src: s.startswith(k) and s.endswith("mw")
                 and not s.startswith(("tco", "tch")) and "terrestre" not in s and "offshore" not in s)
    pick("pompage", lambda s: s.startswith("pompage") and s.endswith("mw"))
    pick("echanges", lambda s: s.startswith("ech") and "physiques" in s and s.endswith("mw"))

    essentials = ["conso", "nucleaire", "eolien", "solaire", "hydraulique"]
    missing = [k for k in essentials if k not in found]
    if missing or ("date" not in found and "datetime" not in found):
        raise ValueError(
            f"Unrecognised file schema. Missing columns for: {missing or 'date'}. "
            f"Columns seen: {list(columns)}"
        )
    if "region_code" not in found and "region" not in found:
        raise ValueError("Neither a region code nor a region name column was found.")
    return found


def _sniff_sep(path: Path) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        head = fh.readline()
    return max([";", ",", "\t"], key=head.count)


def aggregate_raw_csv(path: str | Path, chunksize: int = 250_000, progress=None):
    """Stream the half-hourly CSV into a daily (region x day) table + quality report.

    Returns (daily_df, quality_dict).
    """
    path = Path(path)
    sep = _sniff_sep(path)
    header = pd.read_csv(path, sep=sep, nrows=0, encoding="utf-8-sig").columns.tolist()
    cols = resolve_columns(header)
    value_keys = ["conso"] + [s for s in SOURCES if s in cols] + [k for k in ("pompage", "echanges") if k in cols]

    sums, counts, miss_parts, neg_counts = [], [], [], {k: 0 for k in value_keys}
    key_hashes: list[np.ndarray] = []
    total_rows = blank_rows = 0
    usecols = list(dict.fromkeys(cols.values()))

    for i, chunk in enumerate(pd.read_csv(path, sep=sep, usecols=usecols, chunksize=chunksize,
                                          encoding="utf-8-sig", dtype=str)):
        total_rows += len(chunk)
        c = chunk.rename(columns={v: k for k, v in cols.items()})
        # --- keys ---------------------------------------------------------- #
        code = c["region_code"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip() \
            if "region_code" in c else None
        name = c["region"].astype(str).str.strip() if "region" in c else None
        if code is None:  # derive code from name through the lookup table
            lookup = {norm(v[0]): k for k, v in REGIONS.items()}
            code = name.map(lambda x: lookup.get(norm(x), x))
        if name is None:
            name = code.map(lambda x: REGIONS.get(x, (x,))[0])
        stamp = c["datetime"] if "datetime" in c else (c["date"].astype(str) + " " + c.get("heure", ""))
        dates = pd.to_datetime(c["date"] if "date" in c else stamp.str[:10], errors="coerce")
        blank = dates.isna() | code.isna() | code.isin(["", "nan"])
        blank_rows += int(blank.sum())
        key_hashes.append(pd.util.hash_pandas_object(pd.DataFrame({"c": code, "t": stamp}), index=False).values)

        # --- numeric ------------------------------------------------------- #
        num = pd.DataFrame({k: pd.to_numeric(c[k].str.replace(",", ".", regex=False), errors="coerce")
                            for k in value_keys})
        for k in value_keys:
            neg_counts[k] += int((num[k] < 0).sum())
        num["region_code"], num["region"], num["date"] = code, name, dates
        num = num[~blank]
        g = num.groupby(["region_code", "region", "date"])
        sums.append(g[value_keys].sum(min_count=1))
        counts.append(g[value_keys].count().add_suffix("__n"))
        counts[-1]["n_obs"] = g.size()
        na = num[value_keys].isna().astype(int)
        na["region_code"] = num["region_code"].values
        miss = na.groupby("region_code").sum()
        miss["rows"] = na.groupby("region_code").size()
        miss_parts.append(miss)
        if progress:
            progress(total_rows)

    s = pd.concat(sums).groupby(level=[0, 1, 2]).sum(min_count=1)
    n = pd.concat(counts).groupby(level=[0, 1, 2]).sum()
    daily = pd.DataFrame(index=s.index)
    for k in value_keys:
        # mean power over valid half-hours x 24 h -> MWh/day (robust to missing rows)
        daily[k] = (s[k] / n[f"{k}__n"].replace(0, np.nan)) * HALF_HOUR_TO_DAILY
    daily["n_obs"] = n["n_obs"]
    daily = daily.reset_index()
    for k in SOURCES:
        if k not in daily:
            daily[k] = 0.0

    # --- quality report -------------------------------------------------- #
    hashes = np.concatenate(key_hashes)
    miss_all = pd.concat(miss_parts).groupby(level=0).sum()
    quality = {
        "rows_read": int(total_rows),
        "rows_dropped_blank": int(blank_rows),
        "duplicate_keys": int(len(hashes) - len(np.unique(hashes))),
        "negative_values": {k: int(v) for k, v in neg_counts.items()},
        "missing_by_region": miss_all.reset_index().to_dict(orient="records"),
        "value_columns": value_keys,
        "raw_columns_matched": {k: v for k, v in cols.items()},
    }
    daily = clean_daily(daily)
    return daily, quality


def clean_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Type, fill and sanity-clean the daily table."""
    df = df.copy()
    df["region_code"] = df["region_code"].astype(str)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(["region_code", "date"])
    # Regions without a given source report blanks -> treat as 0 production (documented).
    for k in SOURCES:
        df[k] = df[k].fillna(0.0).clip(lower=0.0)
    df["conso"] = df["conso"].clip(lower=0.0)
    for k in ("pompage", "echanges"):
        if k not in df:
            df[k] = np.nan
    # Harmonise region label with the INSEE code when known
    df["region"] = df.apply(lambda r: REGIONS.get(r["region_code"], (r["region"],))[0], axis=1)
    return df.sort_values(["region_code", "date"]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Feature engineering
# --------------------------------------------------------------------------- #
def add_features(df: pd.DataFrame, thermal_factor: float | None = None) -> pd.DataFrame:
    """Add production totals, shares, CO2 and calendar features (row level)."""
    f = dict(EMISSION_FACTORS)
    if thermal_factor is not None:
        f["thermique"] = float(thermal_factor)
    out = df.copy()
    out["production"] = out[SOURCES].sum(axis=1)
    out["low_carbon"] = out[LOW_CARBON].sum(axis=1)
    out["renewable"] = out[RENEWABLE].sum(axis=1)
    out["co2_kg"] = sum(out[s] * f[s] for s in SOURCES)  # MWh * g/kWh = kg
    out["year"] = out["date"].dt.year
    out["month"] = out["date"].dt.month
    out["month_start"] = out["date"].dt.to_period("M").dt.to_timestamp()
    return out


def summarize(df: pd.DataFrame) -> dict:
    """KPI dictionary for any slice of the (feature-enriched) daily table."""
    prod = df["production"].sum()
    conso = df["conso"].sum()
    if prod <= 0:
        return {k: np.nan for k in ("prod_twh", "conso_twh", "low_carbon_share", "renewable_share",
                                    "solar_share", "wind_share", "co2_intensity", "coverage")}
    return {
        "prod_twh": prod / 1e6,
        "conso_twh": conso / 1e6,
        "low_carbon_share": 100 * df["low_carbon"].sum() / prod,
        "renewable_share": 100 * df["renewable"].sum() / prod,
        "solar_share": 100 * df["solaire"].sum() / prod,
        "wind_share": 100 * df["eolien"].sum() / prod,
        "co2_intensity": df["co2_kg"].sum() / prod,  # kg/MWh == g/kWh
        "coverage": 100 * prod / conso if conso > 0 else np.nan,
    }


def group_summary(df: pd.DataFrame, by) -> pd.DataFrame:
    """Vectorised `summarize` per group (used for rankings, maps, heatmaps)."""
    g = df.groupby(by, observed=True)[
        ["production", "conso", "low_carbon", "renewable", "solaire", "eolien", "co2_kg"]].sum()
    g = g[g["production"] > 0]
    out = pd.DataFrame(index=g.index)
    out["prod_twh"] = g["production"] / 1e6
    out["conso_twh"] = g["conso"] / 1e6
    out["low_carbon_share"] = 100 * g["low_carbon"] / g["production"]
    out["renewable_share"] = 100 * g["renewable"] / g["production"]
    out["solar_share"] = 100 * g["solaire"] / g["production"]
    out["wind_share"] = 100 * g["eolien"] / g["production"]
    out["co2_intensity"] = g["co2_kg"] / g["production"]
    out["coverage"] = 100 * g["production"] / g["conso"].replace(0, np.nan)
    return out.reset_index()


def make_tables(daily: pd.DataFrame, thermal_factor: float | None = None) -> dict[str, pd.DataFrame]:
    """Pre-aggregated tables used by the sections."""
    d = add_features(daily, thermal_factor)
    d["co2_intensity_day"] = np.where(d["production"] > 0, d["co2_kg"] / d["production"], np.nan)
    d["low_carbon_share_day"] = np.where(d["production"] > 0, 100 * d["low_carbon"] / d["production"], np.nan)
    return {"daily": d}


def monthly_mix(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly production by source in TWh (long format)."""
    m = df.groupby("month_start")[SOURCES].sum() / 1e6
    long = m.reset_index().melt("month_start", var_name="source", value_name="twh")
    long["source"] = long["source"].map(LABELS)
    return long


def monthly_kpis(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("month_start")[["production", "conso", "low_carbon", "renewable", "co2_kg", "solaire", "eolien"]].sum()
    g = g[g["production"] > 0]
    out = pd.DataFrame(index=g.index)
    out["low_carbon_share"] = 100 * g["low_carbon"] / g["production"]
    out["renewable_share"] = 100 * g["renewable"] / g["production"]
    out["solar_share"] = 100 * g["solaire"] / g["production"]
    out["wind_share"] = 100 * g["eolien"] / g["production"]
    out["co2_intensity"] = g["co2_kg"] / g["production"]
    out["coverage"] = 100 * g["production"] / g["conso"].replace(0, np.nan)
    return out.reset_index()


def what_if(df: pd.DataFrame, solar_pct: float, wind_pct: float, thermal_cut_pct: float,
            thermal_factor: float) -> pd.DataFrame:
    """Scenario: scale solar / wind / thermal output. Returns per-region before / after.

    ASSUMPTIONS (documented in the UI): demand unchanged, linear scaling of historical
    output, no curtailment, storage or grid constraints, other sources unchanged.
    """
    base = df.copy()
    scen = df.copy()
    scen["solaire"] *= 1 + solar_pct / 100
    scen["eolien"] *= 1 + wind_pct / 100
    scen["thermique"] *= 1 - thermal_cut_pct / 100
    res = []
    for label, frame in (("Baseline", base), ("Scenario", scen)):
        e = add_features(frame, thermal_factor)
        s = group_summary(e, "region")
        s["case"] = label
        res.append(s)
    return pd.concat(res, ignore_index=True)


# --------------------------------------------------------------------------- #
# Validation checks on the daily table
# --------------------------------------------------------------------------- #
def validation_checks(daily: pd.DataFrame, quality: dict) -> pd.DataFrame:
    expected = 48
    full_days = ((daily["n_obs"] >= 46) & (daily["n_obs"] <= 50)).mean() * 100
    checks = [
        ("No duplicated (region, timestamp) keys", quality.get("duplicate_keys", 0) == 0,
         f"{quality.get('duplicate_keys', 0):,} duplicated keys"),
        ("No rows with blank date / region", quality.get("rows_dropped_blank", 0) == 0,
         f"{quality.get('rows_dropped_blank', 0):,} blank rows dropped"),
        ("Consumption never negative (raw)", quality.get("negative_values", {}).get("conso", 0) == 0,
         f"{quality.get('negative_values', {}).get('conso', 0):,} negative values"),
        ("Production never negative (raw)",
         sum(quality.get("negative_values", {}).get(s, 0) for s in SOURCES) == 0,
         f"{sum(quality.get('negative_values', {}).get(s, 0) for s in SOURCES):,} negative values (clipped to 0)"),
        (f"≥ 95 % of region-days have a full day of data (≈{expected} half-hours)", full_days >= 95,
         f"{full_days:.1f} % of region-days complete"),
        ("All regions present", daily["region_code"].nunique() >= 12,
         f"{daily['region_code'].nunique()} regions found"),
        ("Continuous calendar per region", bool(
            (daily.groupby("region_code")["date"].agg(lambda s: (s.max() - s.min()).days + 1 - s.nunique()) == 0).all()),
         "no gaps in daily series" if (daily.groupby("region_code")["date"].agg(
             lambda s: (s.max() - s.min()).days + 1 - s.nunique()) == 0).all() else "gaps detected"),
    ]
    return pd.DataFrame(checks, columns=["Check", "Passed", "Detail"])
