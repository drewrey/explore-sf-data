"""Shared geospatial helpers: joins onto SF boundaries, processed-file output."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from sfdata import fetch

# Good default for "simplify for the web" in EPSG:4326 degrees (~10 m).
SIMPLIFY_TOLERANCE = 0.0001


def assign_boundary(
    points: gpd.GeoDataFrame,
    boundary_dataset: str,
    columns: list[str],
) -> gpd.GeoDataFrame:
    """Tag each point with the boundary polygon it falls in.

    Example: assign_boundary(stations, "supervisor_districts", ["sup_dist"])
    """
    boundaries = fetch.load(boundary_dataset)[columns + ["geometry"]]
    return gpd.sjoin(
        points.to_crs(boundaries.crs), boundaries, how="left", predicate="within"
    ).drop(columns="index_right")


def write_processed(
    gdf: gpd.GeoDataFrame,
    name: str,
    simplify: float | None = SIMPLIFY_TOLERANCE,
) -> Path:
    """Write a GeoDataFrame to data/processed/<name>.geojson for the site.

    Reprojects to EPSG:4326 and (by default) simplifies geometry to keep
    the files small enough to commit and serve.
    """
    out = gdf.to_crs("EPSG:4326")
    if simplify:
        out = out.copy()
        out.geometry = out.geometry.simplify(simplify, preserve_topology=True)
    dest = fetch.PROCESSED_DIR / f"{name}.geojson"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_file(dest, driver="GeoJSON")
    return dest
