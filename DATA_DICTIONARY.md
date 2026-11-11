# Data Dictionary — files in `Outputs/`

The pattern files were generated from the author's analysis workbook (version 11.8.9; not included in this
repository) and the catalog in `Outputs/eclipse_catalog_full_-13198_17189_detailed.csv`.

## `eclipse_catalog_full_-13198_17189_detailed.csv` — the full catalog (145,356 eclipses)

Engine output columns: Date (`-13198 Jun 06` style, astronomical years), TD of GE, Cum. Seconds from -15000 Jan 01
00:00:00 TD (the time axis of every file; added by `Pipeline/add_geometry.py`), DeltaT_s, Kind (Solar/Lunar),
TypeCode (solar P/A/T/H; lunar N/P/T), Type, Gamma, Magnitude, UmbralMag and PenumbralMag (lunar only), plus
**Forward Saros Count** and **Reverse Saros Count** (position within the Saros series; a leading `~` marks an
estimate for series cut off by the catalog edge — 6,315 values).

Geometry columns, added by `Pipeline/add_geometry.py` from DE441 at the instant of greatest eclipse (no catalog
values are used as input; positions are geometric, centre to centre):

| Column | Meaning |
|---|---|
| Sun-Node Distance (deg) | Sun's ecliptic longitude minus the longitude of the Moon's node, −90..+90 (catalog range −17.47 to +17.51). Negative = the Sun has not yet reached the node (opening side of the eclipse window); positive = past it (closing side). Uses the Moon's osculating node on the ecliptic of date |
| Moon Horizontal Parallax (') | asin(6378.1366 km ÷ Earth–Moon distance), in arcminutes (53.93 to 61.51); larger = Moon nearer |
| Earth-Moon Distance (km) | Geocentric distance of the Moon (356,502 to 406,554 km) |
| Earth-Sun Distance (AU) | Distance from Earth to the Sun, 1 AU = 149,597,870.7 km (0.98026 to 1.01974) |
| Moon Mean Anomaly (deg) | The Moon's mean position in its distance cycle, 0–360: 0 = mean perigee, 180 = mean apogee; advances uniformly through each anomalistic month (27.5545 days) |
| Earth Mean Anomaly (deg) | Earth's mean position in its orbit measured from perihelion, 0–360: 0 = mean perihelion, 180 = mean aphelion (Earth–Moon barycentre orbit; anomalistic year 365.2597 days) |
| Sun True Anomaly (deg, 0-360 from perihelion) | The Sun's **precise** position in Earth's orbit: the actual angle, seen from the Sun, from perihelion to the Earth–Moon barycentre, 0–360 (0 = perihelion, 180 = aphelion). Osculating heliocentric orbit of the barycentre (GM = Sun + Earth + Moon); identical to JPL Horizons' TA for target 3, centre 500@10 |
| Moon True Anomaly (deg, 0-360 from perigee) | The Moon's **precise** position in its orbit: the actual angle, seen from Earth's centre, from perigee to the Moon, 0–360 (0 = perigee, 180 = apogee). Osculating geocentric orbit (GM = Earth + Moon); identical to JPL Horizons' TA for target 301, centre 500@399 |

**Mean vs true anomaly.** A mean anomaly is where the body would be if it moved at a constant rate. The true anomaly is
where it actually is. The difference is the equation of centre: up to ±2.4° for the Sun and ±17° for the Moon in
this catalog. The Sun's true anomaly uses the Earth–Moon barycentre because Earth's monthly wobble around it would
shift the osculating perihelion by up to about 3°. The Sun's direction seen from the two points differs by less than
0.002°. The Sun pulls the Moon's osculating perigee back and forth (by up to about 35° within a month), so the Moon's
true anomaly is measured from the instantaneous perigee.

The mean anomalies come from DE441 itself: every perigee of the Moon (402,839) and every perihelion of the Earth–Moon
barycentre (30,389) in the ephemeris is located, and a smooth curve is fitted through them, which averages out the
perturbations that move individual passages. They agree with Meeus (*Astronomical Algorithms*) to 0.01° between
−1000 and +5000.

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
  verifiable; outside that range they are extended by the standard numbering rule (see `Pipeline/apply_saros.py`).
* **Forward / Reverse Saros Count** — position within the Saros series counted from the first member (Forward = 1) or
  from the last member (Reverse = 1). A leading `~` marks an **estimate**: the series is cut off by the catalog edge,
  so the members beyond the edge were estimated by extending the series' gamma trend.
* **Direction** — `A` = near the start of its Saros series; `B` = near the end. When applying the shared intervals,
  **Direction B: target = start + interval; Direction A: target = start − interval.**
* Blank = not applicable.

## `Stride Calculation.csv` — all 145,356 eclipses

| Column | Meaning |
|---|---|
| Date, TD of GE, Cum. Seconds…, Delta T (s), Solar or Lunar, Type, Gamma, Magnitude, Solar Saros #, Lunar Saros # | As above |
| Off-Stride Direction | `A` or `B` for the 5,124 off-stride eclipses (on no lane); blank for the 140,232 on-stride eclipses |
| Forward Stride 1–6 | The six forward lanes. `Start` = the lane's first eclipse; a number = the step, in whole days (rounded from cumulative seconds), by which the lane reached this eclipse from its previous eclipse (693/694/695 for a 694-day stride; 1018/1019 for a 1,019-day stride); blank = not on this lane |
| Backward Stride 1–6 | The six backward lanes, same coding (walked backward in time, so the step is measured to the next-later lane eclipse) |
| Sun-Node Distance (deg) … Moon True Anomaly (deg, 0-360 from perigee) | The eight geometry columns, identical to the full catalog's (see above) |

Rule: step 694 days; if no eclipse lies within ±1.5 days (129,600 s), step 1,019 days. Each lane starts from one
eclipse at the start (forward lanes) or end (backward lanes) of the catalog. The starting eclipses were identified by
matching the eclipses the lanes miss to eclipses that match all of the off-stride shared intervals:

| Lane | Starting eclipse (TD) |
|---|---|
| Forward Stride 1 | -13198 Jun 22 01:42:58 (solar) |
| Forward Stride 2 | -13198 Dec 01 23:48:57 (lunar) |
| Forward Stride 3 | -13198 Dec 16 02:59:44 (solar) |
| Forward Stride 4 | -13197 May 27 02:18:14 (lunar) |
| Forward Stride 5 | -13197 Jun 11 15:48:35 (solar) |
| Forward Stride 6 | -13197 Nov 21 11:09:12 (lunar) |
| Backward Stride 1 | 17189 Aug 10 20:09:57 (solar) |
| Backward Stride 2 | 17189 Feb 15 05:10:55 (solar) |
| Backward Stride 3 | 17188 Sep 05 19:17:36 (lunar) |
| Backward Stride 4 | 17188 Aug 21 05:50:23 (solar) |
| Backward Stride 5 | 17188 Mar 11 20:53:34 (lunar) |
| Backward Stride 6 | 17188 Feb 26 22:16:19 (solar) |

The same lanes and the same off-stride set result for any stride tolerance from ±1.5 to ±3.5 days.

## `Off-Stride Eclipses.csv` — the 5,124 off-stride eclipses

Columns: Date, TD of GE, Cum. Seconds…, Delta T (s), Solar or Lunar, Type, Gamma, Magnitude, Solar Saros #,
Lunar Saros #, Forward Saros Count, Reverse Saros Count, Direction (all as above), **Cycle** (1–112, see
`Off-Stride Cycles.csv`), and the eight geometry columns from the full catalog (Sun-Node Distance … Moon True Anomaly). 264 rows carry a `~` estimate.

