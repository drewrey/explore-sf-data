# Oct 2026 refresh & resale findings

_2026-10-30_

All project data is refreshed, and the site works again after two upstream breakages.
A new notebook compares where San Francisco dumps furniture with where it resells used goods.

## Data refresh

The parking meter map is restored from an Internet Archive copy, and the basemaps work again.
Boundaries and park scores refreshed with no changes since July.

| Problem | Fix |
| --- | --- |
| DataSF's Meter Policies dataset shrank from ~880,000 rows to 5,687 in its Oct 30 update, and our refresh overwrote the good copy | Restored the Apr 13, 2026 Internet Archive copy (877,047 rows) with `scripts/restore_from_wayback.py`; meter coverage is back to its normal 75% |
| Nothing stopped a refresh from replacing good data with a broken download | Refreshes returning under half the cached rows are now rejected (`SFDATA_ALLOW_SHRINK=1` overrides), and each replaced raw file is kept in `data/raw/prev/` |
| CARTO basemap tiles now show "API KEY REQUIRED" | Site switched to OpenFreeMap, notebook 02 to OpenStreetMap; both keyless |
| data.sfgov.org now redirects to data.sf.gov | Code and links moved to data.sf.gov |

The meters page now shows its data dates (meters Oct 24, schedules Apr 13) and explains the gap.
The archive shows DataSF published a similarly broken extract on Mar 29, 2026, so expect this again.

## Dumped furniture vs. resale

Details and charts: [notebook 03](../notebooks/03-resale-and-dumped-furniture.ipynb).
DataSF has nothing on garage sales, yard sales, or flea markets; these are the closest sources.

- **108,352 reports of dumped furniture and mattresses** to 311 since tagging began on Jun 13, 2024.
  Furniture is three-quarters of them.
- **Seasonal and rising.** Reports peak June–September; furniture reports in Jun–Sep 2026 were 7% above 2025.
- **Moving day shows up.** Reports run 17% above an average day from the 28th through the 3rd,
  and 29% above on the 1st. Mondays are the busiest weekday.
- **About 5% of items are gone before the crew arrives** ("unable to locate"). It is highest downtown and
  lowest in the Richmond and Sunset, so it may reflect vague locations as much as people taking things.
- **291 used-goods shops** after removing name-match false positives (car rental, wine bars, contractors).
- **Street vending permits are a small, current-only snapshot:** 152 active permits, of which 13 sell
  second-hand goods. Permit numbers suggest ~150–180 issued a year. Unpermitted vending isn't in the data.

## By neighborhood

The Mission leads on both sides: 2.4× the dumped-item reports of any other neighborhood, and the most used-goods shops.

| Neighborhood | Dumped-item reports | Used-goods shops | Gone on arrival |
| --- | ---: | ---: | ---: |
| Mission | 17,014 | 38 | 3.8% |
| Nob Hill | 7,206 | 6 | 5.1% |
| Tenderloin | 5,957 | 6 | 6.8% |
| South of Market | 5,292 | 15 | 10.4% |
| Sunset/Parkside | 5,096 | 11 | 1.8% |
| Hayes Valley | 5,080 | 9 | 8.1% |
| Bayview Hunters Point | 4,840 | 15 | 7.9% |
| Castro/Upper Market | 4,277 | 10 | 6.5% |
| Outer Richmond | 4,265 | 14 | 1.2% |
| Haight Ashbury | 3,797 | 25 | 4.7% |

Counts are volume, not rates: they aren't yet normalized by population.

## Next steps

- [ ] Re-run `uv run scripts/process_meters.py --refresh` once DataSF fixes Meter Policies
- [ ] Normalize neighborhood counts by population (ACS by tract → neighborhood crosswalk)
- [ ] Check whether the 2026 rise in reports is real or reflects more 311 app use
- [ ] Decide whether the month-end chart and map become a site page

## Sources

- [311 Cases](https://data.sf.gov/d/vw6y-z8j6) (`vw6y-z8j6`), filtered to furniture and mattress reports
- [Registered Business Locations](https://data.sf.gov/d/g8m3-pdis) (`g8m3-pdis`)
- [Street Vending Permits](https://data.sf.gov/d/34ws-kyf6) (`34ws-kyf6`)
- [Meter Policies](https://data.sf.gov/d/qq7v-hds4) (`qq7v-hds4`) and its
  [Internet Archive copy of Apr 13, 2026](http://web.archive.org/web/20260413184235/https://data.sfgov.org/api/views/qq7v-hds4/rows.csv?accessType=DOWNLOAD)
