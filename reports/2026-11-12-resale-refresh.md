# Nov 2026 resale refresh

_2026-11-12 · 311 reports through 2026-11-11_

This reruns the [Oct 30 report](2026-10-30-refresh-and-resale.md) on fresh data, with 2,073 more reports.
The findings hold.
October was the first full month since the last report, and it ran 26% above October 2025.

## What changed since Oct 30

| | Oct 30 | Nov 12 |
| --- | ---: | ---: |
| Dumped furniture & mattress reports | 108,352 | 110,425 |
| Oct reports, year over year | (month in progress) | 4,398 vs 3,500 (+26%) |
| Jan–Oct reports, year over year | — | 41,238 vs 37,859 (+9%) |
| Used-goods shops | 291 | 295 |
| Active street vending permits | 152 | 151 |
| Meter Policies rows on DataSF | 5,687 (broken) | 884,881 (fixed) |

- **DataSF fixed Meter Policies.** The meters map now uses the live schedules (as of Nov 10) instead of the
  Apr 13 Internet Archive copy. Coverage is back to its normal 75%.
- **Dumping is still rising, and faster in the fall.** Summer 2026 furniture reports ran 7% above 2025.
  October's 26% jump is mostly furniture: 3,244 reports vs 2,584 a year earlier.
  One month isn't a trend, and the question of 311 app adoption is still open (see next steps).

## Dumped furniture vs. resale

Details and charts: [notebook 03](../notebooks/03-resale-and-dumped-furniture.ipynb).

- **110,425 reports of dumped furniture and mattresses** to 311 since tagging began on Jun 13, 2024.
  Furniture is three-quarters of them.
- **Seasonal and rising.** Reports peak June–September; furniture reports in Jun–Sep 2026 were 7% above 2025.
- **Moving day shows up.** Reports run 17% above an average day from the 28th through the 3rd,
  and 28% above on the 1st. Mondays are the busiest weekday (27% above average).
- **About 5% of items are gone before the crew arrives** ("unable to locate"). It is highest in SoMa (10%) and
  the Financial District, and lowest in the Richmond and Noe Valley (1–2%).
- **295 used-goods shops** after removing name-match false positives.
- **Street vending permits are a small, current-only snapshot:** 151 active permits, of which 13 sell
  second-hand goods.

## Response times and outcomes

Details and charts: [notebook 04](../notebooks/04-dumped-furniture-outcomes.ipynb). Encampment-related reports are excluded.

- **There's a hard 2pm cutoff.** Reports made before 2pm are closed in a median of about an hour or less.
  From 2pm on, the median jumps to 16 hours, and the next morning's shift picks them up.
- **The longer an item sits, the likelier it's gone.** For reports made 6am–2pm, the "gone on arrival" rate
  rises from 4.7% (closed within an hour) to 10% (4–24 hours) to 15% (over a day).
- **App reports are gone less often** (5.5%) than web and phone reports (7%), which use typed addresses.
- Recology still isn't writing status notes (stopped Aug 27), so finer outcome categories only cover earlier cases.

## By neighborhood

The Mission still leads on both sides: 2.4× the dumped-item reports of any other neighborhood, and the most used-goods shops.
Hayes Valley passed Sunset/Parkside, and Outer Richmond passed Castro/Upper Market.

| Neighborhood | Dumped-item reports | Used-goods shops | Gone on arrival |
| --- | ---: | ---: | ---: |
| Mission | 17,406 | 38 | 3.8% |
| Nob Hill | 7,357 | 7 | 5.1% |
| Tenderloin | 6,127 | 6 | 6.8% |
| South of Market | 5,404 | 15 | 10.3% |
| Hayes Valley | 5,180 | 9 | 8.1% |
| Sunset/Parkside | 5,171 | 12 | 2.0% |
| Bayview Hunters Point | 4,912 | 15 | 7.8% |
| Outer Richmond | 4,345 | 14 | 1.2% |
| Castro/Upper Market | 4,341 | 10 | 6.5% |
| Haight Ashbury | 3,848 | 26 | 4.7% |

Counts are volume, not rates: they aren't yet normalized by population.

## Next steps

- [x] Re-run the meters pipeline once DataSF fixes Meter Policies (done; live data since Nov 12)
- [ ] Normalize neighborhood counts by population (ACS by tract → neighborhood crosswalk)
- [ ] Check whether the 2026 rise in reports, and October's jump, is real or reflects more 311 app use
- [ ] Decide whether the month-end chart and map become a site page

## Sources

- [311 Cases](https://data.sf.gov/d/vw6y-z8j6) (`vw6y-z8j6`), filtered to furniture and mattress reports
- [Registered Business Locations](https://data.sf.gov/d/g8m3-pdis) (`g8m3-pdis`)
- [Street Vending Permits](https://data.sf.gov/d/34ws-kyf6) (`34ws-kyf6`)
- [Meter Policies](https://data.sf.gov/d/qq7v-hds4) (`qq7v-hds4`)
