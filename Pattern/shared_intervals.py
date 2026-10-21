"""Find every interval shared by a set of eclipses (report Section 4).

Each eclipse i has a start time c_i (cumulative seconds) and a direction (A or B). An interval D is applied from it
as target = c_i + D (Direction B) or c_i - D (Direction A). The eclipse is tested for D only if the target lies in
the test range (cumulative seconds 56,881,000,000 to 1,015,815,000,000); otherwise it is not tested from that
eclipse (counted as neither a hit nor a miss). It hits when a catalog eclipse (other than itself) lies at the
target such that the implied intervals of all hits fit inside one window of 2 x tolerance. Misses = tested
eclipses that do not hit. Intervals with up to --max-misses misses are reported.

Search: every implied interval (|D| <= --span years) from 4 reference eclipses that stay inside the test range for
the whole span is a candidate (with at most 3 misses, at least one of the 4 must hit, so no valid interval can be
skipped). Candidates are screened with 64 random eclipses, evaluated in full, re-evaluated centred on each band's
average, and duplicates (bands within 2 x tolerance) are merged.

Usage:
  python pattern/shared_intervals.py                       # the off-stride eclipses -> check against the published set
  python pattern/shared_intervals.py --eclipses "Null Tests/Test Eclipses/1 - Null Test 1 (All Eclipses) - Test Eclipses.csv"
Options: --tolerance DAYS (3.5)  --span YEARS (5000)  --max-misses N (3)  --out FILE.csv
Any input CSV with the columns "Cum. Seconds from -15000 Jan 01 00:00:00 TD", "Date" and "Direction" works.
Run time: several minutes.
"""
import argparse
import csv
import time
from collections import Counter
from pathlib import Path

import numpy as np

from common import DAY, YEAR, TEST_MIN, TEST_MAX, SIGN, CUM, OUT, ROOT, load_catalog, read_csv, load_intervals


def search(cat, c, sg, dates, tol=3.5 * DAY, span_years=5000, max_misses=3, log=print):
    win = 2 * tol
    span = span_years * YEAR
    near = win
    n = len(c)

    def implied(cc, ss, D):
        tgt = cc[:, None] + ss[:, None] * D[None, :]
        inr = (tgt >= TEST_MIN) & (tgt <= TEST_MAX)
        k = np.clip(np.searchsorted(cat, tgt), 1, len(cat) - 1)
        lo, hi = cat[k - 1], cat[k]
        e = np.where(np.abs(lo - tgt) <= np.abs(hi - tgt), lo, hi)
        d = ss[:, None] * (e - cc[:, None])
        bad = (np.abs(e - tgt) > near) | (e == cc[:, None])
        return np.where(bad, np.nan, d), inr

    def best_window(d, inr):
        k, m = d.shape
        v = np.where(inr, d, np.nan)
        ref = np.nanmedian(v, axis=0)
        ref = np.where(np.isnan(ref), 0.0, ref)
        x = v - ref[None, :]
        xs = np.sort(np.where(np.isnan(x), np.inf, x), axis=0)
        off = np.arange(m, dtype=np.float64)[None, :] * 1e7
        flat = (np.where(np.isinf(xs), 5e6, xs) + off).T.ravel()
        ends = np.searchsorted(flat, flat + win, side='right')
        cnt = ends - np.arange(len(flat))
        cnt = np.where((flat - np.repeat(off.ravel(), k)) >= 4e6, 0, cnt).reshape(m, k)
        bi = np.argmax(cnt, axis=1)
        best = cnt[np.arange(m), bi]
        wstart = xs.T[np.arange(m), bi]
        tested = inr.sum(axis=0)
        member = (x >= wstart[None, :]) & (x <= wstart[None, :] + win) & inr
        return tested - best, member, tested

    def evaluate(D, chunk=1000):
        out = []
        for a in range(0, len(D), chunk):
            Dc = D[a:a + chunk]
            d, inr = implied(c, sg, Dc)
            misses, member, tested = best_window(d, inr)
            for j in np.where(misses <= max_misses)[0]:
                vals = d[member[:, j], j]
                mag = np.abs(vals)
                out.append(dict(avg=float(vals.mean()), max=float(vals[np.argmax(mag)]), min=float(vals[np.argmin(mag)]),
                                std=float(vals.std(ddof=1)), tested=int(tested[j]), hits=int(member[:, j].sum()),
                                misses=int(misses[j]), missed=[dates[i] for i in np.where(inr[:, j] & ~member[:, j])[0]]))
        return out

    t0 = time.time()
    safe = np.where((c - span - 60 * DAY >= TEST_MIN) & (c + span + 60 * DAY <= TEST_MAX))[0]
    refs = safe[np.linspace(0, len(safe) - 1, max_misses + 1).astype(int)]
    cand = []
    for i in refs:
        dd = sg[i] * (cat - c[i])
        cand.append(dd[(np.abs(dd) <= span) & (np.abs(dd) > near)])
    cand = np.unique(np.round(np.concatenate(cand)))
    log(f'candidates {len(cand):,}')
    probes = np.random.default_rng(12345).choice(np.arange(n), size=min(64, n), replace=False)
    keep = np.zeros(len(cand), bool)
    for a in range(0, len(cand), 20000):
        d, inr = implied(c[probes], sg[probes], cand[a:a + 20000])
        keep[a:a + 20000] = (inr & np.isnan(d)).sum(axis=0) <= max_misses
    cand = cand[keep]
    log(f'after screening {len(cand):,}  ({time.time() - t0:.0f}s)')
    first = evaluate(cand)
    log(f'pass 1 kept {len(first):,}  ({time.time() - t0:.0f}s)')
    second = evaluate(np.array(sorted({round(r['avg']) for r in first}), dtype=np.float64))
    second.sort(key=lambda r: (r['avg'], r['misses']))
    final = []
    for r in second:
        if final and abs(r['avg'] - final[-1]['avg']) <= win:
            if (r['misses'], -r['hits']) < (final[-1]['misses'], -final[-1]['hits']):
                final[-1] = r
            continue
        final.append(r)
    log(f'final {len(final):,} intervals, by misses {sorted(Counter(r["misses"] for r in final).items())}  ({time.time() - t0:.0f}s)')
    return final


