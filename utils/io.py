"""Data access: download (cached), aggregate once, load fast.

Flow:  raw half-hourly CSV (not committed)  ->  data/eco2mix_daily.csv.gz + quality.json
The two small processed files ARE meant to be committed / zipped so the deployed app
starts instantly and never has to download ~1M rows.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_PATH = DATA_DIR / "raw" / "eco2mix_regional_cons_def.csv"
DAILY_PATH = DATA_DIR / "eco2mix_daily.csv.gz"
QUALITY_PATH = DATA_DIR / "quality.json"
SAMPLE_DAILY = DATA_DIR / "sample" / "eco2mix_daily_SAMPLE.csv.gz"
SAMPLE_QUALITY = DATA_DIR / "sample" / "quality_SAMPLE.json"
SEEDS = ROOT / "seeds.json"

DATASET_TITLE = "Données éCO2mix régionales consolidées et définitives"
DATASET_PAGE = "https://www.data.gouv.fr/datasets/donnees-eco2mix-regionales-consolidees-et-definitives"
PUBLISHER = "RTE via Open Data Réseaux Énergies (ODRE)"
LICENSE = "Licence Ouverte / Open Licence 2.0 (Etalab)"
# Stable data.gouv.fr resource permalink (CSV), then ODRE export as fallback.
DATA_URLS = [
    "https://www.data.gouv.fr/api/1/datasets/r/4c308634-d76e-40b0-a777-ab99a8871564",
    "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-regional-cons-def/exports/csv?delimiter=%3B",
]


def use_sample() -> bool:
    return os.environ.get("ECO2MIX_SAMPLE", "") == "1"


def download_raw(dest: Path = RAW_PATH, force: bool = False, log=print) -> Path:
    """Download the raw CSV once (streamed, resumable by re-running)."""
    import requests

    if dest.exists() and dest.stat().st_size > 0 and not force:
        log(f"Raw file already cached: {dest}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for url in DATA_URLS:
        try:
            log(f"Downloading {url}")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(".part")
                done = 0
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
                        done += len(chunk)
                        if done % (50 << 20) < (1 << 20):
                            log(f"  {done / 1e6:,.0f} MB")
                tmp.replace(dest)
            log(f"Saved {dest} ({dest.stat().st_size / 1e6:,.0f} MB)")
            return dest
        except Exception as exc:  # try next URL
            last_err = exc
            log(f"  failed: {exc}")
    raise RuntimeError(f"Could not download the dataset from any URL. Last error: {last_err}")


def build_processed(raw: Path, daily_path: Path, quality_path: Path, log=print) -> None:
    from utils.prep import aggregate_raw_csv

    log("Aggregating half-hourly data to daily (streaming)…")
    daily, quality = aggregate_raw_csv(raw, progress=lambda n: log(f"  {n:,} rows read"))
    daily_path.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(daily_path, index=False, compression="gzip")
    quality["date_min"] = str(daily["date"].min().date())
    quality["date_max"] = str(daily["date"].max().date())
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2))
    log(f"Wrote {daily_path} ({len(daily):,} region-days) and {quality_path}")


def fetch_and_cache(force: bool = False, log=print) -> None:
    """Make sure the processed files exist (download + aggregate if needed)."""
    if use_sample():
        if SAMPLE_DAILY.exists() and not force:
            return
        from utils.sample import generate_sample_csv

        raw = generate_sample_csv(DATA_DIR / "sample" / "raw_sample.csv", SEEDS)
        build_processed(raw, SAMPLE_DAILY, SAMPLE_QUALITY, log)
        raw.unlink(missing_ok=True)
        return
    if DAILY_PATH.exists() and QUALITY_PATH.exists() and not force:
        return
    raw = download_raw(force=force, log=log)
    build_processed(raw, DAILY_PATH, QUALITY_PATH, log)


def load_data() -> tuple[pd.DataFrame, dict, bool]:
    """Return (daily_df, quality_dict, is_sample)."""
    fetch_and_cache()
    sample = use_sample()
    daily = pd.read_csv(SAMPLE_DAILY if sample else DAILY_PATH, dtype={"region_code": str},
                        parse_dates=["date"])
    quality = json.loads((SAMPLE_QUALITY if sample else QUALITY_PATH).read_text())
    daily["date"] = pd.to_datetime(daily["date"])
    return daily, quality, sample
