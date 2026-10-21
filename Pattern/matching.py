"""Find every point in time that matches all of the off-stride shared intervals (report Section 6).

A point t matches in a direction when every one of the 16,377 shared intervals D, applied from t in that direction
(Direction B: t + D; Direction A: t - D) lands within the tolerance (default +/-3.5 days) of a catalog eclipse,
measured from the middle of the interval's band (mean of Max and Min). An interval whose target (using the
interval's average) lies outside the test range is not tested from that point (counted as neither a hit nor a miss).

Every moment in the test range is tested, not only eclipses: the set of matching times is built exactly as an
intersection of windows. One reference interval gives the candidate windows (one per catalog eclipse, 7 days wide);
each further interval narrows every window to the part whose target still lands on an eclipse, and windows that
become empty are dropped. The surviving windows are the matching times. A window that contains a catalog eclipse is
a matching eclipse (off-stride or on-stride); a window with no eclipse is a matching eclipse near-miss.

Usage:  python pattern/matching.py [--tolerance DAYS] [--out FILE.csv]
Checks the result against Outputs/All Eclipses and Near-Miss Eclipses Matching All Off-Stride Shared Intervals.csv.
"""
import argparse
import csv
from collections import Counter

import numpy as np

from common import DAY, TEST_MIN, TEST_MAX, SIGN, OUT, CUM, load_catalog, load_intervals, read_csv

PUBLISHED = OUT / 'All Eclipses and Near-Miss Eclipses Matching All Off-Stride Shared Intervals.csv'


def matching_windows(cat, mid, avg, s, tol):
    """Matching time windows [lo, hi] for direction sign s."""
    out_lo, out_hi = [], []
    order = np.argsort(np.abs(mid))
    # two reference intervals of opposite sign: for any t, at least one of them is tested
    refs = [order[np.argmax(mid[order] > 0)], order[np.argmax(mid[order] < 0)]]
    for ref in refs:
        lo = cat - s * mid[ref] - tol
        hi = cat - s * mid[ref] + tol
        tested = (cat - s * mid[ref] + s * avg[ref] >= TEST_MIN) & (cat - s * mid[ref] + s * avg[ref] <= TEST_MAX)
        keep = tested & (lo <= TEST_MAX) & (hi >= TEST_MIN)
        lo, hi = lo[keep], hi[keep]
        for j in order:
            if len(lo) == 0:
                break
            m = (lo + hi) / 2
            inr = (m + s * avg[j] >= TEST_MIN) & (m + s * avg[j] <= TEST_MAX)
            tgt = m + s * mid[j]
            k = np.clip(np.searchsorted(cat, tgt), 1, len(cat) - 1)
            e = np.where(np.abs(cat[k - 1] - tgt) <= np.abs(cat[k] - tgt), cat[k - 1], cat[k])
            # times t whose target t + s*mid lands within tol of eclipse e
            nlo = np.where(inr, np.maximum(lo, e - s * mid[j] - tol), lo)
            nhi = np.where(inr, np.minimum(hi, e - s * mid[j] + tol), hi)
            ok = nlo <= nhi
            lo, hi = nlo[ok], nhi[ok]
        out_lo.append(lo); out_hi.append(hi)
    lo, hi = np.concatenate(out_lo), np.concatenate(out_hi)
    w = sorted(zip(lo, hi))
    merged = []
    for a, b in w:                                    # windows found from both references are the same window
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def misses_at(cat, t, mid, avg, s, tol):
    inr = (t + s * avg >= TEST_MIN) & (t + s * avg <= TEST_MAX)
    tgt = t + s * mid[inr]
    k = np.clip(np.searchsorted(cat, tgt), 1, len(cat) - 1)
    return int((np.minimum(np.abs(cat[k] - tgt), np.abs(cat[k - 1] - tgt)) > tol).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tolerance', type=float, default=3.5)
    ap.add_argument('--out', default='matching_points_result.csv')
    a = ap.parse_args()
    tol = a.tolerance * DAY
    C = load_catalog()
    cat = C['cum']
    I = load_intervals()
    off = {float(r[CUM]) for r in read_csv(OUT / 'Off-Stride Eclipses.csv')}
    points = []
    for d, s in SIGN.items():
        for lo, hi in matching_windows(cat, I['mid'], I['avg'], s, tol):
            inside = np.where((cat >= lo) & (cat <= hi))[0]
            if len(inside):
                for i in inside:
                    if misses_at(cat, cat[i], I['mid'], I['avg'], s, tol):
                        print('warning: eclipse inside a matching window misses an interval:', C['date'][i], d)
                    points.append(dict(t=cat[i], i=int(i), d=d, cat='Off-stride eclipse' if cat[i] in off else 'Matching on-stride eclipse',
                                       lo=lo, hi=hi))
            else:
                points.append(dict(t=(lo + hi) / 2, i=None, d=d, cat='Matching eclipse near-miss', lo=lo, hi=hi))
    points.sort(key=lambda p: p['t'])
    print(f'tolerance +/-{a.tolerance} days: {len(points):,} matching points', dict(Counter(p['cat'] for p in points)))
    print('by direction', dict(Counter((p['cat'], p['d']) for p in points)))

    with open(a.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Date', 'TD of GE', CUM, 'Window Start (Cum. Seconds)', 'Window End (Cum. Seconds)', 'Direction', 'Category'])
        for p in points:
            i = p['i']
            w.writerow([C['date'][i] if i is not None else '', C['td'][i] if i is not None else '',
                        f"{p['t']:.0f}", f"{p['lo']:.0f}", f"{p['hi']:.0f}", p['d'], p['cat']])
    print('written', a.out)

    # --- compare with the published file
    pub = read_csv(PUBLISHED)
    pe = Counter((float(r[CUM]), r['Direction']) for r in pub if r['Category'] != 'Matching eclipse near-miss')
    me = Counter((p['t'], p['d']) for p in points if p['i'] is not None)
    print('matching eclipses identical to published file:', pe == me, f'({sum(pe.values()):,} published)')
    pn = sorted((float(r[CUM]), r['Direction']) for r in pub if r['Category'] == 'Matching eclipse near-miss')
    mn = [p for p in points if p['i'] is None]
    pt = np.array([t for t, _ in pn])
    inside = [sum(1 for t, d in pn[max(0, k - 3):k + 3] if d == p['d'] and p['lo'] <= t <= p['hi'])
              for p in mn for k in [int(np.searchsorted(pt, p['lo']))]]
    print(f'computed near-miss windows: {len(mn):,}; published near-misses: {len(pn):,}; '
          f'windows holding exactly one published near-miss: {inside.count(1):,}')


if __name__ == '__main__':
    main()
