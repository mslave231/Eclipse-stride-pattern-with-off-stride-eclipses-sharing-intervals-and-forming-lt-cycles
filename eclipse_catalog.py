"""
Five-Millennium-style eclipse catalogue (SOLAR + LUNAR) for any year range inside
the JPL DE441 ephemeris (-13200 Aug 15 .. +17191 Mar 15). The published 30,000-year
catalog was produced in six chunks covering -13198 .. +17189 and stitched together
(pipeline/stitch.py). Output columns follow NASA's catalogs:

    Date | TD of Greatest Eclipse | Delta T (s) | Solar or Lunar | Type | Magnitude
    (+ a detailed CSV with Gamma, type code, umbral and penumbral magnitudes)

Method
------
* JPL DE441 ephemeris via skyfield (set ECLIPSE_EPH to use another .bsp).
* Every new and full moon is located directly from the ephemeris: a mean-lunation
  estimate seeds a Newton root-find on the Moon-Sun longitude difference. (An
  analytical series such as Meeus Ch. 49 is NOT used -- it degrades far from J2000.)
* Syzygies where the Moon is > 1.75 deg from the shadow axis are skipped (no eclipse
  is possible; the true limit is ~1.58 deg).
* The instant of GREATEST eclipse is refined numerically as the moment the shadow
  axis passes closest to Earth's centre (solar) / the Moon passes closest to the
  antisolar axis (lunar). Gamma is that minimum distance in Earth radii.
* APPARENT geocentric positions (light-time + aberration + deflection) are used
  for both bodies -- calibration against NASA shows this reproduces NASA's gamma
  to ~3e-5 Earth radii (astrometric is ~20x worse for lunar).
* Solar magnitude uses the TOPOCENTRIC correction (observer at the greatest-
  eclipse point is ~1 Earth radius nearer the Moon), matching NASA; lunar radius
  for the magnitude ratio k = 0.272307 (1736.81 km).
* Lunar umbral/penumbral shadow radii are enlarged by a fixed atmospheric shell
  of 63.5 km (calibrated to reproduce NASA's published magnitudes to ~1e-4).
* Delta T = Espenak & Meeus (2006) polynomials plus NASA's lunar secular-
  acceleration correction -0.000012932*(y-1955)^2 (see delta_t_catalog). Delta T
  only affects the Delta T column; all eclipse times are Terrestrial Time (TD).

Calendar: output dates are Julian before 1582 Oct 15 and Gregorian after (NASA
convention), astronomical year numbering (year 0 = 1 BCE). NOTE: the START/END
years passed on the command line are interpreted by skyfield's ts.tt() in the
proleptic GREGORIAN calendar, so a run starting at year -13198 begins on
Gregorian -13198 Jan 1 = Julian -13198 Apr 12.

Usage:     python eclipse_catalog.py START END      (e.g. -13198 -8200)
Validate:  python validate.py   (1000-2000 vs NASA)   pipeline/compare_ref.py (vs Liu)

Sources (full references in README.md)
* Ephemeris: JPL DE441 -- Park, Folkner, Williams & Boggs (2021), AJ 161, 105.
* Ephemeris reader: Skyfield -- Rhodes (2019), ascl:1907.024.
* Calendar conversion (jd_to_cal) and mean-lunation seed (mean_lunation):
  Meeus, Astronomical Algorithms, 2nd ed. (1998), Ch. 7 and Ch. 49.
* Solar non-central magnitude formula: Meeus (1998), Ch. 54.
* Delta T: Espenak & Meeus (2006), NASA TP-2006-214141 (polynomials, based on Morrison &
  Stephenson 2004, J. Hist. Astron. 35, 327), with NASA's lunar secular-acceleration
  correction using n-dot = -25.858"/cy^2 from Chapront, Chapront-Touze & Francou (2002),
  A&A 387, 700.
* Calibration targets (63.5 km shadow shell, k = 0.272307, Delta T check): NASA Five
  Millennium Catalogs -- Eclipse Predictions by Fred Espenak (NASA's GSFC).
"""

import os, math, csv
import numpy as np
from skyfield.api import load, Loader

# ── Constants ─────────────────────────────────────────────────────────────────
R_EARTH_KM    = 6378.1366
R_SUN_KM      = 696000.0
R_MOON_KM     = 1737.4
SYNODIC_MONTH = 29.530588853                  # days
ATM_SHELL_KM  = 63.5                          # lunar shadow atmospheric enlargement
D2R           = math.pi / 180.0

