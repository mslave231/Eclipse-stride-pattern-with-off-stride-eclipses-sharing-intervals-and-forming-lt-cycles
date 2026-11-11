"""Missing half-octon eclipses: the empty new/full moons that link each off-stride chain to the on-stride lanes.

Off-stride chains are runs of off-stride eclipses linked by a half octon (23.5 lunations = 47 new/full moons).
  Direction A: from the FIRST eclipse of each chain, step back 47 new/full moons at a time until an eclipse on a
               FORWARD lane is reached. Every empty step (no eclipse at that new/full moon) is a missing eclipse.
  Direction B: from the LAST eclipse of each chain, step forward 47 at a time until an eclipse on a BACKWARD lane
               is reached. Every empty step is a missing eclipse.
A new/full moon reached from two chains of the same direction is listed once, credited to the earlier chain. A walk
that leaves the catalog or takes more than 40 steps without reaching a lane is dropped.

Each missing eclipse is timed EXACTLY: the true new/full moon is solved from DE441 until the Moon-Sun elongation is
below 1e-7 deg (~0.001 s; the floating-point limit is ~2e-8 deg), then rounded to the whole TD second like the catalog. New/full moon = the Moon's and
Sun's geocentric geometric ecliptic longitudes are equal / 180 deg apart, measured in the ecliptic of date (the
instantaneous orbital plane of the Earth-Moon barycentre). This is the same geometric convention as every other
geometry column; the almanac (apparent) new/full moon falls ~40 s earlier.

Columns (Outputs/Missing Half Octon Eclipses.csv)
  Date, TD of New/Full Moon        calendar date and TD of the true new/full moon (Julian before 1582 Oct 15)
  Cum. Seconds from -15000 ...     whole TD seconds from -15000 Jan 01 00:00:00 TD, same as every other file
  Solar or Lunar                   new moon = Solar slot, full moon = Lunar slot
  Direction                        direction of the off-stride chain the slot links
  Moon-Node Distance (deg)         the Moon's angular distance from its ascending or descending node, measured
                                   along its orbit, -90..+90 (osculating node on the ecliptic of date)
  Moon Distance (mean = 1)         Earth-Moon distance / 385,000.6 km (Meeus's mean distance)
  Strides from Off-Stride Eclipse  half-octon steps from the chain's end eclipse
  Off-Stride Eclipse Linked        date of that off-stride eclipse
  Lane Eclipse Linked              date of the lane eclipse where the walk ends
  In Near-Miss List                Yes = within 1.5 days of one of the matching near-misses in
                                   Outputs/All Eclipses and Near-Miss Eclipses Matching All Off-Stride Shared Intervals.csv
  the eight geometry columns       exactly as in the catalog (Pipeline/add_geometry.py), at the new/full moon
  Sun Mean Anomaly, Osculating (deg, 0-360 from perihelion)
                                   mean anomaly of the osculating heliocentric orbit of the Earth-Moon barycentre

Inputs: Outputs/Stride Calculation.csv and the near-miss file above. Needs de441.bsp (ECLIPSE_EPH) and jplephem.
Usage:  python Pattern/missing_half_octon.py         (~3 min: the mean-anomaly fits find every perigee/perihelion)
"""
import csv, math, os, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'Pipeline'))
import add_geometry as G                                   # noqa: E402  (exact catalog geometry)
from common import OUT, CUM, DAY, read_csv                 # noqa: E402

JD0 = -3757692.5                       # -15000 Jan 01 00:00 TD (Julian calendar)
HALF_LUNATION = 29.530588853 / 2       # days; only used to count new/full moons between eclipses
STEP, MAX_STEPS = 47, 40               # half octon = 47 new/full moons
MOON_MEAN_KM = 385000.6                # Meeus, Astronomical Algorithms, Ch. 47
NEAR_MISS_DAYS = 1.5
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
DEST = OUT / 'Missing Half Octon Eclipses.csv'
HEADER = ['Date', 'TD of New/Full Moon', CUM, 'Solar or Lunar', 'Direction', 'Moon-Node Distance (deg)',
          'Moon Distance (mean = 1)', 'Strides from Off-Stride Eclipse', 'Off-Stride Eclipse Linked',
          'Lane Eclipse Linked', 'In Near-Miss List'] + G.NEW + ['Sun Mean Anomaly, Osculating (deg, 0-360 from perihelion)']