def write(final, path):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Average (Seconds)', 'Max (Seconds)', 'Min (Seconds)', 'Standard Deviation (Seconds)', '% Correct',
                    '# Missed', 'Eclipse #1 Missed', 'Eclipse #2 Missed', 'Eclipse #3 Missed', 'Average (Days)', 'Average (Years)'])
        for x in final:
            m = list(x['missed'][:3]) + [''] * 3
            w.writerow([f"{x['avg']:.1f}", f"{x['max']:.0f}", f"{x['min']:.0f}", f"{x['std']:.1f}",
                        f"{100 * x['hits'] / x['tested']:.2f}%", x['misses'], m[0], m[1], m[2],
                        f"{x['avg'] / DAY:.2f}", f"{x['avg'] / YEAR:.2f}"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--eclipses', default=str(OUT / 'Off-Stride Eclipses.csv'))
    ap.add_argument('--tolerance', type=float, default=3.5)
    ap.add_argument('--span', type=float, default=5000)
    ap.add_argument('--max-misses', type=int, default=3)
    ap.add_argument('--out', default='shared_intervals_result.csv')
    a = ap.parse_args()
    cat = load_catalog()['cum']
    p = Path(a.eclipses)
    rows = read_csv(p if p.is_absolute() else ROOT / p)
    c = np.array([float(r[CUM]) for r in rows])
    sg = np.array([SIGN[r['Direction']] for r in rows])
    final = search(cat, c, sg, [r['Date'] for r in rows], a.tolerance * DAY, a.span, a.max_misses)
    write(final, a.out)
    print('written', a.out)
    zero = np.array([x['avg'] for x in final if x['misses'] == 0])
    print(f'0 misses: {len(zero):,}, span {zero.min() / YEAR:,.0f} to {zero.max() / YEAR:+,.0f} years')
    pub = load_intervals()['avg']
    k = np.clip(np.searchsorted(pub, zero), 1, len(pub) - 1)
    close = np.minimum(np.abs(pub[k] - zero), np.abs(pub[k - 1] - zero))
    print(f'0-miss intervals within 1 day of an interval in Outputs/Off-Stride Shared Intervals.csv: '
          f'{int((close <= DAY).sum()):,}; not: {int((close > DAY).sum()):,}')


if __name__ == '__main__':
    main()
