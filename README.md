# explore-sf-data

Exploring San Francisco open data from [DataSF](https://data.sf.gov/), with a focus on
transit/bicycling, the arts, housing, and effective government. The end product is an
interactive website of maps and visualizations built from reproducible data pipelines.

## Architecture

Analysis and presentation are decoupled by a simple contract: **the site only ever reads
small processed files from `data/processed/`**.

```
DataSF (Socrata SODA API)
        │  scripts/ + src/sfdata/fetch.py  (registry-driven, cached)
        ▼
data/raw/          as-downloaded, gitignored, always refetchable
        │  notebooks + processing scripts (GeoPandas, DuckDB)
        ▼
data/processed/    derived GeoJSON/JSON the site reads
        │
        ▼
site/              static site (MapLibre GL + Vega-Lite), no build step
```

### Data policy

- **`data/raw/` is never committed.** Every raw file is refetchable by script from
  the IDs in `datasets.yaml`.
- **Small processed outputs (roughly < 1 MB) are committed**, so a fresh clone can
  browse the site and notebooks without hitting DataSF.
- **Large processed outputs are gitignored** — each one is listed in `.gitignore`
  with the script that regenerates it (e.g. `data/processed/meters.geojson` ←
  `uv run scripts/process_meters.py`). Pages that depend on one of these say so
  when the file is missing.
- **Refreshes are guarded.** DataSF occasionally publishes a partial extract (Meter
  Policies dropped from ~880k rows to 5,687 on 2026-10-30). If a `--refresh` download
  has under half the cached row count, the cached copy is kept and a warning printed;
  `SFDATA_ALLOW_SHRINK=1` overrides. Each replaced raw file is kept one-deep in
  `data/raw/prev/`.
- Consequence for publishing: a deploy (e.g. GitHub Pages) must run the
  regeneration scripts as a build step, since the large files aren't in the repo.

## Layout

| Path | Purpose |
|---|---|
| `datasets.yaml` | Registry of every DataSF dataset we use: ID, format, provenance notes |
| `src/sfdata/` | Shared Python: SODA fetch/cache layer, geo helpers |
| `scripts/` | Pipeline entry points (e.g. `fetch_boundaries.py`) |
| `data/raw/` | Raw downloads (gitignored) |
| `data/reference/` | Hand-curated reference data (committed), e.g. supervisor tenures by district since 2001, sourced from Wikipedia's Board of Supervisors timeline with corrections verified against news reports |
| `data/processed/` | Derived outputs the site and notebooks consume (committed) |
| `notebooks/` | Jupyter notebooks for exploration |
| `reports/` | Short dated write-ups of findings and data maintenance |
| `site/` | The publishable static site |

## Quickstart

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                                 # create venv, install deps
uv run scripts/fetch_boundaries.py      # pull boundary data, write processed GeoJSON
uv run scripts/process_park_scores.py   # park evaluation scores by district
uv run scripts/process_resale.py        # dumped furniture, used-goods shops, vendors
uv run scripts/process_dumped_reports.py  # report explorer data (~3.5 MB, gitignored output)
uv run scripts/process_meters.py        # parking meters + policies map data (~5 min:
                                        #   downloads ~880k policy rows, gitignored output)
# If DataSF publishes a broken extract (the refresh guard will warn), restore the
# last good full export from the Internet Archive, then rerun the processing script:
uv run scripts/restore_from_wayback.py meter_policies 20260413184235
uv run jupyter lab                      # explore in notebooks/
python3 -m http.server 8000             # from repo root, then open
                                        # http://localhost:8000/site/
```

An optional Socrata app token raises API rate limits: set `SODA_APP_TOKEN` in your
environment (free at https://data.sf.gov/profile/edit/developer_settings).

## Adding a dataset

1. Find it on data.sf.gov (formerly data.sfgov.org) and note the 9-character dataset ID (in the URL).
2. Add an entry to `datasets.yaml`.
3. `from sfdata import fetch; df = fetch.load("your_name")` — cached under `data/raw/`.

## Real-time data (for published projects)

Two patterns, neither requiring a server:

1. **Client-side fetch** when the source allows it — Socrata's API supports CORS, and
   Bay Wheels' GBFS feed is public JSON, so the browser can hit them directly.
2. **Scheduled refresh** when a source needs an API key (e.g. 511.org for Muni vehicle
   positions) — a GitHub Actions cron job runs a fetch script and deploys a small JSON
   snapshot that the site reads, keeping the static-site contract intact.

## Notes

- Spatial work uses GeoPandas; DuckDB (with spatial extension) is available for SQL over
  larger tables. PostGIS is the documented escape hatch if we ever need heavy repeated
  geometry work — the processed-data contract wouldn't change.
- Supervisor districts were redistricted in 2022; `cqbw-m5m3` is the *current* boundaries
  dataset, `keex-zmn4` has the 2012–2022 ones if we ever compare across eras.
