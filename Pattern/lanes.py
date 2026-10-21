"""Walk the 12 stride lanes and derive the on-stride / off-stride split (report Section 3).

Rule: from an eclipse, step 694 days; if an eclipse lies within the tolerance (default +/-1.5 days) of that
point it is the next step, otherwise step 1,019 days. Forward lanes walk forward in time from their starting
eclipse, backward lanes walk backward. The 12 starting eclipses (identified as described in report Section 3.2)
are listed in LANE_STARTS. An eclipse on at least one lane is on-stride; an eclipse on no lane is off-stride.

Usage:  python pattern/lanes.py [--tolerance DAYS] [--check-tolerances]
Checks the result against Outputs/694-1,019 Stride Calculation.csv and Outputs/Off-Stride Eclipses.csv and
prints the stride statistics of report Table 2.
"""
import argparse

import numpy as np

from common import DAY, CYCLE_YEAR, OUT, CUM, load_catalog, read_csv

LANE_STARTS = {     # lane: cumulative seconds of its starting eclipse
    'Forward Stride 1': 56881705378,    # -13198 Jun 22 01:42:58 (solar)
    'Forward Stride 2': 56895781737,    # -13198 Dec 01 23:48:57 (lunar)
    'Forward Stride 3': 56897002784,    # -13198 Dec 16 02:59:44 (solar)
    'Forward Stride 4': 56910997094,    # -13197 May 27 02:18:14 (lunar)
    'Forward Stride 5': 56912341715,    # -13197 Jun 11 15:48:35 (solar)
    'Forward Stride 6': 56926408152,    # -13197 Nov 21 11:09:12 (lunar)
    'Backward Stride 1': 1015815845397,  # 17189 Aug 10 20:09:57 (solar)
    'Backward Stride 2': 1015800585055,  # 17189 Feb 15 05:10:55 (solar)
    'Backward Stride 3': 1015786552656,  # 17188 Sep 05 19:17:36 (lunar)
    'Backward Stride 4': 1015785208223,  # 17188 Aug 21 05:50:23 (solar)
    'Backward Stride 5': 1015771179214,  # 17188 Mar 11 20:53:34 (lunar)
    'Backward Stride 6': 1015769974579,  # 17188 Feb 26 22:16:19 (solar)
}


def walk(cat, start_idx, sign, tol):
    """Indices visited by a lane, and the stride (694 or 1019) used for each step."""
    path, strides, i = [start_idx], [], start_idx
    while True:
        nxt = None
        for d in (694, 1019):
            t = cat[i] + sign * d * DAY
            k = np.searchsorted(cat, t)
            for j in (k - 1, k):
                if 0 <= j < len(cat) and abs(cat[j] - t) <= tol:
                    nxt = j
                    break
            if nxt is not None:
                strides.append(d)
                break
        if nxt is None:
            return path, strides
        path.append(nxt)
        i = nxt


def lanes(cat, tol_days):
    idx = {c: i for i, c in enumerate(cat)}
    out = {}
    for name, c in LANE_STARTS.items():
        sign = 1 if name.startswith('Forward') else -1
        out[name] = walk(cat, idx[c], sign, tol_days * DAY)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tolerance', type=float, default=1.5, help='stride tolerance in days (default 1.5)')
    ap.add_argument('--check-tolerances', action='store_true', help='also confirm the same split for 1.5-3.5 days')
    a = ap.parse_args()
    C = load_catalog()
    cat = C['cum']
    L = lanes(cat, a.tolerance)
    on = set().union(*[set(p) for p, _ in L.values()])
    off = sorted(set(range(len(cat))) - on)
    print(f'tolerance +/-{a.tolerance} days: on-stride {len(on):,}  off-stride {len(off):,}')

    # --- compare with the published files
    stride = C['stride_rows']
    for name, (p, _) in L.items():
        published = {i for i, r in enumerate(stride) if r[name]}
        print(f'  {name}: {len(p):,} eclipses, matches published lane column: {set(p) == published}')
    pub_off = {int(r[CUM]) for r in read_csv(OUT / 'Off-Stride Eclipses.csv')}
    print('off-stride set matches Outputs/Off-Stride Eclipses.csv:', {int(cat[i]) for i in off} == pub_off)

    # --- report Table 2
    n694 = sum(s.count(694) for _, s in L.values()); n1019 = sum(s.count(1019) for _, s in L.values())
    runs_steps, runs_years = [], []
    for name, (p, s) in L.items():
        big = [k for k, d in enumerate(s) if d == 1019]
        for a1, b1 in zip(big, big[1:]):
            runs_steps.append(b1 - a1 - 1)
            runs_years.append(abs(cat[p[b1]] - cat[p[a1 + 1]]) / CYCLE_YEAR)
    rs, ry = np.array(runs_steps), np.array(runs_years)
    print(f'steps: {n694:,} of 694 days, {n1019:,} of 1,019 days; runs between 1,019-day steps: {len(rs):,}')
    print(f'run length (steps): min {rs.min()} max {rs.max()} mean {rs.mean():.1f} median {np.median(rs):.0f}')
    print(f'run length (years): min {ry.min():.1f} max {ry.max():.1f} mean {ry.mean():.1f} median {np.median(ry):.1f}')

    if a.check_tolerances:
        base = set(off)
        for t in (1.5, 2.0, 2.5, 3.0, 3.5):
            Lt = lanes(cat, t)
            o = set(range(len(cat))) - set().union(*[set(p) for p, _ in Lt.values()])
            print(f'  tolerance +/-{t} days: off-stride {len(o):,}, identical set: {o == base}')


if __name__ == '__main__':
    main()
