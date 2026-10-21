"""
Validate eclipse_catalog_detailed.csv against NASA's Five Millennium catalogs:
  Solar  -> https://eclipse.gsfc.nasa.gov/SEcat5/SE####-####.html
  Lunar  -> https://eclipse.gsfc.nasa.gov/LEcat5/LE####-####.html

Source and credit: Espenak & Meeus, Five Millennium Catalogs of Solar and Lunar Eclipses
(NASA TP-2006-214141 / TP-2009-214172 canons; online catalogs SEcat5 / LEcat5).
Eclipse Predictions by Fred Espenak (NASA's GSFC). Cached copies of the 1001-2000 pages
are in reference_nasa/.

NASA 'Type' is one or two chars; the PRIMARY type is the first character
(solar P/A/T/H, lunar N/P/T). The previous regex silently dropped rows whose
type carried a non-word suffix (e.g. 'T-', 'A-'); this one keeps every row.
"""
import re, csv, os, urllib.request
from collections import Counter

CENTURIES = [(y, y+100) for y in range(1000, 2000, 100)]   # 1000-1100 ... 1900-2000
SE_BASE = 'https://eclipse.gsfc.nasa.gov/SEcat5/'
LE_BASE = 'https://eclipse.gsfc.nasa.gov/LEcat5/'
TAG = re.compile(r'<[^>]+>')

# Catalog page filenames start at +1 (e.g. SE1001-1100 covers 1001-1100).
def page(prefix, y0):  return f"reference_nasa/{prefix}{y0+1:04d}-{y0+100:04d}.html"

SOLAR_ROW = re.compile(
    r'^\s*\d{5}\s+(\d{1,4} \w{3} \d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+(-?\d+)\s+'
    r'-?\d+\s+\d+\s+([PATH])\S*\s+\S+\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)')
LUNAR_ROW = re.compile(
    r'^\s*\d{5}\s+(\d{1,4} \w{3} \d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+(-?\d+)\s+'
    r'-?\d+\s+\d+\s+([NPT])\S*\s+\S+\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)')

def fetch(base, fname):
    if not os.path.exists(fname):
        print(f"  downloading {fname} ...")
        html = urllib.request.urlopen(base + fname, timeout=60).read().decode('utf-8','replace')
        open(fname, 'w', encoding='utf-8').write(html)
    return open(fname, 'r', encoding='utf-8').read()

def parse_solar(html):
    text = TAG.sub(' ', html)
    out = []
    for line in text.splitlines():
        m = SOLAR_ROW.match(line)
        if m:
            date, td, dt, typ, gamma, mag = m.groups()
            out.append({'date':date,'td':td,'dt':int(dt),'type':typ,
                        'gamma':float(gamma),'mag':float(mag)})
    return out

def parse_lunar(html):
    text = TAG.sub(' ', html)
    out = []
    for line in text.splitlines():
        m = LUNAR_ROW.match(line)
        if m:
            date, td, dt, typ, gamma, penmag, umbmag = m.groups()
            out.append({'date':date,'td':td,'dt':int(dt),'type':typ,
                        'gamma':float(gamma),'pen':float(penmag),'umb':float(umbmag)})
    return out

def norm_date(d):
    p = d.split()
    return f"{int(p[0])} {p[1]} {int(p[2])}"

def td_seconds(td):
    h, m, s = td.split(':')
    return int(h)*3600 + int(m)*60 + float(s)

def load_mine(path):
    sol, lun = {}, {}
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            rec = {'date':norm_date(r['Date']), 'td':r['TD of GE'].strip(),
                   'dt':float(r['DeltaT_s']), 'type':r['TypeCode'].strip(),
                   'gamma':float(r['Gamma']), 'mag':float(r['Magnitude'])}
            if r['Kind'] == 'Solar':
                sol[rec['date']] = rec
            else:
                rec['umb'] = float(r['UmbralMag']) if r['UmbralMag'] else None
                rec['pen'] = float(r['PenumbralMag']) if r['PenumbralMag'] else None
                lun[rec['date']] = rec
    return sol, lun

