"""Build the resale page's data from the dumped-furniture, used-goods and vending datasets.

Output: data/processed/resale.json (small; committed)
  meta          data dates and headline counts
  monthly       furniture / mattress reports per full month
  day_of_month  reports per calendar day relative to the average day (1.0)
  weekday       reports per weekday relative to the average weekday
  neighborhoods per Analysis Neighborhood: reports, gone-on-arrival share,
                used-goods shops, second-hand street vendors
  shops         used-goods businesses (name, address, lon/lat)
  vendors       second-hand street vendors with a location (goods, lon/lat)

Cleaning rules live in src/sfdata/resale.py (mirroring notebook 03).

Run:  uv run scripts/process_resale.py [--refresh]
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from sfdata import fetch, resale

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def main() -> None:
    refresh = "--refresh" in sys.argv
    dumped = resale.dumped_reports(refresh=refresh)
    shops, _ = resale.used_goods_shops(refresh=refresh)
    vendors = resale.street_vendors(refresh=refresh)

    # Full months only: tagging began mid-month, and the latest month is in progress.
    month = dumped["requested"].dt.to_period("M")
    monthly = dumped.groupby([month, "service_details"]).size().unstack(fill_value=0)
    monthly = monthly.iloc[1:-1]

    dom = resale.relative_by_calendar_day(dumped["requested"])
    dow = dumped["requested"].dt.day_name().value_counts()
    dow = dow.reindex(WEEKDAYS) / dow.mean()

    secondhand = vendors[vendors["secondhand"]]
    hoods = pd.DataFrame({
        "reports": dumped["analysis_neighborhood"].value_counts(),
        "gone": dumped["outcome"].eq("unable to locate")
                .groupby(dumped["analysis_neighborhood"]).mean(),
        "shops": shops["neighborhoods_analysis_boundaries"].value_counts(),
        "vendors": secondhand["analysis_neighborhood"].value_counts(),
    })
    hoods[["reports", "shops", "vendors"]] = hoods[["reports", "shops", "vendors"]].fillna(0)

    located = secondhand[secondhand["latitude"].notna()]
    out = {
        "meta": {
            "first_report": dumped["requested"].min().date().isoformat(),
            "reports_as_of": dumped["requested"].max().date().isoformat(),
            "reports": len(dumped),
            "furniture_share": round(float((dumped["service_details"] == "furniture").mean()), 3),
            "gone_share": round(float(dumped["outcome"].eq("unable to locate").mean()), 3),
            "shops": len(shops),
            "vending_permits": len(vendors),
            "secondhand_vendors": len(secondhand),
        },
        "monthly": [
            {"month": str(m), "furniture": int(r["furniture"]), "mattress": int(r["mattress"])}
            for m, r in monthly.iterrows()
        ],
        "day_of_month": [{"day": int(d), "rel": round(float(v), 3)} for d, v in dom.items()],
        "weekday": [{"day": d[:3], "rel": round(float(v), 3)} for d, v in dow.items()],
        "neighborhoods": {
            n: {
                "reports": int(r["reports"]),
                "gone": None if pd.isna(r["gone"]) else round(float(r["gone"]), 3),
                "shops": int(r["shops"]),
                "vendors": int(r["vendors"]),
            }
            for n, r in hoods.iterrows()
        },
        "shops": [
            {"name": r.dba_name if isinstance(r.dba_name, str) else r.ownership_name,
             "address": r.full_business_address if isinstance(r.full_business_address, str) else "",
             "lon": round(r.lon, 5), "lat": round(r.lat, 5)}
            for r in shops.dropna(subset=["lon", "lat"]).itertuples()
        ],
        "vendors": [
            {"goods": r.describewhatyouwillsell.strip(),
             "lon": round(float(r.longitude), 5), "lat": round(float(r.latitude), 5)}
            for r in located.itertuples()
        ],
    }

    dest = fetch.PROCESSED_DIR / "resale.json"
    with open(dest, "w") as f:
        json.dump(out, f, separators=(",", ":"), allow_nan=False)  # NaN is not valid JSON
    print(f"wrote {dest.relative_to(fetch.REPO_ROOT)} ({dest.stat().st_size / 1e3:.0f} KB)")
    print(json.dumps(out["meta"], indent=2))


if __name__ == "__main__":
    main()
