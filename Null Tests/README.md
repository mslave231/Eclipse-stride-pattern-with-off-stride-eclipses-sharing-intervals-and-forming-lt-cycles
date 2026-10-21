# Null Tests — random eclipse samples with the off-stride Saros-position profile

These tests ask how many intervals a **random** set of 5,124 eclipses shares, using the same interval test as
the off-stride eclipses. Seven tests were run:

* Tests 1–6 have the same Saros-position profile as the off-stride eclipses — three drawn from all eclipses and
  three from on-stride eclipses only.
* Test 7 is drawn from **interior** eclipses (at least 16 from both ends of their Saros series), and each
  eclipse's direction is chosen by the data rather than by its Saros position.

## Tests (numbered in the same order as the summary table)

| # | Test | Population drawn from | Random seed | Off-stride eclipses in the sample |
|---|------|-----------------------|-------------|-----------------------------------|
| 1 | Null Test 1 | All eclipses | 3044065046 | 766 |
| 2 | Null Test 2 | All eclipses | 3687402311 | 756 |
| 3 | Null Test 3 | All eclipses | 1660353500 | 785 |
| 4 | On-Stride Null 1 | On-stride eclipses only | 1316505538 | 0 |
| 5 | On-Stride Null 2 | On-stride eclipses only | 727232544 | 0 |
| 6 | On-Stride Null 3 | On-stride eclipses only | 4053479042 | 0 |
| 7 | Interior Null 1 | Interior eclipses (≥ 16 from both ends of their Saros series); direction chosen by the data | 1465772959 | 0 |

## Files

* `Test Eclipses/<#> - <Test> - Test Eclipses.csv` — the 5,124 eclipses drawn for the test.
* `Shared Intervals/<#> - <Test> - Shared Intervals.csv` — every interval shared by the test eclipses with
  0, 1, 2 or 3 misses.

Column conventions (dates, cumulative seconds, Saros counts, `~`, Direction) follow `../DATA_DICTIONARY.md`.
Extra columns in the Test Eclipses files:

| Column | Meaning |
|---|---|
| F/L Saros Count | The bucket the eclipse was drawn for (its position from the start or end of its Saros series) |
| Sampled Side | `Start of Saros series` (drawn on its Forward Saros Count) or `End of Saros series` (drawn on its Reverse Saros Count) |
| Direction | `A` for start-side eclipses, `B` for end-side eclipses (same convention as the off-stride eclipses) |
| On-Stride or Off-Stride | Whether the drawn eclipse lies on a stride lane |

Test 7's Test Eclipses file replaces `F/L Saros Count` and `Sampled Side` with `Position from Nearer End`
(the smaller of the two Saros counts, 16 or more) and `Nearer End of Saros Series` (`Nearer start`,
`Nearer end`, or `Middle`); its `Direction` is the data-chosen direction.

Shared Intervals columns:

| Column | Meaning |
|---|---|
| Average / Max / Min / Standard Deviation (Seconds) | Mean, largest-magnitude, smallest-magnitude, and sample standard deviation of the interval's measured values (signed; negative = into the past) |
| % Correct | Test eclipses that hit ÷ test eclipses tested for this interval |
| # Missed | Test eclipses tested for this interval that did not hit (0–3) |
| Eclipse #1–#3 Missed | Dates of the test eclipses that missed |
| Average (Days) / Average (Years) | Average ÷ 86,400 / ÷ 31,556,925 (365.2422 days), rounded to 0.01 |

## Sampling method (tests 1–6)

1. **Profile.** The off-stride eclipses fall into 16 buckets by their position from the nearer end of their
   Saros series (F/L Saros Count = 1 for the first or last member, 2 for the second, …). Each sample has
   exactly the same number of eclipses in each bucket:

   | Bucket | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | Total |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
   | Eclipses | 1,052 | 832 | 659 | 551 | 461 | 382 | 313 | 256 | 205 | 158 | 114 | 81 | 40 | 15 | 4 | 1 | 5,124 |

2. **Directions.** Within each bucket, half the eclipses are drawn from the start side of a Saros series
   (Forward Saros Count = bucket; Direction A) and half from the end side (Reverse Saros Count = bucket;
   Direction B). For odd bucket sizes the extra eclipse goes to a randomly chosen side.
3. **Eligibility.** Only eclipses whose count on the drawn side is exact are eligible (no `~` estimates, i.e. no
   series cut off by the catalog edge on that side). Tests 1–3 draw from all eclipses; tests 4–6 draw from
   on-stride eclipses only. No eclipse is drawn twice within a test.
4. **Randomness.** NumPy `default_rng(seed)` with the seed listed above; each seed came from the operating
   system's random source, and re-using it reproduces the sample exactly.

## Interior test (test 7)

