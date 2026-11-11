"""Add eight eclipse-geometry columns, in place, to Outputs/eclipse_catalog_full_-13198_17189_detailed.csv,
Outputs/Stride Calculation.csv and Outputs/Off-Stride Eclipses.csv, computed from the JPL DE441
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
  Sun True Anomaly (deg, 0-360 from perihelion)
                                The Sun's precise position in Earth's orbit: the actual angle, seen
                                from the Sun, between perihelion and the Earth-Moon barycentre, 0-360
                                (0 = perihelion, 180 = aphelion). Osculating heliocentric orbit of the
                                barycentre, GM = Sun + Earth + Moon. Identical to JPL Horizons' TA for
                                target 3 (Earth-Moon barycentre), centre 500@10 (Sun).
  Moon True Anomaly (deg, 0-360 from perigee)
                                The Moon's precise position in its orbit: the actual angle, seen from
                                Earth's centre, between perigee and the Moon, 0-360 (0 = perigee,
                                180 = apogee). Osculating geocentric orbit, GM = Earth + Moon.
                                Identical to JPL Horizons' TA for target 301 (Moon), centre 500@399.

The true anomalies are where each body actually is; the mean anomalies are where it would be if it
moved uniformly. They differ by the equation of centre (up to ~2 deg for the Sun, ~6-15 deg for the
Moon). The barycentre, not Earth's centre, is used for the Sun because Earth's monthly wobble about
the barycentre swings the osculating perihelion by up to ~3 deg; the Sun's direction from the two
points differs by under 0.002 deg. The Moon's osculating perigee is pulled back and forth by the Sun
(up to ~35 deg within a month), so its true anomaly is measured from the instantaneous perigee.

The mean anomalies are taken from DE441 itself rather than from the textbook polynomials: every
perigee of the Moon (402,839) and every perihelion of the Earth-Moon barycentre (30,389) in the
ephemeris is found, and a smooth curve (degree-6 Chebyshev fit of passage number against time)
is fitted through them. The fit averages out the perturbations that shift individual passages
(rms 16 deg for perigees, 0.09 deg for perihelia), leaving the uniformly advancing mean anomaly.
It agrees with Meeus (Astronomical Algorithms, Ch. 47 and 25) to 0.01 deg from -1000 to +5000.

Positions are geometric (no light-time or aberration). Re-running replaces the eight columns. The catalog also
gets the Cum. Seconds from -15000 Jan 01 00:00:00 TD column after TD of GE (added once, if missing).
Needs de441.bsp (set ECLIPSE_EPH to its path; default ./de441.bsp) and jplephem.
Writes atomically via a temp file + os.replace. Other scripts import geometry() / format_geometry() so
that every output file uses exactly this code (Pattern/missing_half_octon.py does)."""
import csv, math, os
import numpy as np
from numpy.polynomial import chebyshev
from jplephem.spk import SPK

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Outputs')
CAT = os.path.join(OUT, 'eclipse_catalog_full_-13198_17189_detailed.csv')
ALSO = [os.path.join(OUT, 'Stride Calculation.csv'), os.path.join(OUT, 'Off-Stride Eclipses.csv')]
EPH = os.environ.get('ECLIPSE_EPH', 'de441.bsp')
R_EARTH_KM, AU_KM = 6378.1366, 149597870.7
CUM, JD0 = 'Cum. Seconds from -15000 Jan 01 00:00:00 TD', -3757692.5      # JD0 = -15000 Jan 01 00:00 TD
GM_SUN, GM_EARTH, GM_MOON = 132712440041.279419, 398600.435507, 4902.800118   # DE441, km^3/s^2
NEW = ['Sun-Node Distance (deg)', "Moon Horizontal Parallax (')",
       'Earth-Moon Distance (km)', 'Earth-Sun Distance (AU)',
       'Moon Mean Anomaly (deg)', 'Earth Mean Anomaly (deg)',
       'Sun True Anomaly (deg, 0-360 from perihelion)', 'Moon True Anomaly (deg, 0-360 from perigee)']
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

def true_anomaly(r, v, gm):
    """Osculating true anomaly (deg, 0-360) from relative position r (km) and velocity v (km/day)."""
    v = v / 86400.0
    h = np.cross(r.T, v.T).T
    ecc = np.cross(v.T, h.T).T / gm - r / np.linalg.norm(r, axis=0)   # eccentricity vector, points to periapsis
    nu = np.arctan2((np.cross(ecc.T, r.T).T * unit(h)).sum(0), (ecc * r).sum(0))
    return np.degrees(nu) % 360.0

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

