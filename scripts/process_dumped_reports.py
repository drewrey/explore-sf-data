"""Build the report explorer's data: every dumped-furniture/mattress 311 report, compactly.

Output: data/processed/dumped_reports.json (~4 MB; LARGE, gitignored, rebuilt by
scripts/build_site.sh). Columnar, one array per field, all small integers so the
browser can filter ~100k rows in milliseconds:

  d  days since meta.start (report date)      h  hour reported (0-23)
  t  type: 0 furniture, 1 mattress            o  outcome index into meta.outcomes
  r  time-to-close bucket index into meta.response (-1 = open / unknown)
  c  hours to close x 10, rounded (-1 = open / unknown)
  s  source index into meta.sources           n  neighborhood index into meta.neighborhoods (-1 = none)
  x, y  position: (lon + 122.6) x 1e5 and (lat - 37.6) x 1e5, rounded (-1 = none)

Outcome categories, the encampment flag and NOTES_STOPPED come from src/sfdata/resale.py.

Run:  uv run scripts/process_dumped_reports.py [--refresh]
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from sfdata import fetch, resale

SOURCES = {"Mobile": 0, "Web": 1, "Phone": 2}  # everything else -> 3 ("Other")


def main() -> None:
    df = resale.dumped_reports(refresh="--refresh" in sys.argv)
    df = df.sort_values("requested").reset_index(drop=True)

    start = df["requested"].min().normalize()
    hoods = sorted(df["analysis_neighborhood"].dropna().unique())
    hood_idx = {n: i for i, n in enumerate(hoods)}
    outcome_idx = {n: i for i, n in enumerate(resale.OUTCOME_NAMES)}
    response_idx = {n: i for i, n in enumerate(resale.RESPONSE_LABELS)}

    lon = pd.to_numeric(df["long"], errors="coerce")
    lat = pd.to_numeric(df["lat"], errors="coerce")
    located = lon.between(-122.6, -122.3) & lat.between(37.6, 37.85)

    cols = {
        "d": (df["requested"].dt.normalize() - start).dt.days,
        "h": df["requested"].dt.hour,
        "t": (df["service_details"] == "mattress").astype(int),
        "o": df["outcome_cat"].map(outcome_idx),
        "r": df["response"].astype(object).map(response_idx).fillna(-1),
        "c": (df["hours_to_close"] * 10).round().fillna(-1),
        "s": df["source"].map(SOURCES).fillna(3),
        "n": df["analysis_neighborhood"].map(hood_idx).fillna(-1),
        "x": ((lon + 122.6) * 1e5).round().where(located, -1),
        "y": ((lat - 37.6) * 1e5).round().where(located, -1),
    }
    out = {
        "meta": {
            "start": start.date().isoformat(),
            "as_of": df["requested"].max().date().isoformat(),
            "notes_stopped": resale.NOTES_STOPPED.date().isoformat(),
            "outcomes": resale.OUTCOME_NAMES,
            "response": resale.RESPONSE_LABELS,
            "sources": ["App", "Web", "Phone", "Other"],
            "neighborhoods": hoods,
        },
        **{k: v.astype(np.int64).tolist() for k, v in cols.items()},
    }

    dest = fetch.PROCESSED_DIR / "dumped_reports.json"
    with open(dest, "w") as f:
        json.dump(out, f, separators=(",", ":"), allow_nan=False)
    print(f"wrote {len(df):,} reports -> {dest.relative_to(fetch.REPO_ROOT)} "
          f"({dest.stat().st_size / 1e6:.1f} MB); {(~located).sum()} without a usable location")


if __name__ == "__main__":
    main()
