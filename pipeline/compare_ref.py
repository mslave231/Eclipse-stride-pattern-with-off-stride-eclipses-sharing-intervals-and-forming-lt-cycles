"""Cross-check this catalog against the external reference workbook
(_ref_catalogue.xlsx) over their overlapping years.

Reference data: Yuk Tung Liu's solar and lunar eclipse catalogs, -3999..+4000
(https://ytliu.epizy.com/eclipse/), compiled into a workbook by Matt Slavik. Liu's
catalogs are computed independently of this project (his own ELP/MPP02-based lunar
ephemeris fitted to JPL DE406, plus a VSOP-class solar theory). The workbook is not
redistributed here; download the catalogs from Liu's site.

Matches eclipses by calendar
date (with a +/-1 day fallback for midnight rollovers) and compares TD of greatest
eclipse, gamma, type, and magnitude.

Usage: python compare_ref.py [my_detailed.csv lo_year hi_year]
Default: chunk 2 detailed vs window -3999..-3200.
"""
import openpyxl, csv, sys

if len(sys.argv) >= 4:
    MY_CSV, WIN_LO, WIN_HI = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
else:
    MY_CSV, WIN_LO, WIN_HI = 'eclipse_catalog_-8199_-3200_detailed.csv', -3999, -3200

MONTHS = {m: i + 1 for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}

# ── reference ────────────────────────────────────────────────────────────────
wb = openpyxl.load_workbook('_ref_catalogue.xlsx', read_only=True, data_only=True)
def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None
def load_ref(sheet):
    d = {}
    for i, r in enumerate(wb[sheet].iter_rows(values_only=True)):
        if i == 0 or r[12] is None: continue
        y = int(r[12])
        if not (WIN_LO <= y <= WIN_HI): continue
        d[(y, int(r[13]), int(r[14]))] = {
            'secs': int(r[15]), 'type': r[3], 'gamma': num(r[4]),
            'mag1': num(r[5]), 'mag2': num(r[6])}
    return d
ref_sol = load_ref('Solar Eclipse Data')
ref_lun = load_ref('Lunar Eclipse Data')

# ── mine ─────────────────────────────────────────────────────────────────────
def load_mine(path):
    sol, lun = {}, {}
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            p = r['Date'].split()
            y = int(p[0])
            if not (WIN_LO <= y <= WIN_HI): continue
            h, mi, s = map(int, r['TD of GE'].split(':'))
            rec = {'secs': h*3600 + mi*60 + s, 'tcode': r['TypeCode'],
                   'gamma': float(r['Gamma']), 'mag': float(r['Magnitude']),
                   'umag': float(r['UmbralMag']) if r['UmbralMag'] else None,
                   'pmag': float(r['PenumbralMag']) if r['PenumbralMag'] else None}
            (sol if r['Kind'] == 'Solar' else lun)[(y, MONTHS[p[1]], int(p[2]))] = rec
    return sol, lun
my_sol, my_lun = load_mine(MY_CSV)

# ── helpers ──────────────────────────────────────────────────────────────────
def norm_sol(c): return c.strip('()').rstrip('ns')          # (T),Tn,Ts -> T ; An,As -> A
def norm_lun(c): return {'Pen': 'N'}.get(c, c)              # Pen -> N ; P,T unchanged
def stats(x):
    if not x: return 'n/a'
    xs = sorted(x); n = len(xs)
    return f'max {xs[-1]:.4g} | mean {sum(xs)/n:.4g} | median {xs[n//2]:.4g}'
def buckets(x):
    b = {'<=1s':0,'<=2s':0,'<=5s':0,'<=10s':0,'<=60s':0,'>60s':0}
    for v in x:
        for k, lim in [('<=1s',1),('<=2s',2),('<=5s',5),('<=10s',10),('<=60s',60)]:
            if v <= lim: b[k]+=1; break
        else: b['>60s']+=1
    return b