def frame(jd):
    """Ecliptic of date (pole of the barycentre's heliocentric orbit), geocentric Moon and Sun, Moon velocity."""
    emb, embv = G.state(0, 3, jd); sun, sunv = G.state(0, 10, jd)
    moo, moov = G.state(3, 301, jd); ear, earv = G.state(3, 399, jd)
    pole = G.unit(np.cross((emb - sun).T, (embv - sunv).T).T)
    return pole, moo - ear, moov - earv, sun - (emb + ear), emb - sun, embv - sunv


def elongation(jd):
    """Moon minus Sun longitude in the ecliptic of date (deg, -180..180)."""
    pole, rm, _, rs, _, _ = frame(jd)
    x1 = G.unit(np.cross(pole.T, np.tile([1.0, 0, 0], (jd.size, 1))).T); x2 = np.cross(pole.T, x1.T).T
    lon = lambda x: np.arctan2((x * x2).sum(0), (x * x1).sum(0))
    return (np.degrees(lon(rm) - lon(rs)) + 180) % 360 - 180


def solve_syzygy(seed, full):
    """Exact new (full=False) / full (full=True) moon nearest each seed JD."""
    j = seed.astype(float).copy(); target = np.where(full, 180.0, 0.0)
    for _ in range(80):
        d = (elongation(j) - target + 180) % 360 - 180
        if np.abs(d).max() < 1e-7:
            break
        j -= d / 12.1907                                     # mean elongation rate, deg/day (converges linearly)
    d = (elongation(j) - target + 180) % 360 - 180
    assert np.abs(d).max() < 1e-7, f'syzygy not converged: {np.abs(d).max()} deg'
    assert np.abs(j - seed).max() < 3, 'syzygy solution wandered from its seed'
    return j


def date_time(cum_s):
    """Whole TD seconds from JD0 -> ('-0997 Jan 23', '03:09:59'); Julian before 1582 Oct 15 (Meeus Ch. 7)."""
    day, sec = divmod(int(cum_s), 86400)
    Z = int(JD0 + 0.5) + day
    A = Z if Z < 2299161 else Z + 1 + (al := math.floor((Z - 1867216.25) / 36524.25)) - math.floor(al / 4)
    B = A + 1524; C = math.floor((B - 122.1) / 365.25); D = math.floor(365.25 * C); E = math.floor((B - D) / 30.6001)
    d = B - D - math.floor(30.6001 * E); m = E - 1 if E < 14 else E - 13; y = C - 4716 if m > 2 else C - 4715
    ys = f'-{abs(y):04d}' if y < 0 else f'{y:04d}'
    return f'{ys} {MONTHS[m - 1]} {d:02d}', f'{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}'


def osculating_mean_anomaly(r, v):
    """Mean anomaly (deg, 0-360) of the osculating orbit from position r (km) and velocity v (km/day)."""
    gm = G.GM_SUN + G.GM_EARTH + G.GM_MOON; v = v / 86400.0
    h = np.cross(r.T, v.T).T
    ev = np.cross(v.T, h.T).T / gm - r / np.linalg.norm(r, axis=0); e = np.linalg.norm(ev, axis=0)
    nu = np.arctan2((np.cross(ev.T, r.T).T * G.unit(h)).sum(0), (ev * r).sum(0))
    E = 2 * np.arctan(np.sqrt((1 - e) / (1 + e)) * np.tan(nu / 2))
    return np.degrees(E - e * np.sin(E)) % 360.0