1. **Population.** All eclipses whose Forward and Reverse Saros Counts are both exact and both at least 16
   (80,871 eclipses). 5,124 were drawn uniformly at random (seed 1465772959).
2. **Direction chosen by the data.** Interior eclipses are not near either end of a Saros series, so direction is
   not taken from Saros position. Instead:
   * an anchor eclipse near the middle of the record (1664 Jul 23) is fixed at Direction B; every other eclipse
     takes the direction in which more of the anchor's intervals (|D| ≤ 5,000 years) land on eclipses within
     ±3.5 days;
   * the interval test below is run with those directions;
   * eclipses that would miss fewer of the resulting shared intervals facing the other way are flipped as a batch,
     and the batch is **kept only if the new test finds more 0-miss intervals** (otherwise the strongest quarter of
     the batch is tried); this repeats until no batch improves the result.

   | Round | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
   |---|---|---|---|---|---|---|---|---|---|
   | Eclipses flipped | (anchor directions) | 105 | 82 | 87 | 68 | 40 | 18 | 9 | 6, then 1 — no improvement |
   | Shared intervals, 0 misses | 4,174 | 5,676 | 6,743 | 7,351 | 7,439 | 7,462 | 7,472 | 7,473 | 7,473 (stop) |

3. **Final directions:** 2,466 Direction A and 2,658 Direction B. Compared with which end of its Saros series each
   eclipse is nearer:

   | | Nearer start | Nearer end | Middle |
   |---|---|---|---|
   | Direction A (target = start − D) | 2,312 | 122 | 32 |
   | Direction B (target = start + D) | 129 | 2,503 | 26 |

   The data-chosen direction matches the nearer end (A = nearer start, B = nearer end) for 4,815 of 5,066
   eclipses (95.0%).

## Interval test

The test is the same as the Saros-edge window tests:

* An interval `D` is applied from each test eclipse in its direction: **Direction B: target = start + D;
  Direction A: target = start − D.**
* A test eclipse is tested for `D` only if its target lies between cumulative seconds 56,881,000,000 and
  1,015,815,000,000.
* It **hits** when a catalog eclipse (other than itself) lies at the target, such that the implied intervals of
  all hits fit inside **one window of 2 × 3.5 days** (tolerance ±3.5 days = 302,400 s). Each interval is
  therefore a narrow band; Average/Max/Min/Standard Deviation describe the values inside the window.
* **Misses** = test eclipses tested for `D` that do not hit. Intervals with 0–3 misses are listed.
* All intervals out to ±5,000 years were searched.

Search procedure: every implied interval (|D| ≤ 5,000 years) from four reference test eclipses that stay in the
test range for the whole search span is a candidate (with at most 3 misses, at least one reference must hit, so
no valid interval can be skipped). Candidates are screened with 64 randomly chosen test eclipses, evaluated in
full, re-evaluated centred on each band's average, and duplicates (bands within 2 × 3.5 days) are merged.

**Check of the method:** run on the 5,124 off-stride eclipses with the same settings, this procedure returns
exactly the published shared interval set — 16,377 intervals with 0 misses (each within 0.05 s of
`../Outputs/Off-Stride Shared Intervals.csv`), 251 with 1 miss and 255 with 2 misses.

## Results

| | Null Test 1 | Null Test 2 | Null Test 3 | On-Stride Null 1 | On-Stride Null 2 | On-Stride Null 3 | Interior Null 1 | Off-stride eclipses |
|---|---|---|---|---|---|---|---|---|
| Test eclipses | 5,124 | 5,124 | 5,124 | 5,124 | 5,124 | 5,124 | 5,124 | 5,124 |
| Shared intervals, 0 misses | 9,875 | 9,663 | 9,780 | 10,447 | 10,507 | 10,315 | 7,473 | 16,377 |
| Span (years) | −3,683 to +3,744 | −3,609 to +3,764 | −3,609 to +3,640 | −3,683 to +4,038 | −3,750 to +4,020 | −3,665 to +3,744 | −3,301 to +3,314 | −4,862 to +4,761 |
| Also in the off-stride shared interval set | 9,761 | 9,495 | 9,626 | 9,601 | 9,661 | 9,448 | 2,498 | — |
| Not in the off-stride shared interval set | 114 | 168 | 154 | 846 | 846 | 867 | 4,975 | — |
| Intervals with 1 / 2 / 3 misses | 533 / 332 / 277 | 570 / 370 / 276 | 596 / 456 / 279 | 544 / 389 / 308 | 543 / 343 / 271 | 722 / 380 / 312 | 451 / 277 / 195 | 251 / 255 / 141 |

"Also in the off-stride shared interval set" counts 0-miss intervals whose average is within 1 day of an
interval in `../Outputs/Off-Stride Shared Intervals.csv`.
