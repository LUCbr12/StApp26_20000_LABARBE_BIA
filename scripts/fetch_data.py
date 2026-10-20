"""Download the éCO2mix regional CSV once, aggregate it to daily data, write data/*.csv.gz|json.

    python scripts/fetch_data.py            # real data (needs internet, ~1 download)
    python scripts/fetch_data.py --force    # re-download and rebuild
    python scripts/fetch_data.py --sample   # synthetic offline test data (NOT real)
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

parser = argparse.ArgumentParser()
parser.add_argument("--force", action="store_true", help="re-download and rebuild")
parser.add_argument("--sample", action="store_true", help="build synthetic test data instead")
args = parser.parse_args()
if args.sample:
    os.environ["ECO2MIX_SAMPLE"] = "1"

from utils import io  # noqa: E402

io.fetch_and_cache(force=args.force)
print("Done. Start the app with: streamlit run app.py")
