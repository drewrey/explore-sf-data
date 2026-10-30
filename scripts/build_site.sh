#!/usr/bin/env bash
# Build the deployable site into dist/ from LIVE DataSF data (used by Vercel; see vercel.json).
#
# Every dataset is refetched. On a fresh checkout (as on Vercel) there's no cached copy for
# the refresh guard to fall back on, so a broken upstream extract gets published as-is; the
# pages carry the caveats (e.g. the meters page flags abnormally low schedule coverage).
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_LINK_MODE=copy  # build machines can't hardlink from uv's cache

if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

uv run scripts/fetch_boundaries.py --refresh
uv run scripts/process_park_scores.py --refresh
uv run scripts/process_resale.py --refresh
uv run scripts/process_meters.py --refresh

# Pages fetch ../data/processed/, which resolves to /data/processed/ when they're served
# from the site root.
rm -rf dist
mkdir -p dist/data
cp -R site/. dist/
cp -R data/processed dist/data/processed
echo "built dist/ ($(du -sh dist | cut -f1))"
