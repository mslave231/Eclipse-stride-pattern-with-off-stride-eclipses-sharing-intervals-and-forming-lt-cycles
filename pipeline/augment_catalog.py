"""Add Gamma (from the detailed CSV) and Year/Month/Day columns directly into
eclipse_catalog_full_formatted.csv, in place. Joins formatted<->detailed by row
order and validates date+TD+kind+magnitude on every row before trusting the join.
Writes atomically via a temp file + os.replace."""
import csv, os

FMT = 'eclipse_catalog_full_formatted.csv'
DET = 'eclipse_catalog_full_-13198_17189_detailed.csv'
MONTHS = {m: i+1 for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}

def parse_fmt(s):                       # '06/06/(13198)' -> (y, m, d)
    mm, dd, yy = s.split('/')
    y = -int(yy.strip('()')) if yy.startswith('(') else int(yy)
    return y, int(mm), int(dd)
def parse_det(s):                       # '-13198 Jun 06' -> (y, m, d)
    p = s.split(); return int(p[0]), MONTHS[p[1]], int(p[2])

with open(DET, newline='') as f:
    det = list(csv.DictReader(f))
with open(FMT, newline='') as f:
    fmt = list(csv.DictReader(f))
assert len(fmt) == len(det), f"row-count mismatch: fmt {len(fmt)} vs det {len(det)}"

mismatch = 0
out = []
for rf, rd in zip(fmt, det):
    if (parse_fmt(rf['Date']) != parse_det(rd['Date'])
            or rf['TD of Greatest Eclipse'] != rd['TD of GE']
            or rf['Solar or Lunar'] != rd['Kind']
            or rf['Magnitude'] != rd['Magnitude']):
        mismatch += 1
        continue
    y, m, d = parse_fmt(rf['Date'])
    gamma = rd['Gamma'][1:] if rd['Gamma'].startswith('+') else rd['Gamma']
    out.append([rf['Date'], rf['TD of Greatest Eclipse'], rf['Delta T (s)'],
                rf['Solar or Lunar'], rf['Type'], gamma, rf['Magnitude'],
                y, m, d, rf['cum. seconds']])

print(f"rows: {len(fmt)}   alignment mismatches: {mismatch}")
if mismatch == 0:
    header = ['Date', 'TD of Greatest Eclipse', 'Delta T (s)', 'Solar or Lunar',
              'Type', 'Gamma', 'Magnitude', 'Year', 'Month', 'Day', 'cum. seconds']
    tmp = FMT + '.tmp'
    with open(tmp, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(out)
    os.replace(tmp, FMT)
    print(f"written IN PLACE -> {FMT}  ({len(out)} rows, {len(header)} columns)")
    print("columns:", header)
else:
    print("ABORTED — no rows written (alignment failed)")
