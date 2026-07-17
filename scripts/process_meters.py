"""Join the SFMTA meter inventory with current meter policies into map data.

Output: data/processed/meters.geojson — one point per ACTIVE meter with
per-meter policy facets derived from the ~880k-row schedule table. This file
is LARGE and gitignored (see README "Data policy"); rerun this script to
regenerate it.

Per-meter properties (terse keys to keep the file small):
  p  post id                      c  cap color
  n  street address              d  compact weekly schedule string
  t  weekday-noon status: P paid / F free (incl. not operated) / T tow / X no policy data
  r  hourly rate at Wed noon ($, present when t == "P")
  l  time limit (minutes) at Wed noon, else max across OP windows
  e  1 if enforced past 6pm any weekday      s  1 if operated on Sunday

Caveat baked into "t": ~25% of active meters (multi-space pay stations and
most motorcycle meters) have no rows in the policies dataset -> t = "X".

Run:  uv run scripts/process_meters.py [--refresh]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import pandas as pd

from sfdata import fetch

NOON = 12 * 60
SIX_PM = 18 * 60
DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


def minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def fmt_time(m: int) -> str:
    return f"{m // 60}:{m % 60:02d}"


def day_summary(windows: list[dict]) -> str:
    """One day's schedule as e.g. '9:00-18:00 $5.75 2h' (free otherwise)."""
    ops = sorted((w for w in windows if w["type"] == "OP"), key=lambda w: w["start"])
    if not ops:
        return "free"
    rates = sorted({w["rate"] for w in ops if w["rate"] is not None})
    rate = (
        f"${rates[0]:g}" if len(rates) == 1
        else f"${rates[0]:g}-{rates[-1]:g}" if rates else ""
    )
    limits = {w["limit"] for w in ops if w["limit"]}
    limit = f" {max(limits) / 60:g}h" if limits else ""
    return f"{fmt_time(ops[0]['start'])}-{fmt_time(ops[-1]['end'])} {rate}{limit}"


def weekly_summary(by_day: dict[str, list[dict]]) -> str:
    """Collapse identical consecutive days: 'Mo-Fr 9:00-18:00 $5.75 2h; Sa ...; Su free'."""
    parts: list[tuple[list[str], str]] = []
    for day in DAYS:
        desc = day_summary(by_day.get(day, []))
        if parts and parts[-1][1] == desc:
            parts[-1][0].append(day)
        else:
            parts.append(([day], desc))
    return "; ".join(
        f"{ds[0]}-{ds[-1]} {desc}" if len(ds) > 1 else f"{ds[0]} {desc}"
        for ds, desc in parts
    )


def facets(by_day: dict[str, list[dict]]) -> dict:
    noon = next(
        (w for w in by_day.get("We", []) if w["start"] <= NOON < w["end"]), None
    )
    if noon is None or noon["type"] in ("FREE", "PRE"):
        status, rate = "F", None
    elif noon["type"] == "OP":
        status, rate = "P", noon["rate"]
    else:
        status, rate = "T", None  # TOW/ALT at noon

    all_ops = [w for ws in by_day.values() for w in ws if w["type"] == "OP"]
    limit = (noon or {}).get("limit") or max(
        (w["limit"] for w in all_ops if w["limit"]), default=None
    )
    weekday_ops = [w for d in DAYS[:5] for w in by_day.get(d, []) if w["type"] == "OP"]
    return {
        "t": status,
        "r": rate,
        "l": limit,
        "e": int(any(w["end"] > SIX_PM for w in weekday_ops)),
        "s": int(any(w["type"] == "OP" for w in by_day.get("Su", []))),
        "d": weekly_summary(by_day),
    }


def main() -> None:
    refresh = "--refresh" in sys.argv

    meters = fetch.load("parking_meters", refresh=refresh)
    meters = meters[meters["active_meter_flag"] == "M"].copy()
    print(f"active meters: {len(meters)}")

    policies = fetch.load("meter_policies", refresh=refresh)
    print(f"policy rows: {len(policies)}")

    by_meter: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in policies.itertuples(index=False):
        by_meter[row.postid][row.dayofweek].append(
            {
                "start": minutes(row.starttime),
                "end": minutes(row.endtime),
                "type": row.scheduletype,
                "rate": None if pd.isna(row.hourlyrate) else float(row.hourlyrate),
                "limit": None if pd.isna(row.timelimitminutes) else int(row.timelimitminutes),
            }
        )

    features = []
    for m in meters.itertuples(index=False):
        post = m.post_id
        props = {
            "p": post,
            "n": f"{m.street_num} {m.street_name}".strip(),
            "c": None if m.cap_color in ("-", None) else m.cap_color,
        }
        if post in by_meter:
            props.update(facets(by_meter[post]))
        else:
            props.update({"t": "X", "r": None, "l": None, "e": 0, "s": 0, "d": None})
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(float(m.longitude), 5), round(float(m.latitude), 5)],
                },
                "properties": props,
            }
        )

    dest = fetch.PROCESSED_DIR / "meters.geojson"
    with open(dest, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))

    df = pd.DataFrame([f["properties"] for f in features])
    print(f"\nwrote {len(features)} features -> {dest.relative_to(fetch.REPO_ROOT)}")
    print(f"size: {dest.stat().st_size / 1e6:.1f} MB")
    print("\nnoon status:\n", df["t"].value_counts().to_string())
    print("\nnoon rate ($/hr):\n", df["r"].describe().round(2).to_string())
    print("\nevening enforcement:", df["e"].sum(), "| sunday operation:", df["s"].sum())


if __name__ == "__main__":
    main()
