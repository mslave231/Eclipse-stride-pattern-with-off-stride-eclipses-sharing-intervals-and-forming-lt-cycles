"""Group the off-stride eclipses into cycles (report Section 5).

Rule: two consecutive off-stride eclipses of the same direction belong to the same cycle unless more than
--gap years (default 150) separate them. Cycles are numbered in time order of their first eclipse. Where
consecutive cycles overlap in time, their eclipses interleave; each eclipse belongs to the cycle of its own
direction. Years are 365.242 days.

Usage:  python Pattern/cycles.py [--gap YEARS] [--scan] [--write]
Checks the result against the Cycle column of Outputs/Off-Stride Eclipses.csv and Outputs/Off-Stride Cycles.csv,
and prints the cycle statistics. --scan reports the range of gap thresholds that give the same cycles. --write
rewrites Outputs/Off-Stride Cycles.csv (it refuses if any previously published value would change).
"""
import argparse
import csv
import os

import numpy as np

from common import CYCLE_YEAR, OUT, CUM, read_csv

HEADER = ['Cycle', 'Direction', 'First Eclipse Date', 'First Eclipse TD', 'First Eclipse ' + CUM,
          'Last Eclipse Date', 'Last Eclipse TD', 'Last Eclipse ' + CUM, 'Eclipses', 'Length (Years)',
          'Interval from Prior Cycle (Years)']


def cycles(rows, gap_years):
    """Cycle number (1..) for each row (rows in time order)."""
    gap = gap_years * CYCLE_YEAR
    groups, last = [], {}
    for i, r in enumerate(rows):
        d, t = r['Direction'], float(r[CUM])
        if d in last and t - last[d][1] <= gap:
            groups[last[d][0]].append(i)
            last[d] = (last[d][0], t)
        else:
            groups.append([i])
            last[d] = (len(groups) - 1, t)
    groups.sort(key=lambda g: float(rows[g[0]][CUM]))
    out = [0] * len(rows)
    for n, g in enumerate(groups, 1):
        for i in g:
            out[i] = n
    return out


def stats(v):
    v = np.asarray(v)
    return f'{v.min():.1f} to {v.max():.1f} (mean {v.mean():.1f}, median {np.median(v):.1f})'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gap', type=float, default=150.0)
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    rows = read_csv(OUT / 'Off-Stride Eclipses.csv')
    cyc = cycles(rows, a.gap)
    n = max(cyc)
    print(f'gap rule {a.gap} years: {n} cycles')
    print('matches Cycle column of Off-Stride Eclipses.csv:', cyc == [int(r['Cycle']) for r in rows])

    t = np.array([float(r[CUM]) for r in rows])
    first = [t[[i for i, k in enumerate(cyc) if k == c]].min() for c in range(1, n + 1)]
    last = [t[[i for i, k in enumerate(cyc) if k == c]].max() for c in range(1, n + 1)]
    count = [cyc.count(c) for c in range(1, n + 1)]
    dirs = [rows[cyc.index(c)]['Direction'] for c in range(1, n + 1)]
    length = [(l - f) / CYCLE_YEAR for f, l in zip(first, last)]
    trans = [(first[k] - last[k - 1]) / CYCLE_YEAR for k in range(1, n)]

    pub = read_csv(OUT / 'Off-Stride Cycles.csv')
    same = len(pub) == n and all(
        p['Direction'] == d and int(p['Eclipses']) == e and abs(float(p['Length (Years)']) - L) < 0.051
        for p, d, e, L in zip(pub, dirs, count, length))
    print('matches Outputs/Off-Stride Cycles.csv:', same)
    print('directions alternate:', all(dirs[k] != dirs[k - 1] for k in range(1, n)))
    print('length (years):', stats(length))
    print('eclipses per cycle:', f'{min(count)} to {max(count)} (mean {np.mean(count):.1f}, median {np.median(count):.1f})')
    brk = [x for x in trans if x > 0]; ovl = [-x for x in trans if x <= 0]
    print(f'transitions: {len(brk)} clean breaks, {stats(brk)}; {len(ovl)} overlaps, {stats(ovl)}')
    ss = [(first[k] - first[k - 2]) / CYCLE_YEAR for k in range(2, n)]
    print('start to start, same direction (years):', f'{min(ss):.0f} to {max(ss):.0f} (mean {np.mean(ss):.0f}, median {np.median(ss):.0f})')
    big = max(ovl)
    print(f'longest overlap {big:.1f} years, between cycles',
          ', '.join(f'{k} and {k + 1}' for k in range(1, n) if abs(-trans[k - 1] - big) < 0.05))

    if a.write:
        table = []
        for c in range(1, n + 1):
            idx = [i for i, k in enumerate(cyc) if k == c]
            f, l = min(idx, key=lambda i: t[i]), max(idx, key=lambda i: t[i])
            table.append({'Cycle': str(c), 'Direction': dirs[c - 1],
                          'First Eclipse Date': rows[f]['Date'], 'First Eclipse TD': rows[f]['TD of GE'],
                          'First Eclipse ' + CUM: rows[f][CUM],
                          'Last Eclipse Date': rows[l]['Date'], 'Last Eclipse TD': rows[l]['TD of GE'],
                          'Last Eclipse ' + CUM: rows[l][CUM], 'Eclipses': str(count[c - 1]),
                          'Length (Years)': f'{length[c - 1]:.1f}',
                          'Interval from Prior Cycle (Years)': f'{trans[c - 2]:.1f}' if c > 1 else ''})
        changed = [(k, p[k], r[k]) for p, r in zip(pub, table) for k in p if k in r and p[k] != r[k]]
        assert len(pub) == len(table) and not changed, f'published values would change: {changed[:5]}'
        tmp = str(OUT / 'Off-Stride Cycles.csv') + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=HEADER); w.writeheader(); w.writerows(table)
        os.replace(tmp, OUT / 'Off-Stride Cycles.csv')
        print('wrote Outputs/Off-Stride Cycles.csv (all previously published values unchanged)')

    if a.scan:
        ok = [g / 10 for g in range(1000, 2500) if cycles(rows, g / 10) == cyc]
        print(f'thresholds giving the same {n} cycles: {min(ok):.1f} to {max(ok):.1f} years (0.1-year steps)')


if __name__ == '__main__':
    main()