# Ephemeris: DE441 (-13200..+17191) by default. NOTE: the .bsp files were removed from
# this folder to save space -- re-download de441.bsp here to run the engine again.
EPH_FILE = os.environ.get('ECLIPSE_EPH', 'de441.bsp')

ts     = load.timescale()
loader = Loader('.')
print(f"Loading {EPH_FILE} ...")
eph    = loader(EPH_FILE)
earth, moon, sun = eph['earth'], eph['moon'], eph['sun']
print("Loaded.")

# ── Apparent geocentric position (km): light-time + aberration + deflection ─────
def apparent_km(t, body):
    return earth.at(t).observe(body).apparent().position.km

# ── JD (TT) -> calendar (Julian before 1582 Oct 15, Gregorian after) ────────────
# Uses math.floor (not int) throughout: for negative JD (deep BCE, before JD 0 =
# 4713 BCE) int() truncates toward zero and yields negative days. Astronomical
# year numbering (year 0 = 1 BCE), matching NASA.
def jd_to_cal(jd_tt):
    jd = jd_tt + 0.5
    z  = math.floor(jd)
    f  = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - math.floor(alpha / 4)
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    dy    = b - d - math.floor(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year  = c - 4716 if month > 2 else c - 4715
    hours = f * 24
    h     = int(hours)
    mins  = (hours - h) * 60
    m     = int(mins)
    secs  = (mins - m) * 60
    return year, month, dy, h, m, secs

def decimal_year(jd_tt):
    """Fractional year for the Delta T polynomial (Espenak convention)."""
    y, mo, d, h, mi, s = jd_to_cal(jd_tt)
    return y + (mo - 0.5) / 12.0

# NASA's Five Millennium catalogs use the Espenak & Meeus 2006 polynomials with the
# Moon's secular acceleration revised to n-dot = -25.858"/cy^2 (Chapront et al. 2002),
# which adds  c = -0.000012932 * (y - 1955)^2  seconds outside 1955-2005.
# Verified against NASA's published Delta T: 1001-2000 (5,044 eclipses) mean |err|
# 0.25 s (integer rounding); spot checks at -1999, 2045-2061 and 2901-3000 within
# 1.4 s. (Until 2026-10-20 this used a quadratic fitted to 1001-2000 only and frozen
# outside that range, which drifted from NASA's values before 1000 and after 2000.)
def delta_t_catalog(year):
    c = 0.0 if 1955.0 <= year <= 2005.0 else -0.000012932 * (year - 1955.0) ** 2
    return delta_t(year) + c

# ── Delta T (Espenak & Meeus 2006) ───────────────────────────────────────────
def delta_t(year: float) -> float:
    y = year
    if y < -500:
        u = (y - 1820) / 100
        return -20 + 32*u*u
    elif y < 500:
        u = y / 100
        return (10583.6 + u*(-1014.41 + u*(33.78311 + u*(-5.952053
                + u*(-0.1798452 + u*(0.022174192 + u*0.0090316521))))))
    elif y < 1600:
        u = (y - 1000) / 100
        return (1574.2 + u*(-556.01 + u*(71.23472 + u*(0.319781
                + u*(-0.8503463 + u*(-0.005050998 + u*0.0083572073))))))
    elif y < 1700:
        t = y - 1600
        return 120 + t*(-0.9808 + t*(-0.01532 + t/7129))
    elif y < 1800:
        t = y - 1700
        return (8.83 + t*(0.1603 + t*(-0.0059285 + t*(0.00013336 - t/1174000))))
    elif y < 1860:
        t = y - 1800
        return (13.72 + t*(-0.332447 + t*(0.0068612 + t*(0.0041116
                + t*(-0.00037436 + t*(0.0000121272 + t*(-0.0000001699
                + t*0.000000000875)))))))
    elif y < 1900:
        t = y - 1860
        return (7.62 + t*(0.5737 + t*(-0.251754 + t*(0.01680668
                + t*(-0.0004473624 + t/233174)))))
    elif y < 1920:
        t = y - 1900
        return -2.79 + t*(1.494119 + t*(-0.0598939 + t*(0.0061966 - t*0.000197)))
    elif y < 1941:
        t = y - 1920
        return 21.20 + t*(0.84493 + t*(-0.076100 + t*0.0020936))
    elif y < 1961:
        t = y - 1950
        return 29.07 + t*(0.407 + t*(-1/233 + t/2547))
    elif y < 1986:
        t = y - 1975
        return 45.45 + t*(1.067 + t*(-1/260 - t/718))
    elif y < 2005:
        t = y - 2000
        return (63.86 + t*(0.3345 + t*(-0.060374 + t*(0.0017275
                + t*(0.000651814 + t*0.00002373599)))))
    elif y < 2050:
        t = y - 2000
        return 62.92 + t*(0.32217 + t*0.005589)
    elif y < 2150:
        # Espenak & Meeus 2006 segment 2050-2150 (missing before 2026-10-20, which
        # made Delta T jump from ~93 s to ~151 s at 2050).
        u = (y - 1820) / 100
        return -20 + 32*u*u - 0.5628*(2150 - y)
    else:
        u = (y - 1820) / 100
        return -20 + 32*u*u

# ── Syzygy from the ephemeris (robust over DE441's full -13200..+17191 span) ─────
# The Meeus analytical series is only accurate within a few millennia of J2000, so
# new/full moons are found directly from the ephemeris: a linear+secular mean-
# lunation predictor seeds a Newton root-find on the Moon-Sun ecliptic-longitude
# difference, which increases monotonically at ~12.19 deg/day (one root per month).
MEAN_ELONG_RATE = 12.190749            # deg/day, mean synodic motion of the Moon

def mean_lunation(k):
    """Mean syzygy JD(TT). k integer -> new moon (k=0 ~ 2000 Jan 6);
    k = integer+0.5 -> full moon."""
    T = k / 1236.85
    return (2451550.09766 + 29.530588861 * k
            + 0.00015437 * T**2 - 0.000000150 * T**3 + 0.00000000073 * T**4)

_geo_moon = moon - earth          # geocentric vector functions (no light-time)
_geo_sun  = sun  - earth
_OBLIQ = 23.4392911 * D2R          # J2000 mean obliquity
_COSE, _SINE = math.cos(_OBLIQ), math.sin(_OBLIQ)

def _ecl_lonlat(vec_func, t):
    """Geometric ecliptic (lon, lat) in radians, via a fixed J2000-obliquity
    rotation of the ICRF position. BOTH bodies must use this same rotation so
    the elongation is frame-consistent -- mixing a J2000 Moon with an ecliptic-
    of-date Sun introduces a precession error (~14 deg at year 1000)."""
    x, y, z = vec_func.at(t).position.km
    ye =  y * _COSE + z * _SINE
    ze = -y * _SINE + z * _COSE
    return math.atan2(ye, x), math.atan2(ze, math.hypot(x, ye))

def find_syzygy(k_value, target_deg):
    """target_deg=0 -> new moon, 180 -> full moon. Returns (jd_tt, Moon latitude
    RELATIVE TO THE SUN, deg) -- the node-distance proxy that decides eclipses.
    Newton on the (monotonic) Moon-Sun elongation, both bodies in the J2000
    ecliptic. The RELATIVE latitude (beta_moon - beta_sun) is frame-invariant; the
    Moon's absolute J2000 latitude is not -- over 13000 yr the ecliptic itself tilts
    ~1.5 deg vs J2000, which would push real eclipses past the node cutoff. A loose
    tolerance keeps it cheap -- this just seeds greatest_eclipse (re-found to ~1 s)."""
    target = target_deg * D2R
    full = target_deg != 0.0
    jd = mean_lunation(k_value)
    lat_rel = 0.0
    for _ in range(8):
        t = ts.tt_jd(jd)
        lon_m, lat_m = _ecl_lonlat(_geo_moon, t)
        lon_s, lat_s = _ecl_lonlat(_geo_sun, t)
        # eclipse node-distance = Moon latitude minus the shadow-axis latitude:
        # the Sun (new moon) or the antisolar point at -beta_sun (full moon).
        lat_rel = lat_m - (-lat_s if full else lat_s)
        d = (lon_m - lon_s - target + math.pi) % (2*math.pi) - math.pi
        step = math.degrees(d) / MEAN_ELONG_RATE
        jd -= step
        if abs(step) < 0.02:                                   # ~30 min: ample seed
            break
    return jd, math.degrees(lat_rel)

# ── Solar shadow geometry ───────────────────────────────────────────────────────
GAMMA_CENTRAL = 0.9972                     # mean central-eclipse limit (oblate Earth)

def solar_geometry(jd):
    t = ts.tt_jd(jd)
    r_moon = apparent_km(t, moon)
    r_sun  = apparent_km(t, sun)
    d_moon = np.linalg.norm(r_moon)
    d_sun  = np.linalg.norm(r_sun)
    d_sm   = np.linalg.norm(r_sun - r_moon)

    axis_hat = (r_moon - r_sun) / d_sm        # Sun -> Moon -> Earth
    s0   = -np.dot(r_moon, axis_hat)
    foot = r_moon + s0 * axis_hat
    gamma = np.linalg.norm(foot) / R_EARTH_KM
    if foot[2] < 0:
        gamma = -gamma

    sin_f1 = (R_SUN_KM + R_MOON_KM) / d_sm
    sin_f2 = (R_SUN_KM - R_MOON_KM) / d_sm
    L1 = (d_moon * sin_f1 + R_MOON_KM) / R_EARTH_KM      # penumbral radius
    u  = (d_moon * sin_f2 - R_MOON_KM) / R_EARTH_KM      # umbral radius (signed)

    sin_sun  = R_SUN_KM  / d_sun
    sin_moon = R_MOON_KM / d_moon
    toward_earth = np.dot(r_moon, r_sun) > 0             # new-moon guard
    return gamma, sin_sun, sin_moon, L1, u, toward_earth, d_moon, d_sun

# Effective lunar radius for the SOLAR magnitude (apparent-diameter ratio).
# Calibrated to NASA SEcat5 central eclipses (k=0.272307, the IAU eclipse-
# prediction value); removes a +0.0004 bias vs the physical radius and resolves
# 8 of 13 type-boundary mismatches. Detection/geometry still use R_MOON_KM.
R_MOON_MAG = 1736.81

# ── Solar classification (topocentric magnitude; oblate central limit) ──────────
def classify_solar(gamma, sin_sun, sin_moon, L1, u, d_moon, d_sun):
    ag = abs(gamma)
    penumbra_limit = GAMMA_CENTRAL + L1
    if ag >= penumbra_limit:
        return None, 0.0

    if ag >= GAMMA_CENTRAL:
        # Non-central eclipse: the shadow axis misses Earth's centre-disk, so no
        # observer is ever on the axis. NASA reports the obscuration magnitude
        # (fraction of the Sun's diameter covered) at the greatest-eclipse point,
        # which -> 1.0 exactly where the umbra/antumbra grazes the limb.
        mag = (penumbra_limit - ag) / (L1 + u)
        if ag >= GAMMA_CENTRAL + abs(u):
            return 'P', mag                             # umbra/antumbra miss Earth
        return ('T' if u < 0 else 'A'), mag             # umbral graze (never hybrid)

    # Central eclipse: an observer at the greatest-eclipse point lies on the axis
    # and is ~R_earth*sqrt(1-gamma^2) nearer the Moon. NASA reports the
    # topocentric ratio of apparent diameters there.
    q = math.sqrt(max(0.0, 1.0 - gamma * gamma))
    d_moon_topo = d_moon - R_EARTH_KM * q
    d_sun_topo  = d_sun  - R_EARTH_KM * q
    mag_topo = (R_MOON_MAG / d_moon_topo) / (R_SUN_KM / d_sun_topo)
    mag_geo  = (R_MOON_MAG / d_moon)      / (R_SUN_KM / d_sun)   # ~ mag at path ends

    if mag_topo < 1.0:
        return 'A', mag_topo                            # annular even at greatest
    if mag_geo < 1.0:
        return 'H', mag_topo                            # total mid-path, annular ends
    return 'T', mag_topo

# ── Lunar shadow geometry (antisolar axis) ──────────────────────────────────────
def lunar_geometry(jd):
    t = ts.tt_jd(jd)
    r_moon = apparent_km(t, moon)
    r_sun  = apparent_km(t, sun)
    d_moon = np.linalg.norm(r_moon)
    d_sun  = np.linalg.norm(r_sun)
    axis = -r_sun / d_sun                               # antisolar direction
    x_m  = np.dot(r_moon, axis)
    perp = r_moon - x_m * axis
    gamma_km = np.linalg.norm(perp)
    if perp[2] < 0:
        gamma_km = -gamma_km
    # geometric shadow radii at the Moon's distance, + atmospheric shell
    r_umb = R_EARTH_KM - x_m * (R_SUN_KM - R_EARTH_KM) / d_sun + ATM_SHELL_KM
    r_pen = R_EARTH_KM + x_m * (R_SUN_KM + R_EARTH_KM) / d_sun + ATM_SHELL_KM
    opposite = x_m > 0                                  # full-moon guard
    return gamma_km, r_umb, r_pen, opposite

def classify_lunar(gamma_km, r_umb, r_pen):
    ag = abs(gamma_km)
    umb_mag = (r_umb + R_MOON_KM - ag) / (2 * R_MOON_KM)
    pen_mag = (r_pen + R_MOON_KM - ag) / (2 * R_MOON_KM)
    if pen_mag <= 0.0:
        return None, 0.0, 0.0
    if umb_mag >= 1.0:
        return 'T', umb_mag, pen_mag
    if umb_mag > 0.0:
        return 'P', umb_mag, pen_mag
    return 'N', umb_mag, pen_mag                        # penumbral only

# ── Greatest eclipse: minimise gamma^2 near syzygy (coarse->fine->parabola) ─────
def greatest_eclipse(jd0, gamma_km_fn):
    def g2(j):
        v = gamma_km_fn(j)
        return v * v
    # Coarse bracket over +/-0.3 day, then two successive zoom-and-parabola passes
    # (~12 min, then ~1.5 min spacing) so the greatest-eclipse instant is good to ~1s.
    lo, hi = jd0 - 0.3, jd0 + 0.3
    best = jd0
    for _ in range(2):
        grid = np.linspace(lo, hi, 13)
        gv = [g2(j) for j in grid]
        jf = int(np.argmin(gv))
        best = float(grid[jf])
        if 0 < jf < 12:
            y0, y1, y2 = gv[jf-1], gv[jf], gv[jf+1]
            den = y0 - 2*y1 + y2
            h = grid[1] - grid[0]
            if den > 0:
                best = float(grid[jf] + 0.5 * h * (y0 - y2) / den)
        step = grid[1] - grid[0]
        lo, hi = best - step, best + step
    return best

def _solar_gamma_km(jd):  return solar_geometry(jd)[0] * R_EARTH_KM
def _lunar_gamma_km(jd):  return lunar_geometry(jd)[0]

# ── Scan ────────────────────────────────────────────────────────────────────────
MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun',
               'Jul','Aug','Sep','Oct','Nov','Dec']
