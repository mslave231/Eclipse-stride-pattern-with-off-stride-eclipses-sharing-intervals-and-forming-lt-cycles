"""Add six eclipse-geometry columns, in place, to Outputs/eclipse_catalog_full_-13198_17189_detailed.csv,
Outputs/694-1,019 Stride Calculation.csv and Outputs/Off-Stride Eclipses.csv, computed from the JPL DE441
ephemeris at each eclipse's instant of greatest eclipse (Date + TD of GE from the catalog). No Saros
numbers, gamma or other catalog values are used as input. The stride and off-stride files receive the
catalog's values, matched on Date (year compared as a number) + TD of GE; every row must match.

  Sun-Node Distance (deg)       Sun's ecliptic longitude minus the longitude of the Moon's node,
                                folded to -90..+90. Negative = the Sun has not yet reached the node
                                (opening side of the eclipse window); positive = past it (closing
                                side). The node is the Moon's osculating (instantaneous) node on the
                                ecliptic of date (plane of the Earth-Moon barycentre's orbit).
  Moon Horizontal Parallax (')  asin(6378.1366 km / Earth-Moon distance), in arcminutes.
  Earth-Moon Distance (km)      Geocentric, centre to centre.
  Earth-Sun Distance (AU)       Earth centre to Sun centre; 1 AU = 149,597,870.7 km.
  Moon Mean Anomaly (deg)       Moon's mean position in its distance cycle: 0 = mean perigee,
                                180 = mean apogee, increasing uniformly through each anomalistic month.
  Earth Mean Anomaly (deg)      Earth's mean position in its orbit measured from perihelion:
                                0 = mean perihelion, 180 = mean aphelion (Earth-Moon barycentre).

The mean anomalies are taken from DE441 itself rather than from the textbook polynomials: every
perigee of the Moon (402,839) and every perihelion of the Earth-Moon barycentre (30,389) in the
ephemeris is found, and a smooth curve (degree-6 Chebyshev fit of passage number against time)
is fitted through them. The fit averages out the perturbations that shift individual passages
(rms 16 deg for perigees, 0.09 deg for perihelia), leaving the uniformly advancing mean anomaly.
It agrees with Meeus (Astronomical Algorithms, Ch. 47 and 25) to 0.01 deg from -1000 to +5000.

Positions are geometric (no light-time or aberration). Re-running replaces the six columns.
Needs de441.bsp (set ECLIPSE_EPH to its path; default ./de441.bsp) and jplephem.
Writes atomically via a temp file + os.replace."""
import csv, math, os
import numpy as np
from numpy.polynomial import chebyshev
from jplephem.spk import SPK

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Outputs')
CAT = os.path.join(OUT, 'eclipse_catalog_full_-13198_17189_detailed.csv')
ALSO = [os.path.join(OUT, '694-1,019 Stride Calculation.csv'), os.path.join(OUT, 'Off-Stride Eclipses.csv')]
EPH = os.environ.get('ECLIPSE_EPH', 'de441.bsp')
R_EARTH_KM, AU_KM = 6378.1366, 149597870.7
NEW = ['Sun-Node Distance (deg)', "Moon Horizontal Parallax (')",
       'Earth-Moon Distance (km)', 'Earth-Sun Distance (AU)',
       'Moon Mean Anomaly (deg)', 'Earth Mean Anomaly (deg)']
MONTHS = {m: i + 1 for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}

def cal_to_jd(y, m, d):
    """JD at 0h of a calendar date: Julian before 1582 Oct 15, Gregorian after (Meeus Ch. 7)."""
    if m <= 2:
        y, m = y - 1, m + 12
    b = 0
    if (y, m, d) >= (1582, 10, 15):
        a = math.floor(y / 100); b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5

def row_jd(date, td):                    # '-13198 Jun 06', '22:21:03' -> JD (TD)
    p = date.split(); h, mi, s = (int(x) for x in td.split(':'))
    return cal_to_jd(int(p[0]), MONTHS[p[1]], int(p[2])) + (h + mi / 60 + s / 3600) / 24

kernel = SPK.open(EPH)
def state(center, target, jd):
    """Position (km) and velocity (km/day) from whichever DE441 segment covers each time."""
    pos, vel = np.empty((3, jd.size)), np.empty((3, jd.size)); done = np.zeros(jd.size, bool)
    for seg in kernel.segments:
        if seg.center == center and seg.target == target:
            m = (~done) & (jd >= seg.start_jd) & (jd <= seg.end_jd)
            if m.any():
                pos[:, m], vel[:, m] = seg.compute_and_differentiate(jd[m]); done |= m
    assert done.all(), f'times outside {EPH} for {center}->{target}'
    return pos, vel

def unit(v):
    return v / np.linalg.norm(v, axis=0)

def radial(center, target, origin):
    """r.v of target relative to origin (both seen from center); zero at each distance extreme."""
    def f(jd):
        a, av = state(center, target, jd); b, bv = state(center, origin, jd)
        return ((a - b) * (av - bv)).sum(0)
    return f