def main():
    rows = read_csv(OUT / 'Stride Calculation.csv')
    t = np.array([int(r[CUM]) for r in rows], dtype=np.float64) / DAY + JD0
    # new/full-moon index of every eclipse: count half lunations between consecutive eclipses (never more than
    # a few months apart, so the rounding is unambiguous); solar eclipses must all land on even indices
    gaps = np.diff(t) / HALF_LUNATION
    assert np.abs(gaps - np.round(gaps)).max() < 0.3
    n = np.concatenate([[0], np.cumsum(np.round(gaps).astype(int))])
    solar = np.array([r['Solar or Lunar'] == 'Solar' for r in rows])
    parity = n[solar][0] % 2
    assert (n[solar] % 2 == parity).all() and (n[~solar] % 2 != parity).all(), 'new/full-moon index parity check failed'
    pos = {int(v): i for i, v in enumerate(n)}
    on_fwd = np.array([any(r[f'Forward Stride {k}'] for k in range(1, 7)) for r in rows])
    on_bwd = np.array([any(r[f'Backward Stride {k}'] for k in range(1, 7)) for r in rows])
    od = np.array([r['Off-Stride Direction'] for r in rows])

    links, chains, unresolved = {}, 0, 0
    for d, step, lane in (('A', -STEP, on_fwd), ('B', STEP, on_bwd)):
        for i in np.where(od == d)[0]:
            if int(n[i]) + step in pos:                     # not the end of its chain on this side
                continue
            chains += 1
            k, miss, hit = int(n[i]), [], -1
            for s in range(1, MAX_STEPS + 1):
                k += step
                if k < n[0] or k > n[-1]:
                    break
                j = pos.get(k)
                if j is None:
                    miss.append((k, s))
                elif lane[j]:
                    hit = j
                    break
            if hit < 0:
                unresolved += 1
                continue
            for k_, s in miss:
                links.setdefault((k_, d), (i, hit, s))
    keys = sorted(links, key=lambda kd: kd[0])
    kn = np.array([k for k, _ in keys])
    full = (kn % 2) != parity
    seed = np.interp(kn, n, t)                              # nearest eclipses bracket each slot
    j = solve_syzygy(seed, full)
    cum = np.round((j - JD0) * DAY)                         # whole TD seconds, as in the catalog
    jr = cum / DAY + JD0                                    # geometry at the rounded instant, like the catalog

    pole, rm, vm, _, re_, ve = frame(jr)
    hm = np.cross(rm.T, vm.T).T; node = G.unit(np.cross(pole.T, hm.T).T)
    u = np.degrees(np.arctan2((np.cross(node.T, rm.T).T * G.unit(hm)).sum(0), (node * rm).sum(0)))
    moon_node = (u + 90) % 180 - 90
    moon_rel = np.linalg.norm(rm, axis=0) / MOON_MEAN_KM
    osc_ma = osculating_mean_anomaly(re_, ve)
    geo = G.format_geometry(G.geometry(jr))
    nm = np.sort([float(r[CUM]) / DAY for r in read_csv(OUT / 'All Eclipses and Near-Miss Eclipses Matching All '
                  'Off-Stride Shared Intervals.csv') if r['Category'] == 'Matching eclipse near-miss'])

    out = []
    for q, (k, d) in enumerate(keys):
        i, h, s = links[(k, d)]
        p = np.clip(np.searchsorted(nm, cum[q] / DAY), 1, len(nm) - 1)
        near = min(abs(nm[p] - cum[q] / DAY), abs(nm[p - 1] - cum[q] / DAY)) <= NEAR_MISS_DAYS
        dt, tm = date_time(cum[q])
        out.append([dt, tm, int(cum[q]), 'Lunar' if full[q] else 'Solar', d, f'{moon_node[q]:.3f}',
                    f'{moon_rel[q]:.4f}', s, rows[i]['Date'], rows[h]['Date'], 'Yes' if near else 'No']
                   + geo[q] + [G.deg360(osc_ma[q])])
    out.sort(key=lambda r: (r[2], r[4]))
    tmp = str(DEST) + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(HEADER); w.writerows(out)
    os.replace(tmp, DEST)
    print(f'chains {chains}; unresolved {unresolved}; missing half-octon eclipses {len(out)} '
          f'(A {sum(r[4] == "A" for r in out)}, B {sum(r[4] == "B" for r in out)}); '
          f'in near-miss list {sum(r[10] == "Yes" for r in out)} -> {DEST.name}')


if __name__ == '__main__':
    main()
