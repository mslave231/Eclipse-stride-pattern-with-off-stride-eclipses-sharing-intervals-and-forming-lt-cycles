# 30,000-Year Eclipse Catalog and Stride-Pattern Results, −13198 to +17189

A catalog of every solar and lunar eclipse from **−13198 to +17189** (astronomical
year numbering; year 0 = 1 BCE) — **145,356 eclipses** (72,224 solar, 73,132 lunar,
~4.78 per year) — computed directly from the JPL **DE441** ephemeris and compared with
NASA's *Five Millennium Catalogs* and an independent catalog by Yuk Tung Liu — together
with the results of a 694/1,019-day stride analysis of the full eclipse sequence.

The catalog was built in the format of NASA's catalogs, then extended over the full
time span DE441 covers (−13200 Aug 15 .. +17191 Mar 15).

## Terms

* **Lane** — one of the 6 forward or 6 backward walks produced by the stride rule: from an
  eclipse step 694 days; if no eclipse lies within ±1.5 days (129,600 s), step 1,019 days.
  Each lane starts from one eclipse at the catalog's start (forward) or end (backward); the
  starting eclipses were identified by matching the eclipses the lanes miss to eclipses that
  match all of the off-stride shared intervals, and are listed in `DATA_DICTIONARY.md`.
  The same lanes result for any stride tolerance from ±1.5 to ±3.5 days.
* **On-stride eclipse** — an eclipse on at least one lane (140,232).
* **Off-stride eclipse** — an eclipse on no lane (5,124).
* **Shared interval set** — the 16,377 intervals that lead from every off-stride eclipse to
  another eclipse.
* **Direction A / Direction B** — the two directions in which the shared intervals apply:
  A for off-stride eclipses near the start of their Saros series (target = start − interval),
  B for those near the end (target = start + interval).
* **Matching on-stride eclipse** — an on-stride eclipse that matches all 16,377 intervals (2,854).
* **Matching eclipse near-miss** — a new or full moon with no eclipse that matches all
  16,377 intervals (2,993).
* **Off-stride cycle** — a group of off-stride eclipses of the same direction. Two
  consecutive same-direction off-stride eclipses belong to the same cycle unless more than
  150 years separate them (any threshold from 137.6 to 171.8 years gives the same 112 cycles).
  The cycles alternate A, B, A, B; where consecutive cycles overlap in time, their eclipses
  interleave.

## Repository contents