# Node pre-filter: no eclipse of any kind is possible if the Moon's ecliptic
# latitude at syzygy exceeds the ecliptic limit (~1.58 deg solar, ~1.57 lunar);
# 1.75 deg leaves margin for parallax/distance variation.
LAT_LIMIT   = 1.75          # degrees
TYPE_WORD_SOLAR = {'P':'Partial','A':'Annular','T':'Total','H':'Hybrid'}
TYPE_WORD_LUNAR = {'N':'Penumbral','P':'Partial','T':'Total'}

def _fmt(jd_ge):
    # Round to a whole second in JD space so any midnight rollover lands on the
    # correct calendar date (jd_to_cal applies the Julian/Gregorian switch).
    jd_r = round(jd_ge * 86400.0) / 86400.0
    yr, mo, dy, hr, mi, se = jd_to_cal(jd_r)
    se = int(round(se))
    if se >= 60:                       # float residue at a minute boundary
        se = 59
    date_str = f"{yr:4d} {MONTH_NAMES[mo-1]} {int(dy):02d}"
    td_str   = f"{hr:02d}:{mi:02d}:{se:02d}"
    return yr, mo, dy, date_str, td_str

def scan(year_start, year_end):
    # Half-open interval [START Jan 1 00:00, (END+1) Jan 1 00:00) TT, so consecutive
    # chunks (e.g. ..-8200 and -8199..) tile time exactly. Before 2026-10-20 the end
    # was END Dec 31 00:00, which skipped the last day of each chunk (checked: no
    # eclipse fell on any of the five skipped days of the published catalog).
    # ts.tt() interprets these dates in the proleptic Gregorian calendar.
    jd_start = ts.tt(year_start, 1, 1).tt
    jd_end   = ts.tt(year_end + 1, 1, 1).tt
    k0 = int((jd_start - 2451550.09766) / SYNODIC_MONTH) - 1
    k1 = int((jd_end   - 2451550.09766) / SYNODIC_MONTH) + 1
    print(f"Scanning lunations k={k0}..{k1} for {year_start}-{year_end} ...")

    results = []
    n_lun = (k1 - k0 + 1)
    for i, k in enumerate(range(k0, k1 + 1)):
        if i % 2000 == 0:
            print(f"  {100*i/n_lun:.0f}%  ({len(results)} eclipses)")

        # ---- Solar (new moon) ----
        jd_nm, lat_nm = find_syzygy(k, 0.0)
        if jd_start <= jd_nm < jd_end and abs(lat_nm) <= LAT_LIMIT:
            jd_ge = greatest_eclipse(jd_nm, _solar_gamma_km)
            g, ss, sm, L1, u, toward, dM, dS = solar_geometry(jd_ge)
            if toward:
                etype, mag = classify_solar(g, ss, sm, L1, u, dM, dS)
                if etype:
                    dt_s = delta_t_catalog(decimal_year(jd_ge))
                    yr, mo, dy, ds, tds = _fmt(jd_ge)
                    results.append({'jd':jd_ge,'kind':'Solar','date':ds,'td':tds,
                        'dt':dt_s,'tcode':etype,'type':TYPE_WORD_SOLAR[etype],
                        'mag':mag,'gamma':g})

        # ---- Lunar (full moon) ----
        jd_fm, lat_fm = find_syzygy(k + 0.5, 180.0)
        if jd_start <= jd_fm < jd_end and abs(lat_fm) <= LAT_LIMIT:
            jd_ge = greatest_eclipse(jd_fm, _lunar_gamma_km)
            gkm, r_umb, r_pen, opp = lunar_geometry(jd_ge)
            if opp:
                etype, umag, pmag = classify_lunar(gkm, r_umb, r_pen)
                if etype:
                    dt_s = delta_t_catalog(decimal_year(jd_ge))
                    yr, mo, dy, ds, tds = _fmt(jd_ge)
                    mag = umag if etype in ('T', 'P') else pmag
                    results.append({'jd':jd_ge,'kind':'Lunar','date':ds,'td':tds,
                        'dt':dt_s,'tcode':etype,'type':TYPE_WORD_LUNAR[etype],
                        'mag':mag,'gamma':gkm/R_EARTH_KM,'umag':umag,'pmag':pmag})

    results.sort(key=lambda r: r['jd'])
    return results

