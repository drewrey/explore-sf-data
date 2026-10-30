"""Registry-driven fetch/cache layer for DataSF's Socrata (SODA) API.

Every dataset we use is declared in datasets.yaml at the repo root. This module
downloads them to data/raw/ (gitignored) and loads them as (Geo)DataFrames.

    from sfdata import fetch
    districts = fetch.load("supervisor_districts")          # GeoDataFrame
    xwalk = fetch.load("tracts_to_neighborhoods")            # DataFrame
    fresh = fetch.load("supervisor_districts", refresh=True)

An optional Socrata app token (env var SODA_APP_TOKEN) raises rate limits.

Refreshes are guarded: if a re-download comes back with far fewer rows than the
cached copy (DataSF publishes partial extracts now and then -- Meter Policies
shrank from ~880k rows to 5,687 on 2026-10-30), the cached copy is kept and a
warning is printed. Set SFDATA_ALLOW_SHRINK=1 to accept the smaller download.
The replaced file is always kept at data/raw/prev/ as a one-deep backup.
"""

from __future__ import annotations

import io
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
import yaml

# data.sfgov.org now 301-redirects here (seen 2026-10-30).
DOMAIN = "data.sf.gov"
REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "datasets.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REFERENCE_DIR = REPO_ROOT / "data" / "reference"

# SODA returns at most this many rows per request; we page until exhausted.
PAGE_SIZE = 50_000

# A refresh that returns fewer than this fraction of the cached row count is
# treated as a broken upstream extract and rejected (see module docstring).
MIN_REFRESH_RATIO = 0.5


def registry() -> dict[str, dict[str, Any]]:
    """All datasets declared in datasets.yaml, keyed by short name."""
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f)["datasets"]


def _headers() -> dict[str, str]:
    token = os.environ.get("SODA_APP_TOKEN")
    return {"X-App-Token": token} if token else {}


def raw_path(name: str) -> Path:
    entry = registry()[name]
    return RAW_DIR / f"{name}.{entry['format']}"


def _query_params(entry: dict[str, Any]) -> dict[str, str]:
    """Optional server-side filters from the registry (for huge datasets like 311).

    A stable $order is required for $offset paging to be reliable in SODA.
    """
    params = {"$order": ":id"}
    if "where" in entry:
        params["$where"] = entry["where"]
    if "select" in entry:
        params["$select"] = entry["select"]
    return params


def _fetch_pages(url: str, params: dict[str, str], parse) -> list:
    pages = []
    offset = 0
    while True:
        r = requests.get(
            url,
            params={**params, "$limit": PAGE_SIZE, "$offset": offset},
            headers=_headers(),
            timeout=120,
        )
        r.raise_for_status()
        page = parse(r)
        pages.append(page)
        if len(page) < PAGE_SIZE:
            return pages
        offset += PAGE_SIZE


def _row_count(path: Path, fmt: str) -> int:
    if fmt == "geojson":
        return len(gpd.read_file(path))
    with open(path) as f:
        return max(sum(1 for _ in f) - 1, 0)


def download(name: str, refresh: bool = False) -> Path:
    """Download a registered dataset to data/raw/ (skipped if already cached)."""
    entry = registry()[name]
    dest = raw_path(name)
    if dest.exists() and not refresh:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    fmt = entry["format"]
    url = f"https://{DOMAIN}/resource/{entry['id']}.{fmt}"
    params = _query_params(entry)
    tmp = dest.with_name(f".{dest.name}.tmp")

    if fmt == "geojson":
        pages = _fetch_pages(url, params, lambda r: r.json()["features"])
        features = [f for page in pages for f in page]
        gpd.GeoDataFrame.from_features(features, crs="EPSG:4326").to_file(
            tmp, driver="GeoJSON"
        )
        new_rows = len(features)
    else:
        pages = _fetch_pages(url, params, lambda r: pd.read_csv(io.StringIO(r.text)))
        df = pd.concat(pages, ignore_index=True)
        df.to_csv(tmp, index=False)
        new_rows = len(df)

    if dest.exists():
        old_rows = _row_count(dest, fmt)
        if (
            old_rows
            and new_rows < MIN_REFRESH_RATIO * old_rows
            and os.environ.get("SFDATA_ALLOW_SHRINK") != "1"
        ):
            tmp.unlink()
            print(
                f"WARNING: {name} ({entry['id']}) refresh returned {new_rows:,} rows, "
                f"down from {old_rows:,} cached. Keeping the cached copy; this is "
                "usually a broken upstream extract. Set SFDATA_ALLOW_SHRINK=1 to "
                "accept it.",
                file=sys.stderr,
            )
            return dest
        prev = RAW_DIR / "prev" / dest.name
        prev.parent.mkdir(exist_ok=True)
        shutil.copy2(dest, prev)

    tmp.replace(dest)
    return dest


def load(name: str, refresh: bool = False) -> pd.DataFrame | gpd.GeoDataFrame:
    """Load a registered dataset, downloading it first if needed."""
    path = download(name, refresh=refresh)
    if registry()[name]["format"] == "geojson":
        return gpd.read_file(path)
    return pd.read_csv(path)


def load_reference(name: str) -> pd.DataFrame:
    """Load a hand-curated CSV from data/reference/ (committed, not from DataSF)."""
    return pd.read_csv(REFERENCE_DIR / f"{name}.csv")


def soql(dataset_id: str, query: str) -> pd.DataFrame:
    """Run a SoQL query against any DataSF dataset and return the result.

    Useful for server-side filtering/aggregation of large tables, e.g.:
        soql("vw6y-z8j6", "SELECT category, count(*) GROUP BY category")
    """
    r = requests.get(
        f"https://{DOMAIN}/resource/{dataset_id}.json",
        params={"$query": query},
        headers=_headers(),
        timeout=120,
    )
    r.raise_for_status()
    return pd.DataFrame(r.json())
