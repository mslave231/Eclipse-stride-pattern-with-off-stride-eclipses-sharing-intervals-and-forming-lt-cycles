"""Reproduce the seven null tests (Null Tests/README.md; report Section 4.4).

Tests 1-6 draw 5,124 eclipses with the same Saros-position profile as the off-stride eclipses (tests 1-3 from all
eclipses, tests 4-6 from on-stride eclipses only); half of each bucket from the start side of a Saros series
(Direction A), half from the end side (Direction B). Test 7 draws 5,124 interior eclipses (at least 16 from both ends
of their Saros series) and lets the data choose each eclipse's direction. Only exact Saros counts are eligible.

Usage:
  python pattern/null_tests.py 1            # redraw test 1 from its seed and compare with the published Test Eclipses file
  python pattern/null_tests.py 1 --search   # ... and run the shared-interval search on it (several minutes)
  python pattern/null_tests.py 7 --search   # interior test: anchor directions, then the accept-only-if-better
                                            # refinement (each round is one search; expect an hour or more)
  python pattern/null_tests.py 2 --seed 123 # a new draw with another seed
"""
import argparse
from collections import Counter

import numpy as np

from common import DAY, YEAR, TEST_MIN, TEST_MAX, SIGN, CUM, ROOT, load_catalog, load_intervals, read_csv
from shared_intervals import search, write

TESTS = {1: ('1 - Null Test 1 (All Eclipses)', 3044065046, 'all'),
         2: ('2 - Null Test 2 (All Eclipses)', 3687402311, 'all'),
         3: ('3 - Null Test 3 (All Eclipses)', 1660353500, 'all'),
         4: ('4 - On-Stride Null 1 (On-Stride Eclipses Only)', 1316505538, 'onstride'),
         5: ('5 - On-Stride Null 2 (On-Stride Eclipses Only)', 727232544, 'onstride'),
         6: ('6 - On-Stride Null 3 (On-Stride Eclipses Only)', 4053479042, 'onstride'),
         7: ('7 - Interior Null 1 (Interior Eclipses, Data-Chosen Direction)', 1465772959, 'interior')}
PROFILE = {1: 1052, 2: 832, 3: 659, 4: 551, 5: 461, 6: 382, 7: 313, 8: 256, 9: 205, 10: 158, 11: 114, 12: 81,
           13: 40, 14: 15, 15: 4, 16: 1}      # off-stride eclipses per position from the nearer end of the series
TOL = 3.5 * DAY


def draw_profile(C, rng, onstride_only):
    n = len(C['cum'])
    on = np.array([r['Off-Stride Direction'] == '' for r in C['stride_rows']])
    pool = {(k, side): [i for i in range(n) if cnt[i] == k and not est[i] and (on[i] or not onstride_only)]
            for k in PROFILE for side, cnt, est in (('A', C['fwd'], C['fwd_est']), ('B', C['rev'], C['rev_est']))}
    used, sample = set(), []
    for k, m in PROFILE.items():
        nA, nB = m // 2, m - m // 2
        if m % 2 and rng.random() < 0.5:
            nA, nB = nB, nA
        for side, mm in (('A', nA), ('B', nB)):
            pick = rng.choice([i for i in pool[(k, side)] if i not in used], size=mm, replace=False)
            for i in sorted(int(x) for x in pick):
                used.add(i)
                sample.append((i, side))
    sample.sort(key=lambda s: C['cum'][s[0]])
    return [i for i, _ in sample], np.array([SIGN[d] for _, d in sample])


def hits_or_misses(cat, cc, s, D, count_hits):
    t = cc + s * D
    t = t[(t >= TEST_MIN) & (t <= TEST_MAX)]
    k = np.clip(np.searchsorted(cat, t), 1, len(cat) - 1)
    dl = np.minimum(np.abs(cat[k] - t), np.abs(cat[k - 1] - t))
    return int((dl <= TOL).sum()) if count_hits else int((dl > TOL).sum())