## `Off-Stride Cycles.csv` — the 112 off-stride cycles

| Column | Meaning |
|---|---|
| Cycle | Cycle number, 1–112 in time order; directions alternate A, B, A, B |
| Direction | `A` or `B` |
| First / Last Eclipse Date, TD | The first and last off-stride eclipse of the cycle |
| First / Last Eclipse Cum. Seconds from -15000 Jan 01 00:00:00 TD | The same two eclipses on the common time axis |
| Eclipses | Number of off-stride eclipses in the cycle |
| Length (Years) | First to last eclipse, in years of 365.242 days |
| Interval from Prior Cycle (Years) | Last eclipse of the previous cycle to the first eclipse of this one; negative = overlap |

Cycle rule: two consecutive off-stride eclipses of the same direction belong to the same cycle unless more than
150 years separate them (any threshold from 137.6 to 171.8 years gives the same 112 cycles). Where consecutive cycles
overlap in time, their eclipses interleave; each belongs to the cycle of its own direction. For example, the
eclipse of 16961 Apr 28 (Direction B) is 137.6 years after the previous Direction B eclipse (cycle 110) and 171.8 years
before the next (cycle 112), so it belongs to cycle 110.

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

## `Missing Half Octon Eclipses.csv` — the 4,949 missing half-octon eclipses

