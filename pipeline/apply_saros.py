"""Add 'SEC Saros #' and 'LEC Saros #' to eclipse_catalog_full_formatted.csv (in place).

SAROS NUMBERING CONVENTION (read before quoting Saros numbers)
- Reference numbering: '_saros_numbers.xlsx', 38,284 eclipses (19,013 solar, 19,271
  lunar) covering -3999..+4000. Matt Slavik built this eclipse list from Yuk Tung Liu's
  catalogs (https://ytliu.epizy.com/eclipse/) and assigned the Saros numbers himself,
  matching NASA's Saros numbering wherever it could be verified and calculating the rest
  (Liu's catalogs do not carry Saros numbers). Inside that range every eclipse carries the reference
  number exactly (38,283/38,283 checked), propagated along each 223-lunation series
  (union-find) so series that cross the range edge keep their number outside it too.
- Series lying entirely outside -3999..+4000 have no published reference here. They are
  numbered by the standard rule saros = ((38n+C) mod 223) + 223*cycle, with C and the
  secular trend fitted to the reference data (the "count up/down" continuation). These
  numbers are a convention of this catalog, NOT an external standard, and they can differ
  from other extended numberings -- e.g. the Saros-Inex panorama by Luca Quaglia and
  John Tilley (-11000..+15000, hosted on NASA's eclipse website) labels ~145 of its ~910
  solar series differently, all outside -3999..+4000 (checked 2026-10-20).
- Known quirks: one deep-BCE solar label collision (two series near year -5000 share -66;
  recount_saros.py counts them separately), and lunar Saros 3/-3 follow the reference's
  (NASA's) assignment, which is off the regular Saros-Inex lattice.
- Scheme: Saros/Inex numbering after van den Bergh (1955), Periodicity and Variation of
  Solar (and Lunar) Eclipses, as used by NASA.
Solar eclipses get SEC=number / LEC='x'; lunar get LEC=number / SEC='x'."""
import openpyxl, csv, math, os
from collections import Counter, defaultdict
EPOCH, SYN = 2451550.09766, 29.530588853

def cal_to_jd(y, mo, d, frac=0.0):
    Y, M = y, mo
    if M <= 2: Y -= 1; M += 12
    A = math.floor(Y/100)
    B = (2 - A + math.floor(A/4)) if (y, mo, d) >= (1582,10,15) else 0
    return math.floor(365.25*(Y+4716)) + math.floor(30.6001*(M+1)) + d + B - 1524.5 + frac
def pdate(s):
    mm, dd, yy = s.split('/'); return (-int(yy.strip('()')) if yy.startswith('(') else int(yy)), int(mm), int(dd)

# ---- reference Saros numbers (_saros_numbers.xlsx), keyed by lunation number n ----
wb = openpyxl.load_workbook('_saros_numbers.xlsx', read_only=True, data_only=True)
usol, ulun = {}, {}
for i, row in enumerate(wb['Sheet1'].iter_rows(values_only=True)):
    if i == 0 or row[0] is None: continue
    date, td, kind, sec, lec = row[:5]
    y, m, d = pdate(date); jd = cal_to_jd(y, m, d, td if isinstance(td, (int, float)) else 0.0)
    if kind == 'Solar': usol[round((jd-EPOCH)/SYN)] = int(sec)
    else:               ulun[round((jd-EPOCH)/SYN - 0.5)] = int(lec)

def fit(u):                                   # dominant residue C + secular slope/intercept
    pts = list(u.items())
    C = Counter((s - 38*n) % 223 for n, s in pts).most_common(1)[0][0]
    N = len(pts); sx = sum(n for n, _ in pts); sy = sum(s for _, s in pts)
    sxx = sum(n*n for n, _ in pts); sxy = sum(n*s for n, s in pts)
    slope = (N*sxy - sx*sy)/(N*sxx - sx*sx); return C, slope, (sy - slope*sx)/N
Cs, ms, bs = fit(usol); Cl, ml, bl = fit(ulun)
def formula(n, C, slope, intc):
    mod = (38*n + C) % 223; return mod + 223*round((slope*n + intc - mod)/223)

# ---- this catalog ----
with open('eclipse_catalog_full_formatted.csv', newline='') as f:
    rdr = csv.DictReader(f); fields = rdr.fieldnames; rows = list(rdr)
def nfor(r):
    y, m, d = pdate(r['Date']); h, mi, se = map(int, r['TD of Greatest Eclipse'].split(':'))
    jd = cal_to_jd(y, m, d, (h*3600+mi*60+se)/86400.0)
    return round((jd-EPOCH)/SYN) if r['Solar or Lunar'] == 'Solar' else round((jd-EPOCH)/SYN - 0.5)
for r in rows: r['_n'] = nfor(r)

def solve(ecl, user, C, slope, intc, label):
    ns = set(r['_n'] for r in ecl)
    parent = {n: n for n in ns}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for n in ns:                                   # link members 223 apart (bridge a 1-member gap)
        if n+223 in ns: parent[find(n)] = find(n+223)
        elif n+446 in ns: parent[find(n)] = find(n+446)
    comp = defaultdict(list)
    for n in ns: comp[find(n)].append(n)
    umin, umax = min(user), max(user)
    saros = {}; anc = fml = conflict = 0
    for members in comp.values():
        vals = [user[m] for m in members if m in user]
        if vals:
            v = Counter(vals).most_common(1)[0][0]; anc += 1
            if len(set(vals)) > 1: conflict += 1
        else:
            rep = min(members, key=lambda m: min(abs(m-umin), abs(m-umax)))
            v = formula(rep, C, slope, intc); fml += 1
        for m in members: saros[m] = v
    print(f"  {label}: {len(comp)} series ({anc} anchored, {fml} beyond-range formula); conflicts={conflict}; "
          f"saros range {min(saros.values())}..{max(saros.values())}")
    return saros

print(f"params: solar C={Cs} slope={ms:.7f}; lunar C={Cl} slope={ml:.7f}")
ssol = solve([r for r in rows if r['Solar or Lunar']=='Solar'], usol, Cs, ms, bs, "SOLAR")
slun = solve([r for r in rows if r['Solar or Lunar']=='Lunar'], ulun, Cl, ml, bl, "LUNAR")

# ---- verify against the reference list in-range, then write ----
umin_s, umax_s = min(usol), max(usol); umin_l, umax_l = min(ulun), max(ulun)
chk = miss = 0
for r in rows:
    n = r['_n']
    if r['Solar or Lunar'] == 'Solar' and n in usol:
        chk += 1; miss += (ssol[n] != usol[n])
    elif r['Solar or Lunar'] == 'Lunar' and n in ulun:
        chk += 1; miss += (slun[n] != ulun[n])
print(f"in-range verification vs reference list: {chk-miss}/{chk} exact ({miss} mismatches)")

header = fields[:fields.index('cum. seconds')+1] + ['SEC Saros #', 'LEC Saros #']
tmp = 'eclipse_catalog_full_formatted.csv.tmp'
with open(tmp, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(header)
    for r in rows:
        n = r['_n']
        if r['Solar or Lunar'] == 'Solar': sec, lec = ssol[n], 'x'
        else:                              sec, lec = 'x', slun[n]
        w.writerow([r[c] for c in fields if c != '_n'] + [sec, lec])
os.replace(tmp, 'eclipse_catalog_full_formatted.csv')
print(f"written in place; {len(header)} columns")