def compare(label, nasa_by_date, mine_by_date, magfn):
    nd, md = set(nasa_by_date), set(mine_by_date)
    print(f"\n===== {label} =====")
    print(f"NASA: {len(nd)}   Mine: {len(md)}")
    print(f"  NASA type tally: {dict(Counter(r['type'] for r in nasa_by_date.values()))}")
    print(f"  Mine type tally: {dict(Counter(r['type'] for r in mine_by_date.values()))}")
    missing = nd - md; extra = md - nd
    print(f"  Matched: {len(nd & md)}   Missing(NASA-only): {len(missing)}   Extra(mine-only): {len(extra)}")
    if missing: print("    missing e.g.:", sorted(missing)[:8])
    if extra:   print("    extra   e.g.:", sorted(extra)[:8])

    n=0; td_e=dt_e=g_e=m_e=0.0; type_bad=0
    worst_td=worst_g=worst_m=(0,None); conf=Counter()
    for d in nd & md:
        a, b = nasa_by_date[d], mine_by_date[d]
        n += 1
        te = abs(td_seconds(a['td'])-td_seconds(b['td'])); td_e+=te
        de = abs(a['dt']-b['dt']); dt_e+=de
        ge = abs(a['gamma']-abs_signed(b['gamma'],a['gamma'])); g_e+=ge
        me = magfn(a,b); m_e+=me
        if te>worst_td[0]: worst_td=(te,d)
        if ge>worst_g[0]:  worst_g=(ge,d)
        if me>worst_m[0]:  worst_m=(me,d)
        if a['type']!=b['type']:
            type_bad+=1; conf[(a['type'],b['type'])]+=1
    if n:
        print(f"  -- mean abs error over {n} matched --")
        print(f"    TD    : {td_e/n:7.2f}s  (worst {worst_td[0]:.0f}s @ {worst_td[1]})")
        print(f"    DeltaT: {dt_e/n:7.2f}s")
        print(f"    Gamma : {g_e/n:7.5f}   (worst {worst_g[0]:.4f} @ {worst_g[1]})")
        print(f"    Mag   : {m_e/n:7.5f}   (worst {worst_m[0]:.4f} @ {worst_m[1]})")
        print(f"    Type mismatches: {type_bad}/{n}")
        for (nt,mt),c in sorted(conf.items(), key=lambda x:-x[1]):
            print(f"        NASA {nt} -> mine {mt}: {c}")

def abs_signed(mine_g, nasa_g):
    # NASA and our sign conventions agree; compare directly.
    return mine_g

def main():
    nasa_sol, nasa_lun = [], []
    for (y0, y1) in CENTURIES:
        nasa_sol += parse_solar(fetch(SE_BASE, page('SE', y0)))
        nasa_lun += parse_lunar(fetch(LE_BASE, page('LE', y0)))
    nsol = {norm_date(r['date']): r for r in nasa_sol}
    nlun = {norm_date(r['date']): r for r in nasa_lun}
    print(f"NASA parsed -- solar {len(nasa_sol)}, lunar {len(nasa_lun)}")

    msol, mlun = load_mine('eclipse_catalog_detailed.csv')

    compare("SOLAR", nsol, msol, magfn=lambda a,b: abs(a['mag']-b['mag']))
    # lunar: compare against umbral mag for T/P, penumbral for N
    def lunar_mag_err(a, b):
        if a['type'] in ('T','P'):
            return abs(a['umb'] - (b['umb'] if b['umb'] is not None else b['mag']))
        return abs(a['pen'] - (b['pen'] if b['pen'] is not None else b['mag']))
    compare("LUNAR", nlun, mlun, magfn=lunar_mag_err)

if __name__ == '__main__':
    main()