The empty new and full moons that link each off-stride chain to the on-stride lanes. An off-stride chain is a run of
off-stride eclipses linked by a half octon (23.5 lunations = 47 new/full moons). For Direction A, the walk goes from
the first eclipse of each chain back in steps of 47 new/full moons until it reaches an eclipse on a forward lane.
For Direction B, it goes from the last eclipse of each chain forward until it reaches an eclipse on a backward lane.
Every empty step (a new or full moon with no eclipse) is a missing half-octon eclipse. Built by
`Pattern/missing_half_octon.py`. The chains number 1,896; one of them never reaches a lane within the catalog
and is left out. Direction A has 2,478 missing eclipses and Direction B 2,471.

| Column | Meaning |
|---|---|
| Date, TD of New/Full Moon | The true new or full moon, solved from DE441 until the Moon–Sun elongation is below 1e-7° (~0.001 s), then rounded to the whole TD second. New/full moon = the geocentric geometric ecliptic longitudes of the Moon and Sun are equal (new) or 180° apart (full), in the ecliptic of date. This is the same geometric convention as the geometry columns; the almanac (apparent) instant is about 40 s earlier |
| Cum. Seconds from -15000 Jan 01 00:00:00 TD | Whole TD seconds, as in every other file |
| Solar or Lunar | New moon = `Solar` slot, full moon = `Lunar` slot |
| Direction | Direction of the off-stride chain the slot links (`A` or `B`) |
| Moon-Node Distance (deg) | The Moon's distance from its ascending or descending node, measured along its orbit, −90..+90 (osculating node on the ecliptic of date) |
| Moon Distance (mean = 1) | Earth–Moon distance ÷ 385,000.6 km (Meeus's mean distance) |
| Strides from Off-Stride Eclipse | Half-octon steps from the chain's end eclipse |
| Off-Stride Eclipse Linked | Date of that off-stride eclipse |
| Lane Eclipse Linked | Date of the lane eclipse where the walk ends |
| In Near-Miss List | `Yes` = within 1.5 days of one of the 2,993 matching eclipse near-misses (1,476 rows) |
| Sun-Node Distance (deg) … Moon True Anomaly (deg, 0-360 from perigee) | The eight geometry columns, computed with the catalog's own code (`Pipeline/add_geometry.py`) at the new/full moon |
| Sun Mean Anomaly, Osculating (deg, 0-360 from perihelion) | Mean anomaly of the osculating heliocentric orbit of the Earth–Moon barycentre |

## `Missing Half Octon Shared Intervals.csv` — the 16,526 shared intervals of the missing eclipses

The intervals shared by all 4,949 missing half-octon eclipses (0 misses). They come from the same search as
`Off-Stride Shared Intervals.csv` (±3.5 days, same test range and direction convention), run over ±10,000 years by
`Pattern/missing_shared_intervals.py`. The intervals span −4,531 to +4,772 years. The search also finds 262 / 241 /
172 intervals with 1 / 2 / 3 misses, which are not listed.

| Column | Meaning |
|---|---|
| Average, Max, Min, Standard Deviation (Seconds), Average (Days), Average (Years) | As in `Off-Stride Shared Intervals.csv` |
| In Off-Stride Shared Intervals (within 1 day) | `Yes` = the off-stride shared set has an interval within 1 day of this one (14,909 of 16,526) |

## `All Eclipses and Near-Miss Eclipses Matching All Off-Stride Shared Intervals.csv` — 10,971 points

Same columns as `Off-Stride Eclipses.csv` except Cycle, plus:

| Column | Meaning |
|---|---|
| Category | `Off-stride eclipse` (5,124), `Matching on-stride eclipse` (2,854), or `Matching eclipse near-miss` (2,993) |

* Matching = every one of the 16,377 intervals, applied in the point's direction, lands within ±3.5 days
  (302,400 s, measured from the middle of the interval's band) of an eclipse, wherever the target lies inside the
  test range.
* Near-miss rows are new or full moons with no eclipse: the eclipse columns are blank, and the cumulative seconds may
  carry a fraction (the time is derived from the interval set, not from an eclipse). 345 rows carry a `~` estimate.
* Seven near-misses were added after the workbook version, when `Pattern/matching.py` tested every moment in the test
  range (12086 Oct 01, 12137 Jul 11, 12193 Jul 07, 12602 Jul 19, 12622 Jun 24, 12998 Oct 05 — Direction A; 17189 Jan 30 —
  Direction B). Their time is the mean, over the tested intervals, of (eclipse reached − interval average), which
  places it within the window of matching times.
