"""Restore a registered CSV dataset's raw file from an Internet Archive snapshot.

For when DataSF publishes a broken extract and we have no good local copy.
The Wayback Machine has crawled many DataSF full exports
(api/views/<id>/rows.csv?accessType=DOWNLOAD). This downloads one, renames its
display-name headers (e.g. "PostID") to the API field names our scripts use
("postid"), and installs it as data/raw/<name>.csv. The file it replaces is
kept in data/raw/prev/.

Find snapshot timestamps with the CDX API, e.g.:
  curl "http://web.archive.org/cdx/search/cdx?url=data.sfgov.org/api/views/qq7v-hds4/rows.csv&matchType=prefix&filter=statuscode:200&from=2026"

Run:  uv run scripts/restore_from_wayback.py meter_policies 20260413184235
      (then rerun the dataset's processing script, without --refresh)

Snapshot values are as-exported (e.g. dates as 2026/04/13 rather than the
API's ISO timestamps); processing scripts should parse dates leniently.
"""

from __future__ import annotations

import gzip
import io
import shutil
import sys

import pandas as pd
import requests

from sfdata import fetch

EXPORT_URL = "https://data.sfgov.org/api/views/{id}/rows.csv?accessType=DOWNLOAD"


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    name, timestamp = sys.argv[1], sys.argv[2]
    entry = fetch.registry()[name]
    if entry["format"] != "csv":
        sys.exit(f"{name} is {entry['format']}; only csv datasets are supported")

    url = f"http://web.archive.org/web/{timestamp}id_/" + EXPORT_URL.format(id=entry["id"])
    print(f"downloading {url}")
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    body = r.content
    if body[:2] == b"\x1f\x8b":  # Wayback often serves the stored gzip as-is
        body = gzip.decompress(body)
    df = pd.read_csv(io.BytesIO(body), dtype=str)

    meta = requests.get(
        f"https://{fetch.DOMAIN}/api/views/{entry['id']}.json", timeout=60
    ).json()
    field_names = {c["name"]: c["fieldName"] for c in meta["columns"]}
    df = df.rename(columns=lambda c: field_names.get(c, c.lower()))

    dest = fetch.raw_path(name)
    if dest.exists():
        prev = fetch.RAW_DIR / "prev" / dest.name
        prev.parent.mkdir(exist_ok=True)
        shutil.copy2(dest, prev)
        print(f"previous copy kept at {prev.relative_to(fetch.REPO_ROOT)}")
    df.to_csv(dest, index=False)
    print(f"{name}: {len(df):,} rows from snapshot {timestamp} -> "
          f"{dest.relative_to(fetch.REPO_ROOT)}")


if __name__ == "__main__":
    main()