| Path | Contents |
|------|----------|
| `Outputs/eclipse_catalog_full_-13198_17189_detailed.csv` | The full catalog: Date, TD of greatest eclipse, ΔT, kind, type code, type, gamma, magnitude, umbral & penumbral magnitudes, plus Forward and Reverse Saros Count (`~` = estimated). Start here to replicate the pattern results without recomputing the catalog |
| `Outputs/694-1,019 Stride Calculation.csv` | Every eclipse with its six forward and six backward stride lanes and, for off-stride eclipses, Direction A/B |
| `Outputs/Off-Stride Eclipses.csv` | The 5,124 off-stride eclipses with Saros numbers, Saros positions, Direction and Cycle |
| `Outputs/Off-Stride Cycles.csv` | The 112 off-stride cycles: direction, first and last eclipse, eclipse count, length, and interval from the prior cycle |
| `Outputs/Off-Stride Shared Intervals.csv` | The 16,377 shared intervals |
| `Outputs/All Eclipses and Near-Miss Eclipses Matching All Off-Stride Shared Intervals.csv` | Every point that matches all 16,377 intervals: off-stride eclipses, matching on-stride eclipses, and matching eclipse near-misses |
| `Null Tests/` | Seven null tests: random samples of 5,124 eclipses — six with the off-stride Saros-position profile (three from all eclipses, three from on-stride eclipses only) and one from interior eclipses with data-chosen directions — their shared intervals, and a README describing the method and results |
| `pattern/` | Scripts that recompute the pattern results from the `Outputs/` files and check them against the published files: lanes, shared intervals, matching points, cycles, and null tests (see *Reproducing the pattern*) |
| `DATA_DICTIONARY.md` | Column definitions and conventions for the `Outputs/` files |
| `eclipse_catalog.py` | The eclipse engine (one year range per run; needs `de441.bsp`) |
| `pipeline/` | stitch.py, reformat_catalog.py, augment_catalog.py, apply_saros.py, recount_saros.py, sanity_check.py, compare_ref.py |
| `_saros_numbers.xlsx` | Saros reference numbering for −3999..+4000 (input to `pipeline/apply_saros.py`) |
| `validate.py`, `reference_nasa/` | Comparison with NASA SEcat5 / LEcat5 for 1001–2000 (cached NASA pages; Eclipse Predictions by Fred Espenak, NASA's GSFC) |
| `FULL_CATALOG_SUMMARY.md` | Summary of the catalog build and comparisons |

Not included: the JPL `de441.bsp` ephemeris (~3 GB; download it from
https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de441.bsp), and Yuk Tung Liu's catalogs (download from
https://ytliu.epizy.com/eclipse/ to run `pipeline/compare_ref.py`). The pipeline's intermediate files
(`eclipse_catalog_full_-13198_17189.csv`, `eclipse_catalog_full_formatted.csv`) are regenerated by running the
pipeline.

## Catalog column conventions

* **Date** — Julian calendar before 1582 Oct 15, Gregorian after (NASA convention).
* **TD of greatest eclipse** — Terrestrial (Dynamical) Time, to the second.
* **ΔT** — TD − UT in seconds, from Espenak & Meeus (2006) with NASA's lunar
  secular-acceleration correction (see Method). ΔT is a *model* far from the
  present and affects only this column — never the eclipse times.
* **Magnitude** — solar: eclipse magnitude; lunar: umbral magnitude for total/partial,
  penumbral magnitude for penumbral eclipses.
* **Gamma** — distance of the shadow axis from Earth's centre at greatest eclipse, in
  Earth radii (sign: north/south of the J2000 equator).
* **cum. seconds** — whole TD seconds since −15000 Jan 1 00:00 (Julian calendar
  before 1582 Oct 15, Gregorian after). Subtract two rows for the exact interval.
* The catalog's first year is partial: the scan starts at Gregorian −13198 Jan 1,
  which is **Julian −13198 Apr 12**.

## How to reproduce

Requires Python 3 with `numpy`, `skyfield`, `openpyxl`, and the JPL ephemeris
`de441.bsp` (~3 GB), downloaded from https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de441.bsp
and placed in this folder. It is not stored in this repository.

```
python eclipse_catalog.py 1000 2000          # one range (~10 min) -> eclipse_catalog_1000_2000[_detailed].csv
python validate.py                           # compare 1001-2000 with NASA
```

Full catalog: run the six ranges −13198..−8200, −8199..−3200, −3199..1800,
1801..6800, 6801..11800, 11801..17189 (≈50 min each), then `pipeline/stitch.py`,
`reformat_catalog.py`, `augment_catalog.py`, `apply_saros.py`, `recount_saros.py`.

## Reproducing the pattern

The scripts in `pattern/` need only Python 3 and `numpy`, and read the `Outputs/` files (no ephemeris needed). Each
prints its results and whether they agree with the published files. Run them from the repository folder:

```
python pattern/lanes.py --check-tolerances   # 12 lanes, 140,232 on-stride / 5,124 off-stride, stride statistics (seconds)
python pattern/shared_intervals.py           # shared interval search from the off-stride eclipses (several minutes)
python pattern/matching.py                   # every moment in the test range that matches all 16,377 intervals (~2 min)
python pattern/cycles.py --scan              # the 112 off-stride cycles and their statistics
python pattern/null_tests.py 1 --search      # redraw null test 1 (of 1-7) from its seed and run its search
```

| Script | Reproduces |
|---|---|
| `lanes.py` | Lanes from the 12 starting eclipses at ±1.5 days; same result from ±1.5 to ±3.5 days; stride statistics |
| `shared_intervals.py` | 16,377 intervals with 0 misses (also 251 / 255 / 141 with 1 / 2 / 3 misses) at ±3.5 days; works on any eclipse list with a Direction column |
| `matching.py` | 5,124 off-stride eclipses, 2,854 matching on-stride eclipses, 2,993 matching eclipse near-misses |
| `cycles.py` | 112 cycles from the 150-year rule; the same cycles for thresholds from 137.6 to 171.8 years |
| `null_tests.py` | The seven null-test samples from their seeds, their shared-interval searches, and the interior test's direction refinement |
| `common.py` | Shared file readers and constants |

The Saros counts and their `~` estimates are read from the catalog file; they come from the catalog pipeline, not
from these scripts.

## Method

1. **Positions** — apparent geocentric positions of the Sun and Moon from DE441 via
   skyfield (light-time, aberration, deflection).
2. **New and full moons** — found directly from the ephemeris by root-finding the
   Moon–Sun longitude difference (no analytical series, which degrade far from J2000).
3. **Screen** — syzygies with the Moon more than 1.75° from the shadow axis cannot
   produce an eclipse and are skipped (true limit ≈ 1.58°).
4. **Greatest eclipse** — the instant the shadow axis passes closest to Earth's centre
   (solar) or the Moon passes closest to the centre of Earth's shadow (lunar), refined
   to about one second; gamma is that minimum distance.
5. **Type and magnitude** — standard shadow geometry. Two constants are calibrated to
   NASA: a 63.5 km atmospheric enlargement of Earth's shadow (lunar), and lunar radius
   k = 0.272307 for solar magnitudes. Central solar eclipses use the topocentric
   diameter ratio; non-central ones the obscuration formula.
6. **ΔT** — Espenak & Meeus (2006) polynomials plus NASA's correction
   −0.000012932 × (year − 1955)² s (Moon's secular acceleration n-dot = −25.858″/cy²),
   applied outside 1955–2005. Matches NASA's published ΔT to 0.25 s (1001–2000) and
   within ~1 s at spot checks from −1999 to +3000.

## Comparison with other catalogs

| Compared with | Result |
|-------|--------|
| NASA SEcat5/LEcat5, 1001–2000 | 4,816 of 4,816 eclipses reproduced, 0 missing; TD 0.66 s (solar) / 3 s (lunar) mean; gamma 0.00004; magnitude 0.00014–0.00018; 6 type differences |
| Yuk Tung Liu catalog, −3999..+4000 (independent ELP/MPP02 + VSOP pipeline) | Identical counts (19,013 solar, 19,271 lunar); all dates matched except one near-zero-magnitude graze each side; gamma identical to 4 decimals; solar TD ≤ 1 s, lunar ≤ 13 s |
| Saros–Inex panorama by L. Quaglia & J. Tilley (Solex numerical integration; hosted on NASA's eclipse website), −11000..+15000 | 61,231 of 61,775 solar panorama cells at identical Saros/Inex coordinates; within −3999..+4000 the two differ only by one near-zero-magnitude first/last eclipse in 11 series |
| Internal (full span) | No Saros series missing an interior member; 4.76–4.81 eclipses/yr in every 2,000-yr block; solar/lunar ratio 0.984–0.990 |

Beyond −3999..+4000 there is no external eclipse catalog; eclipse times there are
DE441-grade, while ΔT is model-extrapolated.

## Known limitations

* **Total vs hybrid** — the hybrid test uses the geocentric diameter ratio as a proxy
  for the path ends, so a few hybrids are labelled total (4 vs NASA in 1001–2000;
  31 vs Liu in −3999..+4000).
* **Near-zero-magnitude grazes** — eclipses with magnitude ≲ 0.004 at the very start or
  end of a Saros series can differ between ephemerides; e.g. NASA's Saros 69 page lists
  78 eclipses, while this catalog (and Liu's) includes one more of magnitude 0.0007.
* **Saros numbering** — within −3999..+4000 every eclipse carries the Saros number from
  `_saros_numbers.xlsx`, a reference list Matt Slavik built from Yuk Tung Liu's eclipse
  data and numbered himself: matched to NASA's Saros numbering wherever it could be
  verified, and calculated where it could not. Series lying entirely outside that range are numbered by the standard
  mod-223 rule fitted to the reference data; those numbers are this catalog's own
  convention, not an external standard, and differ for ~145 solar series from the
  Quaglia & Tilley panorama's extended numbering. Details in `pipeline/apply_saros.py`.

## Acknowledgements

* **Yuk Tung Liu (廖育棟)** — solar and lunar eclipse catalogs, −3999 to +4000
  (https://ytliu.epizy.com/eclipse/). The independent catalog this one is compared
  with over −3999..+4000 (`pipeline/compare_ref.py`), and the eclipse data from which
  Matt Slavik built the reference eclipse list used for Saros numbering (the Saros numbers
  themselves are Matt Slavik's; see "Known limitations"). His catalogs are computed with
  his own ELP/MPP02-based lunar ephemeris fitted to JPL DE406 and a VSOP-class solar
  theory, independently of this project.
* **NASA eclipse catalogs** — used for comparison over 1001–2000 (`validate.py`; the
  catalog pages are cached in `reference_nasa/`) and for the ΔT method.
  **Eclipse Predictions by Fred Espenak (NASA's GSFC).**
* **Luca Quaglia and John Tilley** — solar Saros–Inex panorama, −11000 to +15000, computed
  with an integrator built on the core of Aldo Vitagliano's Solex; hosted on NASA's
  eclipse website (https://eclipse.gsfc.nasa.gov/SEsaros/SEpanorama.html). Used to
  cross-check Saros/Inex coordinates.
* **JPL Solar System Dynamics group** — the DE441 ephemeris, the source of every eclipse
  position and time.

## References

**Ephemeris and software**
* Park, R. S., Folkner, W. M., Williams, J. G., & Boggs, D. H. (2021). The JPL Planetary
  and Lunar Ephemerides DE440 and DE441. *The Astronomical Journal*, 161, 105.
  Ephemeris file: https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de441.bsp
* Rhodes, B. (2019). Skyfield: High precision research-grade positions for planets and
  Earth satellites generator. Astrophysics Source Code Library, ascl:1907.024.
* Harris, C. R., et al. (2020). Array programming with NumPy. *Nature*, 585, 357–362.
* openpyxl — Python library for reading/writing Excel files (https://openpyxl.readthedocs.io/).

**Eclipse catalogs used for comparison and numbering**
* Espenak, F., & Meeus, J. (2006). *Five Millennium Canon of Solar Eclipses: −1999 to
  +3000*. NASA Technical Publication TP-2006-214141.
* Espenak, F., & Meeus, J. (2009). *Five Millennium Canon of Lunar Eclipses: −1999 to
  +3000*. NASA Technical Publication TP-2009-214172.
* Espenak, F., & Meeus, J. *Five Millennium Catalog of Solar Eclipses* and *Five
  Millennium Catalog of Lunar Eclipses*, online at https://eclipse.gsfc.nasa.gov/SEcat5/
  and https://eclipse.gsfc.nasa.gov/LEcat5/ — Eclipse Predictions by Fred Espenak (NASA's GSFC).
* Liu, Y. T. Solar and lunar eclipse catalogs, −3999 to +4000.
  https://ytliu.epizy.com/eclipse/
* Quaglia, L., & Tilley, J. Saros–Inex panorama of solar eclipses, −11000 to +15000.
  https://eclipse.gsfc.nasa.gov/SEsaros/SEpanorama.html

**Methods**
* Meeus, J. (1998). *Astronomical Algorithms*, 2nd ed. Willmann-Bell. — calendar
  conversions (Ch. 7), mean-lunation estimate used to seed each new/full-moon search
  (Ch. 49), and the standard solar-eclipse magnitude formulas (Ch. 54).
* Espenak, F., & Meeus, J. (2006), as above — ΔT polynomial expressions (`delta_t()` in
  `eclipse_catalog.py`).
* Morrison, L. V., & Stephenson, F. R. (2004). Historical values of the Earth's clock error
  ΔT and the calculation of eclipses. *Journal for the History of Astronomy*, 35, 327–336.
  — the historical ΔT fits on which the Espenak & Meeus expressions are based.
* Chapront, J., Chapront-Touzé, M., & Francou, G. (2002). A new determination of lunar
  orbital parameters, precession constant and tidal acceleration from LLR measurements.
  *Astronomy & Astrophysics*, 387, 700–709. — source of the lunar secular acceleration
  (n-dot = −25.858″/cy²) behind NASA's ΔT correction (`delta_t_catalog()`).
* van den Bergh, G. (1955). *Periodicity and Variation of Solar (and Lunar) Eclipses*.
  H. D. Tjeenk Willink, Haarlem. — origin of the Saros–Inex scheme and numbering used by
  NASA, and followed here.

## Change log

* 2026-10-20 — ΔT: added the missing Espenak–Meeus 2050–2150 segment and replaced the
  fitted 1000–2000 correction with NASA's lunar-acceleration term (ΔT column
  recomputed in both CSVs; eclipse times unchanged). Engine: year ranges are now
  half-open [START Jan 1, END+1 Jan 1) so chunks tile exactly (the old end skipped
  Dec 31 of each chunk; no eclipse fell on those days). Documentation updated.
* 2026-10-20 — Added the stride-analysis result files (`Outputs/`) and `DATA_DICTIONARY.md`.
* 2026-10-21 — Added the null tests (`Null Tests/`), including the interior test (test 7).
* 2026-10-21 — Stride tolerance stated as ±1.5 days (the lanes are identical from ±1.5 to ±3.5 days). Added the
  off-stride cycles (`Outputs/Off-Stride Cycles.csv` and a Cycle column in `Outputs/Off-Stride Eclipses.csv`; the
  eclipse of 16961 Apr 28 belongs to cycle 110 under the 150-year rule). Added the `pattern/` scripts. Testing every
  moment in the test range found 7 matching eclipse near-misses not in the earlier list, which were added (2,986 → 2,993;
  10,964 → 10,971 matching points).
