"""Quick structural sanity check on chunk CSVs (no ephemeris load).
Usage: python sanity_check.py [path y0 y1]...   default = the two BCE chunks.
Checks: row count, eclipse rate, solar/lunar balance, type mix, date validity,
magnitude range, and that consecutive chunks' requested YEAR RANGES are adjacent.
(It does not test the exact boundary instants; since 2026-10-20 the engine scans the
half-open interval [START Jan 1, END+1 Jan 1), so adjacent ranges tile exactly.)"""
import csv, sys, calendar
from collections import Counter

args = sys.argv[1:]
if args:
    files = [(args[i], int(args[i+1]), int(args[i+2])) for i in range(0, len(args), 3)]
else:
    files = [('eclipse_catalog_-13198_-8200.csv', -13198, -8200),
             ('eclipse_catalog_-8199_-3200.csv', -8199, -3200)]

EXPECT_COLS = ['Date', 'TD of Greatest Eclipse', 'Delta T (s)',
               'Solar or Lunar', 'Type', 'Magnitude']

def y(d):  return int(d.split()[0])
def dom(d): return int(d.split()[2])

loaded = []
for path, y0, y1 in files:
    rows = list(csv.DictReader(open(path, newline='')))
    loaded.append((path, y0, y1, rows))
    n = len(rows)
    span = y1 - y0 + 1
    years = [y(r['Date']) for r in rows]
    days  = [dom(r['Date']) for r in rows]
    kinds = Counter(r['Solar or Lunar'] for r in rows)
    sol = Counter(r['Type'] for r in rows if r['Solar or Lunar'] == 'Solar')
    lun = Counter(r['Type'] for r in rows if r['Solar or Lunar'] == 'Lunar')
    mags = [float(r['Magnitude']) for r in rows]
    # validity checks
    cols_ok = list(rows[0].keys()) == EXPECT_COLS
    bad_day = sum(1 for d in days if d < 1 or d > 31)
    bad_kind = sum(1 for r in rows if r['Solar or Lunar'] not in ('Solar', 'Lunar'))
    out_of_range = sum(1 for yy in years if yy < y0 or yy > y1)
    bad_td = 0
    for r in rows:
        try:
            h, m, s = map(int, r['TD of Greatest Eclipse'].split(':'))
            if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60): bad_td += 1
        except Exception:
            bad_td += 1
    bal = kinds['Solar'] / kinds['Lunar'] if kinds['Lunar'] else float('nan')
    print(f"=== {path} ===")
    print(f"  columns match 6-col spec : {cols_ok}  ({list(rows[0].keys())})")
    print(f"  rows                     : {n}")
    print(f"  requested / actual years : {y0}..{y1} ({span} yr)  |  data {min(years)}..{max(years)}")
    print(f"  eclipse rate             : {n/span:.2f} /yr")
    print(f"  Solar / Lunar            : {kinds['Solar']} / {kinds['Lunar']}  (ratio {bal:.3f})")
    print(f"  Solar types              : {dict(sol)}")
    print(f"  Lunar types              : {dict(lun)}")
    print(f"  magnitude range          : {min(mags):.4f} .. {max(mags):.4f}")
    print(f"  VALIDITY (want all 0)    : bad_day={bad_day} bad_TD={bad_td} bad_kind={bad_kind} year_out_of_range={out_of_range}")
    print(f"  first row : {rows[0]['Date']:>14} | {rows[0]['TD of Greatest Eclipse']} | {rows[0]['Solar or Lunar']:5} | {rows[0]['Type']:9} | mag {rows[0]['Magnitude']}")
    print(f"  last  row : {rows[-1]['Date']:>14} | {rows[-1]['TD of Greatest Eclipse']} | {rows[-1]['Solar or Lunar']:5} | {rows[-1]['Type']:9} | mag {rows[-1]['Magnitude']}")
    print()

# boundary gap/overlap between consecutive chunks (sorted by start year)
loaded.sort(key=lambda x: x[1])
print("=== chunk boundaries (gap / overlap check) ===")
for a, b in zip(loaded, loaded[1:]):
    a_end_yr = a[2]; b_start_yr = b[1]
    a_last = a[3][-1]['Date']; b_first = b[3][0]['Date']
    status = "OK adjacent" if b_start_yr == a_end_yr + 1 else f"!! gap/overlap ({a_end_yr} -> {b_start_yr})"
    print(f"  {a[0]} (ends yr {a_end_yr}, last {a_last!r})")
    print(f"    -> {b[0]} (starts yr {b_start_yr}, first {b_first!r}) : {status}")
