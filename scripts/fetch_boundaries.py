"""Fetch SF boundary datasets and write web-ready GeoJSON to data/processed/.

Run:  uv run scripts/fetch_boundaries.py [--refresh]
"""

from __future__ import annotations

import sys

from sfdata import fetch, geo

BOUNDARIES = [
    "city_boundary",
    "supervisor_districts",
    "analysis_neighborhoods",
    "census_tracts",
]


def main() -> None:
    refresh = "--refresh" in sys.argv

    for name in BOUNDARIES:
        gdf = fetch.load(name, refresh=refresh)
        dest = geo.write_processed(gdf, name)
        print(f"{name}: {len(gdf)} features -> {dest.relative_to(fetch.REPO_ROOT)}")

    # Tract->neighborhood crosswalk is tabular; cache the raw copy only.
    path = fetch.download("tracts_to_neighborhoods", refresh=refresh)
    print(f"tracts_to_neighborhoods: cached at {path.relative_to(fetch.REPO_ROOT)}")


if __name__ == "__main__":
    main()