def draw_interior(C, rng):
    cat = C['cum']
    pool = [i for i in range(len(cat)) if C['fwd'][i] >= 16 and C['rev'][i] >= 16 and not C['fwd_est'][i] and not C['rev_est'][i]]
    pick = sorted(int(x) for x in rng.choice(pool, size=5124, replace=False))
    c = cat[pick]
    span = 5000 * YEAR
    mid = np.where((c - span >= TEST_MIN + 30 * DAY) & (c + span <= TEST_MAX - 30 * DAY))[0]
    a = int(mid[len(mid) // 2])                                   # anchor, fixed at Direction B
    Da = cat - c[a]
    Da = Da[(np.abs(Da) <= span) & (np.abs(Da) > 2 * TOL)]
    sg = np.ones(len(c))
    for i in range(len(c)):
        if i != a:
            sg[i] = 1.0 if hits_or_misses(cat, c[i], 1.0, Da, True) >= hits_or_misses(cat, c[i], -1.0, Da, True) else -1.0
    print(f'interior pool {len(pool):,}; anchor {C["date"][pick[a]]}; anchor directions A {int((sg < 0).sum()):,}, B {int((sg > 0).sum()):,}')
    return pick, sg


def refine(cat, c, sg, dates, quiet):
    """Flip eclipses that would miss fewer shared intervals facing the other way; keep a batch only if the search
    finds more 0-miss intervals (else try the strongest quarter); stop when neither improves."""
    final = search(cat, c, sg, dates, TOL, log=quiet)
    zero = sum(x['misses'] == 0 for x in final)
    print(f'round 1 (anchor directions): {zero:,} intervals with 0 misses')
    rnd = 1
    while True:
        rnd += 1
        D = np.array([x['avg'] for x in final])
        gain = np.array([hits_or_misses(cat, c[i], sg[i], D, False) - hits_or_misses(cat, c[i], -sg[i], D, False) for i in range(len(c))])
        cand = np.where(gain > 0)[0]
        if len(cand) == 0:
            return sg, final
        improved = False
        for frac in (1.0, 0.25):
            sel = cand[np.argsort(-gain[cand])][:max(1, int(len(cand) * frac))]
            trial = sg.copy(); trial[sel] *= -1
            ft = search(cat, c, trial, dates, TOL, log=quiet)
            zt = sum(x['misses'] == 0 for x in ft)
            print(f'round {rnd}: flip {len(sel)} -> {zt:,} intervals with 0 misses ({"kept" if zt > zero else "rejected"})')
            if zt > zero:
                sg, final, zero, improved = trial, ft, zt, True
                break
        if not improved:
            return sg, final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('test', type=int, choices=range(1, 8))
    ap.add_argument('--seed', type=int)
    ap.add_argument('--search', action='store_true')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    label, seed, kind = TESTS[a.test]
    seed = a.seed if a.seed is not None else seed
    C = load_catalog()
    cat = C['cum']
    rng = np.random.default_rng(seed)
    pick, sg = draw_interior(C, rng) if kind == 'interior' else draw_profile(C, rng, kind == 'onstride')
    c, dates = cat[pick], [C['date'][i] for i in pick]
    offs = sum(C['stride_rows'][i]['Off-Stride Direction'] != '' for i in pick)
    print(f'test {a.test} seed {seed}: drew {len(pick):,} eclipses ({offs} off-stride)')

    if seed == TESTS[a.test][1]:
        pub = read_csv(ROOT / 'Null Tests' / 'Test Eclipses' / f'{label} - Test Eclipses.csv')
        same = [float(r[CUM]) for r in pub] == list(c)
        print('same eclipses as the published Test Eclipses file:', same)
        if kind != 'interior':
            print('same directions:', [SIGN[r['Direction']] for r in pub] == list(sg))

    if a.search:
        quiet = lambda *x: None
        if kind == 'interior':
            sg, final = refine(cat, c, sg, dates, quiet)
            if seed == TESTS[a.test][1]:
                print('final directions same as the published file:', [SIGN[r['Direction']] for r in pub] == list(sg))
        else:
            final = search(cat, c, sg, dates, TOL)
        print('intervals by misses:', sorted(Counter(x['misses'] for x in final).items()))
        zero = np.array(sorted(x['avg'] for x in final if x['misses'] == 0))
        pub_i = load_intervals()['avg']
        k = np.clip(np.searchsorted(pub_i, zero), 1, len(pub_i) - 1)
        close = np.minimum(np.abs(pub_i[k] - zero), np.abs(pub_i[k - 1] - zero)) <= DAY
        print(f'0 misses: {len(zero):,}, span {zero.min() / YEAR:,.0f} to {zero.max() / YEAR:+,.0f} years; '
              f'also in the off-stride shared interval set {int(close.sum()):,}; not {int((~close).sum()):,}')
        if a.out:
            write(sorted(final, key=lambda x: x['avg']), a.out)
            print('written', a.out)


if __name__ == '__main__':
    main()