MISM = []
def compare(my, ref, kind):
    only_my = set(my) - set(ref)
    only_ref = set(ref) - set(my)
    exact = set(my) & set(ref)
    # +/-1,2 day fallback for the date-only mismatches (midnight rollovers)
    pm = []
    for k in list(only_my):
        y, m, dd = k
        for off in (1, -1, 2, -2):
            if (y, m, dd+off) in only_ref:
                pm.append((k, (y, m, dd+off))); break
    pm_my = {a for a, _ in pm}; pm_ref = {b for _, b in pm}
    g_only_my = only_my - pm_my; g_only_ref = only_ref - pm_ref

    td=[]; gd=[]; gda=[]; m1=[]; m2=[]; tmis={}
    for k in exact:
        a, b = my[k], ref[k]
        td.append(abs(a['secs'] - b['secs']))
        if b['gamma'] is not None:
            gd.append(a['gamma'] - b['gamma']); gda.append(abs(a['gamma'] - b['gamma']))
        tn = norm_sol(b['type']) if kind == 'solar' else norm_lun(b['type'])
        if a['tcode'] != tn:
            tmis[(a['tcode'], b['type'])] = tmis.get((a['tcode'], b['type']), 0) + 1
            mv = a['mag'] if kind == 'solar' else a['umag']
            rv = b['mag1'] if kind == 'solar' else b['mag2']
            MISM.append((kind, k, a['tcode'], b['type'], a['gamma'], b['gamma'], mv, rv))
        if kind == 'solar':
            if b['mag1'] is not None: m1.append(abs(a['mag'] - b['mag1']))
            if b['mag2'] is not None: m2.append(abs(a['mag'] - b['mag2']))
        else:
            if a['umag'] is not None and b['mag2'] is not None: m1.append(abs(a['umag'] - b['mag2']))
            if a['pmag'] is not None and b['mag1'] is not None: m2.append(abs(a['pmag'] - b['mag1']))
    # cross-midnight TD deltas for the +/-1 day matches
    pm_td = []
    for a, b in pm:
        sa, sb = my[a]['secs'], ref[b]['secs']
        dd = b[2] - a[2]
        pm_td.append(abs((sa - dd*86400) - sb))

    print(f'### {kind.upper()}  window {WIN_LO}..{WIN_HI} ###')
    print(f'  count: mine={len(my)}  ref={len(ref)}  (diff {len(my)-len(ref):+d})')
    print(f'  exact-date matches : {len(exact)}  ({100*len(exact)/max(len(my),1):.2f}% of mine)')
    print(f'  +/- day matches    : {len(pm)}  (TD delta {stats(pm_td)})')
    print(f'  unmatched mine-only: {len(g_only_my)}   ref-only: {len(g_only_ref)}')
    print(f'  TD |delta|, s      : {stats(td)}')
    print(f'  TD buckets         : {buckets(td)}')
    print(f'  gamma signed delta : {stats(gd)}')
    print(f'  gamma |delta|      : {stats(gda)}')
    if kind == 'solar':
        print(f'  |mag - EclipseMag| : {stats(m1)}')
        print(f'  |mag - EclipseMag2|: {stats(m2)}')
    else:
        print(f'  |umbMag - UmMag|   : {stats(m1)}')
        print(f'  |penMag - PenMag|  : {stats(m2)}')
    print(f'  type mismatches (normalized): {sum(tmis.values())}  {tmis}')
    if g_only_my:  print(f'  sample mine-only : {sorted(g_only_my)[:6]}')
    if g_only_ref: print(f'  sample ref-only  : {sorted(g_only_ref)[:6]}')
    print()

compare(my_sol, ref_sol, 'solar')
compare(my_lun, ref_lun, 'lunar')

print('### type-boundary disagreements (date | mine vs ref | gamma mine/ref | mag mine/ref) ###')
for kind, (y, m, d), mt, rt, mg, rg, mv, rv in sorted(MISM):
    mon = [k for k, v in MONTHS.items() if v == m][0]
    print(f'  {kind:5} {y:5d} {mon} {d:02d} | {mt} vs {rt} | g {mg:+.4f}/{rg:+.4f} | mag {mv:.4f}/{rv:.4f}')
