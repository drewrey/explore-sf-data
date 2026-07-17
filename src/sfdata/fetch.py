"""Registry-driven fetch/cache layer for DataSF's Socrata (SODA) API.

Every dataset we use is declared in datasets.yaml at the repo root. This module
downloads them to data/raw/ (gitignored) and loads them as (Geo)DataFrames.

    from sfdata import fetch
    districts = fetch.load("supervisor_districts")          # GeoDataFrame
    xwalk = fetch.load("tracts_to_neighborhoods")            # DataFrame
    fresh = fetch.load("supervisor_districts", refresh=True)

An optional Socrata app token (env var SODA_APP_TOKEN) raises rate limits.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
import yaml

DOMAIN = "data.sfgov.org"
REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "datasets.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REFERENCE_DIR = REPO_ROOT / "data" / "reference"

# SODA returns at most this many rows per request; we page until exhausted.
PAGE_SIZE = 50_000


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


def download(name: str, refresh: bool = False) -> Path:
    """Download a registered dataset to data/raw/ (skipped if already cached)."""
    entry = registry()[name]
    dest = raw_path(name)
    if dest.exists() and not refresh:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    fmt = entry["format"]
    url = f"https://{DOMAIN}/resource/{entry['id']}.{fmt}"

    if fmt == "geojson":
        features: list[dict] = []
        offset = 0
        while True:
            r = requests.get(
                url,
                params={"$limit": PAGE_SIZE, "$offset": offset},
                headers=_headers(),
                timeout=120,
            )
            r.raise_for_status()
            page = r.json()["features"]
            features.extend(page)
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        gpd.GeoDataFrame.from_features(features, crs="EPSG:4326").to_file(
            dest, driver="GeoJSON"
        )
    else:
        frames: list[pd.DataFrame] = []
        offset = 0
        while True:
            r = requests.get(
                url,
                params={"$limit": PAGE_SIZE, "$offset": offset},
                headers=_headers(),
                timeout=120,
            )
            r.raise_for_status()
            page = pd.read_csv(io.StringIO(r.text))
            frames.append(page)
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        pd.concat(frames, ignore_index=True).to_csv(dest, index=False)

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