def passages(f, step, chunk):
    """Times of every distance minimum (r.v turning - to +), bisected to ~1e-6 day."""
    segs = [s for s in kernel.segments if (s.center, s.target) == (3, 301)]
    j0, j1 = min(s.start_jd for s in segs) + 1, max(s.end_jd for s in segs) - 1
    out = []
    for a in np.arange(j0, j1, chunk):
        t = np.arange(a, min(a + chunk + step, j1), step); g = f(t)
        i = np.where((g[:-1] < 0) & (g[1:] >= 0))[0]
        lo, hi = t[i], t[i + 1]
        for _ in range(40):
            mid = (lo + hi) / 2; neg = f(mid) < 0
            lo, hi = np.where(neg, mid, lo), np.where(neg, hi, mid)
        out.append((lo + hi) / 2)
    return np.unique(np.round(np.concatenate(out), 6))

def mean_anomaly(times, deg=6):
    """Mean anomaly (deg) as a function of JD, from a smooth fit through the passage times."""
    a, b = times[0], times[-1]
    scale = lambda jd: (jd - (a + b) / 2) / ((b - a) / 2)
    c = chebyshev.chebfit(scale(times), np.arange(times.size, dtype=float), deg)
    return lambda jd: (chebyshev.chebval(scale(jd), c) % 1.0) * 360.0

def read_without_new(path):
    """Header and rows of a CSV with any existing geometry columns dropped (so re-runs replace them)."""
    with open(path, newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    keep = [i for i, h in enumerate(header) if h not in NEW]
    return [header[i] for i in keep], [[r[i] for i in keep] for r in rows]

def write_with_new(path, header, rows, values):
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(header + NEW)
        for r, v in zip(rows, values):
            w.writerow(r + v)
    os.replace(tmp, path)

def key(date, td):
    """Match key that ignores year padding ('-999 Mar 14' in the catalog = '-0999 Mar 14' elsewhere)."""
    y, mon, d = date.split()
    return int(y), mon, int(d), td

header, rows = read_without_new(CAT)
iD, iT = header.index('Date'), header.index('TD of GE')
jd = np.array([row_jd(r[iD], r[iT]) for r in rows])

emb, embv = state(0, 3, jd)        # SSB -> Earth-Moon barycentre
sun, sunv = state(0, 10, jd)       # SSB -> Sun
moo, moov = state(3, 301, jd)      # EMB -> Moon
ear, earv = state(3, 399, jd)      # EMB -> Earth

pole = unit(np.cross((emb - sun).T, (embv - sunv).T).T)                   # ecliptic of date
node = unit(np.cross(pole.T, np.cross((moo - ear).T, (moov - earv).T)).T)  # Moon's ascending node
sun_geo = sun - (emb + ear)
s_ecl = unit(sun_geo - pole * (pole * sun_geo).sum(0))
lam = np.degrees(np.arctan2((pole * np.cross(node.T, s_ecl.T).T).sum(0), (node * s_ecl).sum(0)))
sun_node = (lam + 90) % 180 - 90
moon_km = np.linalg.norm(moo - ear, axis=0)
parallax = np.degrees(np.arcsin(R_EARTH_KM / moon_km)) * 60
sun_au = np.linalg.norm(sun_geo, axis=0) / AU_KM
perigees = passages(radial(3, 301, 399), 0.5, 365.25 * 500)       # Moon about Earth
perihelia = passages(radial(0, 3, 10), 5.0, 365.25 * 2000)        # EMB about Sun
moon_ma = mean_anomaly(perigees)(jd)
earth_ma = mean_anomaly(perihelia)(jd)

values = [[f'{a:+.4f}', f'{b:.4f}', f'{c:.1f}', f'{d:.7f}', f'{e:.4f}', f'{g:.4f}']
          for a, b, c, d, e, g in zip(sun_node, parallax, moon_km, sun_au, moon_ma, earth_ma)]
write_with_new(CAT, header, rows, values)
by_key = {key(r[iD], r[iT]): v for r, v in zip(rows, values)}
assert len(by_key) == len(rows), 'Date + TD of GE is not unique in the catalog'
for path in ALSO:
    h, rs = read_without_new(path)
    jD, jT = h.index('Date'), h.index('TD of GE')
    missing = [r[jD] + ' ' + r[jT] for r in rs if key(r[jD], r[jT]) not in by_key]
    assert not missing, f'{os.path.basename(path)}: {len(missing)} rows not in the catalog, e.g. {missing[:3]}'
    write_with_new(path, h, rs, [by_key[key(r[jD], r[jT])] for r in rs])
    print(f'{os.path.basename(path)}: {len(rs)} rows')
print(f'{len(rows)} rows; Sun-node {sun_node.min():+.3f}..{sun_node.max():+.3f} deg; '
      f'parallax {parallax.min():.2f}..{parallax.max():.2f}\'; '
      f'Moon {moon_km.min():,.0f}..{moon_km.max():,.0f} km; Sun {sun_au.min():.5f}..{sun_au.max():.5f} AU; '
      f'{perigees.size} perigees, {perihelia.size} perihelia')