_fits = {}
def mean_anomaly_fits():
    """(Moon, Earth) mean-anomaly functions, from every DE441 perigee and perihelion (found once, ~2 min)."""
    if not _fits:
        _fits['perigees'] = passages(radial(3, 301, 399), 0.5, 365.25 * 500)       # Moon about Earth
        _fits['perihelia'] = passages(radial(0, 3, 10), 5.0, 365.25 * 2000)        # EMB about Sun
        _fits['moon'] = mean_anomaly(_fits['perigees'])
        _fits['earth'] = mean_anomaly(_fits['perihelia'])
    return _fits['moon'], _fits['earth']

def geometry(jd):
    """The eight geometry columns (unrounded numpy arrays, in NEW order) at each JD (TT)."""
    emb, embv = state(0, 3, jd)        # SSB -> Earth-Moon barycentre
    sun, sunv = state(0, 10, jd)       # SSB -> Sun
    moo, moov = state(3, 301, jd)      # EMB -> Moon
    ear, earv = state(3, 399, jd)      # EMB -> Earth
    pole = unit(np.cross((emb - sun).T, (embv - sunv).T).T)                   # ecliptic of date
    node = unit(np.cross(pole.T, np.cross((moo - ear).T, (moov - earv).T)).T)  # Moon's ascending node
    sun_geo = sun - (emb + ear)
    s_ecl = unit(sun_geo - pole * (pole * sun_geo).sum(0))
    lam = np.degrees(np.arctan2((pole * np.cross(node.T, s_ecl.T).T).sum(0), (node * s_ecl).sum(0)))
    moon_km = np.linalg.norm(moo - ear, axis=0)
    moon_fit, earth_fit = mean_anomaly_fits()
    return [(lam + 90) % 180 - 90,                                   # Sun-node distance
            np.degrees(np.arcsin(R_EARTH_KM / moon_km)) * 60,        # Moon horizontal parallax
            moon_km,
            np.linalg.norm(sun_geo, axis=0) / AU_KM,
            moon_fit(jd), earth_fit(jd),
            true_anomaly(emb - sun, embv - sunv, GM_SUN + GM_EARTH + GM_MOON),
            true_anomaly(moo - ear, moov - earv, GM_EARTH + GM_MOON)]

def deg360(x):
    """0-360 angle to 4 decimals as text; a value that rounds to 360.0000 is written 0.0000."""
    return f'{x:.4f}' if round(x, 4) < 360 else '0.0000'

def format_geometry(cols):
    """Rows of output text for the arrays returned by geometry()."""
    return [[f'{a:+.4f}', f'{b:.4f}', f'{c:.1f}', f'{d:.7f}', f'{e:.4f}', f'{g:.4f}', deg360(s), deg360(m)]
            for a, b, c, d, e, g, s, m in zip(*cols)]

def add_cum_seconds(header, rows):
    """Insert the time axis used by every other output file -- whole TD seconds from -15000 Jan 01 00:00 TD
    (Julian calendar before 1582 Oct 15) -- after 'TD of GE', if the catalog does not have it yet."""
    if CUM in header:
        return header, rows
    iD, iT = header.index('Date'), header.index('TD of GE')
    def cum(date, td):
        p = date.split(); h, mi, s = (int(x) for x in td.split(':'))
        days = cal_to_jd(int(p[0]), MONTHS[p[1]], int(p[2])) - JD0          # exact whole days
        return str(int(round(days)) * 86400 + h * 3600 + mi * 60 + s)
    k = iT + 1
    return header[:k] + [CUM] + header[k:], [r[:k] + [cum(r[iD], r[iT])] + r[k:] for r in rows]

def main():
    header, rows = add_cum_seconds(*read_without_new(CAT))
    iD, iT = header.index('Date'), header.index('TD of GE')
    jd = np.array([row_jd(r[iD], r[iT]) for r in rows])
    cols = geometry(jd)
    values = format_geometry(cols)
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
    sun_node, parallax, moon_km, sun_au = cols[:4]
    print(f'{len(rows)} rows; Sun-node {sun_node.min():+.3f}..{sun_node.max():+.3f} deg; '
          f'parallax {parallax.min():.2f}..{parallax.max():.2f}\'; '
          f'Moon {moon_km.min():,.0f}..{moon_km.max():,.0f} km; Sun {sun_au.min():.5f}..{sun_au.max():.5f} AU; '
          f"{_fits['perigees'].size} perigees, {_fits['perihelia'].size} perihelia")

if __name__ == '__main__':
    main()
