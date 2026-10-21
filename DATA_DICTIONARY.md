# Data Dictionary — files in `Outputs/`

All four files were generated from the author's analysis workbook (version 11.8.8; not included in this
repository) and the catalog in `Outputs/eclipse_catalog_full_-13198_17189_detailed.csv`.

## `eclipse_catalog_full_-13198_17189_detailed.csv` — the full catalog (145,356 eclipses)

Engine output columns: Date (`-13198 Jun 06` style, astronomical years), TD of GE, DeltaT_s, Kind (Solar/Lunar),
TypeCode (solar P/A/T/H; lunar N/P/T), Type, Gamma, Magnitude, UmbralMag and PenumbralMag (lunar only), plus
**Forward Saros Count** and **Reverse Saros Count** (position within the Saros series; a leading `~` marks an
estimate for series cut off by the catalog edge — 6,315 values).

## Conventions used in every file

* **Date** — NASA *Five Millennium Catalog* format: signed year padded to four digits, three-letter month,
  two-digit day, e.g. `-13192 Aug 28`, `0032 Sep 23`, `2291 May 14`. Years are numbered astronomically and include
  year 0: year 0 = 1 BCE, −1 = 2 BCE, so −13192 = 13193 BCE. Julian calendar before 1582 Oct 15, Gregorian after.
* **TD of GE** — Terrestrial (Dynamical) Time of greatest eclipse, `HH:MM:SS`. Dates are TD dates.
* **Cum. Seconds from -15000 Jan 01 00:00:00 TD** — whole TD seconds since −15000 Jan 1 00:00 (counted on the same
  Julian/Gregorian calendar). This is the time axis for every interval. Subtract two values for the exact interval.
* **Delta T (s)** — TD − UT, Espenak & Meeus (2006) with NASA's lunar secular-acceleration correction. A model value;
  it is not used in any pattern calculation.
* **Gamma** — closest distance of the shadow axis from Earth's centre (solar) or of the Moon's centre from the centre
  of Earth's shadow (lunar), in Earth radii; sign = north (+) / south (−) of the J2000 equator.
* **Magnitude** — solar: eclipse magnitude; lunar: umbral magnitude for total/partial, penumbral magnitude for penumbral.
* **Solar Saros # / Lunar Saros #** — Saros series number; blank when not applicable (solar eclipses have no lunar
  number and vice versa). From −3999 to +4000 the numbers are Matt Slavik's, matched to NASA's Saros numbering wherever
  verifiable; outside that range they are extended by the standard numbering rule (see `pipeline/apply_saros.py`).
* **Forward / Reverse Saros Count** — position within the Saros series counted from the first member (Forward = 1) or
  from the last member (Reverse = 1). A leading `~` marks an **estimate**: the series is cut off by the catalog edge,
  so the members beyond the edge were estimated by extending the series' gamma trend.
* **Direction** — `A` = near the start of its Saros series; `B` = near the end. When applying the shared intervals,
  **Direction B: target = start + interval; Direction A: target = start − interval.**
* Blank = not applicable.

## `694-1,019 Stride Calculation.csv` — all 145,356 eclipses

| Column | Meaning |
|---|---|
| Date, TD of GE, Cum. Seconds…, Delta T (s), Solar or Lunar, Type, Gamma, Magnitude, Solar Saros #, Lunar Saros # | As above |
| Off-Stride Direction | `A` or `B` for the 5,124 off-stride eclipses (on no lane); blank for the 140,232 on-stride eclipses |
| Forward Stride 1–6 | The six forward lanes. `Start` = the lane's first eclipse; a number = the step, in whole days (rounded from cumulative seconds), by which the lane reached this eclipse from its previous eclipse (693/694/695 for a 694-day stride; 1018/1019 for a 1,019-day stride); blank = not on this lane |
| Backward Stride 1–6 | The six backward lanes, same coding (walked backward in time, so the step is measured to the next-later lane eclipse) |

Rule: step 694 days; if no eclipse lies within ±2.5 days (216,000 s), step 1,019 days. Forward lanes are seeded from
every eclipse in the first 694 days of the catalog, backward lanes from every eclipse in the last 694 days.

## `Off-Stride Eclipses.csv` — the 5,124 off-stride eclipses

Columns: Date, TD of GE, Cum. Seconds…, Delta T (s), Solar or Lunar, Type, Gamma, Magnitude, Solar Saros #,
Lunar Saros #, Forward Saros Count, Reverse Saros Count, Direction (all as above). 264 rows carry a `~` estimate.

## `Off-Stride Shared Intervals.csv` — the 16,377 shared intervals

| Column | Meaning |
|---|---|
| Average (Seconds) | Mean of the interval's measured values (signed; negative = into the past) |
| Max (Seconds) / Min (Seconds) | The measured values with the largest and smallest magnitude |
| Standard Deviation (Seconds) | Sample standard deviation of the measured values |
| Average (Days) | Average ÷ 86,400, rounded to 0.01 |
| Average (Years) | Average ÷ 31,556,925 s (365.2422 days), rounded to 0.01 |

Each interval is a narrow band: all of its measured values fit within one window of 2 × 246,896 s (±2.86 days).
Test range: targets between cumulative seconds 56,881,000,000 and 1,015,815,000,000.

## `All Eclipses and Near-Miss Eclipses Matching All Off-Stride Shared Intervals.csv` — 10,964 points

Same columns as `Off-Stride Eclipses.csv`, plus:

| Column | Meaning |
|---|---|
| Category | `Off-stride eclipse` (5,124), `Matching on-stride eclipse` (2,854), or `Matching eclipse near-miss` (2,986) |

* Matching = every one of the 16,377 intervals, applied in the point's direction, lands within ±3.5 days
  (302,400 s, measured from the middle of the interval's band) of an eclipse, wherever the target lies inside the
  test range.
* Near-miss rows are new or full moons with no eclipse: the eclipse columns are blank, and the cumulative seconds may
  carry a fraction (the time is derived from the interval set, not from an eclipse). 345 rows carry a `~` estimate.
