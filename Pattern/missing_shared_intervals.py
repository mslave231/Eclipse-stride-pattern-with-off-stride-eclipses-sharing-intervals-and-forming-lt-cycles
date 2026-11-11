"""Shared intervals of the missing half-octon eclipses -> Outputs/Missing Half Octon Shared Intervals.csv.

Same search and conventions as Pattern/shared_intervals.py (Direction B target = start + interval, Direction A
target = start - interval, tolerance +/-3.5 days, a start is tested only if its target lies in the test range),
applied to the 4,949 missing half-octon eclipses in Outputs/Missing Half Octon Eclipses.csv (exact new/full-moon
times), over +/-10,000 years. Published: every interval shared by ALL tested missing eclipses (0 misses), in the
column format of Outputs/Off-Stride Shared Intervals.csv, plus whether the same interval (within 1 day) is also in
the off-stride shared set.

Usage:  python Pattern/missing_shared_intervals.py        (run time: several minutes)
"""
import csv

import numpy as np

from common import DAY, YEAR, SIGN, CUM, OUT, load_catalog, read_csv, load_intervals
from shared_intervals import search

SRC = OUT / 'Missing Half Octon Eclipses.csv'
DEST = OUT / 'Missing Half Octon Shared Intervals.csv'
TOL_DAYS, SPAN_YEARS = 3.5, 10000


def main():
    rows = read_csv(SRC)
    c = np.array([float(r[CUM]) for r in rows])
    sg = np.array([SIGN[r['Direction']] for r in rows])
    final = search(load_catalog()['cum'], c, sg, [f"{r['Date']} ({r['Direction']})" for r in rows],
                   TOL_DAYS * DAY, SPAN_YEARS, max_misses=3)          # same search as the off-stride set; keep 0 misses
    final = sorted((x for x in final if x['misses'] == 0), key=lambda x: x['avg'])
    pub = load_intervals()['avg']
    with open(DEST, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Average (Seconds)', 'Max (Seconds)', 'Min (Seconds)', 'Standard Deviation (Seconds)',
                    'Average (Days)', 'Average (Years)', 'In Off-Stride Shared Intervals (within 1 day)'])
        for x in final:
            k = np.clip(np.searchsorted(pub, x['avg']), 1, len(pub) - 1)
            ins = min(abs(pub[k] - x['avg']), abs(pub[k - 1] - x['avg'])) <= DAY
            w.writerow([f"{x['avg']:.1f}", f"{x['max']:.0f}", f"{x['min']:.0f}", f"{x['std']:.1f}",
                        f"{x['avg'] / DAY:.2f}", f"{x['avg'] / YEAR:.2f}", 'Yes' if ins else 'No'])
    a = np.array([x['avg'] for x in final]) / YEAR
    both = sum(1 for x in final if min(abs(pub - x['avg'])) <= DAY)
    print(f'{len(rows)} missing eclipses; {len(final):,} intervals shared by all, {a.min():,.0f} to {a.max():+,.0f} years; '
          f'{both:,} also in the off-stride shared set -> {DEST.name}')


if __name__ == '__main__':
    main()
