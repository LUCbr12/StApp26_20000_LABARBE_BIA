"""Synthetic stand-in for the éCO2mix regional CSV (offline development and tests ONLY).

The numbers are invented: shares, seasonality and trends are only loosely inspired by
reality. The app shows a red banner whenever this data is used. It exists so the
pipeline (chunked read -> daily aggregation -> dashboard) can be tested without network.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from utils.prep import REGIONS

# code: (mean consumption MW, nuclear, thermal, hydro, wind, solar, bio) as share of consumption
PROFILE = {
    "11": (6500, 0.00, 0.10, 0.00, 0.00, 0.01, 0.03),
    "24": (1800, 3.20, 0.02, 0.01, 0.12, 0.04, 0.02),
    "27": (1900, 0.00, 0.03, 0.10, 0.12, 0.06, 0.03),
    "28": (2500, 2.10, 0.08, 0.00, 0.12, 0.02, 0.02),
    "32": (4200, 1.30, 0.20, 0.00, 0.30, 0.03, 0.04),
    "44": (4800, 1.60, 0.07, 0.25, 0.30, 0.04, 0.03),
    "52": (2900, 0.00, 0.35, 0.01, 0.30, 0.07, 0.05),
    "53": (1900, 0.00, 0.20, 0.03, 0.40, 0.05, 0.06),
    "75": (4300, 1.50, 0.08, 0.25, 0.12, 0.30, 0.06),
    "76": (3500, 0.80, 0.07, 0.35, 0.25, 0.30, 0.03),
    "84": (6500, 1.50, 0.04, 0.80, 0.10, 0.10, 0.03),
    "93": (3300, 0.00, 0.30, 0.45, 0.01, 0.20, 0.03),
    "94": (200, 0.00, 0.60, 0.20, 0.02, 0.15, 0.00),
}

HEADER = ["Code INSEE région", "Région", "Date - Heure", "Date", "Heure", "Consommation (MW)",
          "Thermique (MW)", "Nucléaire (MW)", "Eolien (MW)", "Solaire (MW)", "Hydraulique (MW)",
          "Pompage (MW)", "Bioénergies (MW)", "Ech. physiques (MW)", "TCO Thermique (%)",
          "TCH Thermique (%)", "Eolien terrestre (MW)", "Eolien offshore (MW)"]


def generate_sample_csv(dest: str | Path, seeds_file: str | Path | None = None,
                        start="2021-01-01", end="2023-12-31") -> Path:
    seed = 42
    if seeds_file and Path(seeds_file).exists():
        seed = json.loads(Path(seeds_file).read_text()).get("sample_seed", 42)
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, end + " 23:30", freq="30min", tz="Europe/Paris")
    doy = idx.dayofyear.values
    hour = idx.hour.values + idx.minute.values / 60
    t = (idx.year.values - 2021) + doy / 365.0  # years since start
    winter = np.cos(2 * np.pi * (doy - 15) / 365)  # +1 mid-January
    summer = -winter
    day_curve = np.clip(np.sin(np.pi * (hour - 6) / 14), 0, None)

    frames = []
    for code, prof in PROFILE.items():
        base, nuc, thm, hyd, wnd, sol, bio = prof
        name = REGIONS[code][0]
        conso = base * (1 + 0.25 * winter + 0.1 * np.sin(np.pi * (hour - 7) / 12) ** 2) * rng.normal(1, 0.02, len(idx))
        production = {
            "Nucléaire (MW)": base * nuc * (1 + 0.05 * winter) * rng.normal(1, 0.01, len(idx)),
            "Eolien (MW)": base * wnd * (1 + 0.12 * t) * np.clip(1 + 0.35 * winter + rng.normal(0, 0.45, len(idx)), 0.02, None),
            "Solaire (MW)": base * sol * (1 + 0.25 * t) * (1 + 0.8 * summer) * day_curve * 3.2,
            "Hydraulique (MW)": base * hyd * (1 + 0.2 * np.sin(2 * np.pi * (doy - 120) / 365)) * rng.normal(1, 0.03, len(idx)),
            "Bioénergies (MW)": base * bio * rng.normal(1, 0.02, len(idx)),
        }
        renew_nuc = sum(production.values())
        thermal = np.clip(conso - renew_nuc, 0, None) * 0.35 + base * thm * 0.5
        df = pd.DataFrame({
            "Code INSEE région": code, "Région": name,
            "Date - Heure": idx.strftime("%Y-%m-%dT%H:%M:%S%z").str.replace(r"(\d\d)(\d\d)$", r"\1:\2", regex=True),
            "Date": idx.strftime("%Y-%m-%d"), "Heure": idx.strftime("%H:%M"),
            "Consommation (MW)": conso.round(0), "Thermique (MW)": thermal.round(0),
            "Pompage (MW)": -np.where(hyd > 0.2, base * 0.02, 0).round(0) * np.ones(len(idx)),
            "Ech. physiques (MW)": (renew_nuc + thermal - conso).round(0),
            "TCO Thermique (%)": 5.0, "TCH Thermique (%)": 20.0,
            "Eolien terrestre (MW)": production["Eolien (MW)"].round(0), "Eolien offshore (MW)": 0,
        })
        for k, v in production.items():
            df[k] = v.round(0)
        # realistic blemishes: regions without a source report blanks; a few random gaps
        for k in ("Nucléaire (MW)", "Hydraulique (MW)"):
            if production[k].mean() < 1e-6 + base * 0.0005:
                df[k] = np.nan
        gaps = rng.random(len(df)) < 0.002
        df.loc[gaps, ["Consommation (MW)", "Solaire (MW)"]] = np.nan
        frames.append(df[HEADER])

    out = pd.concat(frames, ignore_index=True)
    out = pd.concat([out, out.sample(40, random_state=seed)], ignore_index=True)  # duplicated rows
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest, sep=";", index=False, encoding="utf-8")
    return dest
