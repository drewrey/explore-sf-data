"""Build site-ready park-score JSONs from the Annual Park Evaluation Scores.

Outputs to data/processed/:
  park_scores_points.json       one row per park x fiscal year x district
  park_scores_by_district.json  district-level mean per fiscal year, with the
                                supervisor(s) who served that district that FY

Multi-district parks (supervisor_district like "1, 2") count toward every
district listed. District assignments in the source reflect current
(post-2022) boundaries for all years. FY2021 is absent (COVID). SF fiscal
years run July 1 - June 30, so FY n is Jul 1 n-1 through Jun 30 n.

Run:  uv run scripts/process_park_scores.py [--refresh]
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from sfdata import fetch


def explode_districts(scores: pd.DataFrame) -> pd.DataFrame:
    out = scores.copy()
    out["district"] = out["supervisor_district"].astype(str).str.split(",")
    out = out.explode("district")
    out["district"] = out["district"].str.strip().astype(int)
    return out


def supervisors_for_fy(tenures: pd.DataFrame, district: int, fy: int) -> str:
    """Names of everyone who held the district seat during fiscal year `fy`."""
    fy_start = pd.Timestamp(fy - 1, 7, 1)
    fy_end = pd.Timestamp(fy, 6, 30)
    t = tenures[tenures["district"] == district]
    held = t[(t["start_date"] <= fy_end) & (t["end_date"] >= fy_start)]
    return " / ".join(held["supervisor"])


def main() -> None:
    refresh = "--refresh" in sys.argv
    scores = explode_districts(fetch.load("park_scores", refresh=refresh))

    tenures = fetch.load_reference("supervisors")
    tenures["start_date"] = pd.to_datetime(tenures["start_date"])
    tenures["end_date"] = pd.to_datetime(tenures["end_date"]).fillna(pd.Timestamp.max)

    points = scores.rename(columns={"park_score": "score"})[
        ["fy", "district", "park", "park_type", "score"]
    ].sort_values(["fy", "district", "park"])

    by_district = (
        scores.groupby(["fy", "district"])["park_score"]
        .agg(mean_score="mean", n_parks="size")
        .round({"mean_score": 4})
        .reset_index()
    )
    by_district["supervisors"] = [
        supervisors_for_fy(tenures, d, fy)
        for fy, d in zip(by_district["fy"], by_district["district"])
    ]

    for name, df in [
        ("park_scores_points", points),
        ("park_scores_by_district", by_district),
    ]:
        dest = fetch.PROCESSED_DIR / f"{name}.json"
        df.to_json(dest, orient="records")
        print(f"{name}: {len(df)} rows -> {dest.relative_to(fetch.REPO_ROOT)}")


if __name__ == "__main__":
    main()