# ── Entry point ───────────────────────────────────────────────────────────────
# Usage:  python eclipse_catalog.py [START_YEAR END_YEAR]
#   no args      -> 1000..2000 (the range compared with NASA; fixed filenames used by validate.py)
#   START END    -> that range -> eclipse_catalog_<START>_<END>[_detailed].csv
# Astronomical year numbering (year 0 = 1 BCE), so BCE years are negative.
# Uses de441.bsp by default (set ECLIPSE_EPH to another .bsp, e.g. de422.bsp, if wanted).
if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 3:
        y0, y1 = int(sys.argv[1]), int(sys.argv[2])
        out6 = f'eclipse_catalog_{y0}_{y1}.csv'
        outd = f'eclipse_catalog_{y0}_{y1}_detailed.csv'
    else:
        y0, y1 = 1000, 2000
        out6 = 'eclipse_catalog_1000_2000.csv'
        outd = 'eclipse_catalog_detailed.csv'

    ecl = scan(y0, y1)

    # Deliverable: the 6 requested columns.
    with open(out6, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Date','TD of Greatest Eclipse','Delta T (s)',
                    'Solar or Lunar','Type','Magnitude'])
        for e in ecl:
            w.writerow([e['date'], e['td'], f"{e['dt']:.0f}",
                        e['kind'], e['type'], f"{e['mag']:.4f}"])

    # Detailed CSV for comparison / richer use.
    with open(outd, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Date','TD of GE','DeltaT_s','Kind','TypeCode','Type',
                    'Gamma','Magnitude','UmbralMag','PenumbralMag'])
        for e in ecl:
            w.writerow([e['date'], e['td'], f"{e['dt']:.1f}", e['kind'],
                        e['tcode'], e['type'], f"{e['gamma']:+.4f}",
                        f"{e['mag']:.4f}",
                        f"{e.get('umag',''):.4f}" if 'umag' in e else '',
                        f"{e.get('pmag',''):.4f}" if 'pmag' in e else ''])

    from collections import Counter
    sol = [e for e in ecl if e['kind']=='Solar']
    lun = [e for e in ecl if e['kind']=='Lunar']
    print(f"\nDone -- {len(ecl)} eclipses -> {out6}")
    print(f"  Solar: {len(sol)}  tally {dict(Counter(e['tcode'] for e in sol))}")
    print(f"  Lunar: {len(lun)}  tally {dict(Counter(e['tcode'] for e in lun))}")
