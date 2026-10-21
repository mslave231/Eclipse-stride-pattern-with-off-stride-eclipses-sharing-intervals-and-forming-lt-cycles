"""Stitch the six DE441 chunk CSVs into one full-span catalog (-13198..17189).
Chunks are adjacent (verified: no gaps/overlaps) and each is jd-sorted, so simple
concatenation in chronological order preserves global ordering. Produces both the
6-column deliverable and the detailed CSV, then verifies the result."""
import csv

ORDER = ['-13198_-8200', '-8199_-3200', '-3199_1800',
         '1801_6800', '6801_11800', '11801_17189']

def stitch(suffix, outname):
    total = 0
    with open(outname, 'w', newline='') as fout:
        w = None
        for i, tag in enumerate(ORDER):
            with open(f'eclipse_catalog_{tag}{suffix}.csv', newline='') as fin:
                r = csv.reader(fin)
                h = next(r)
                if i == 0:
                    w = csv.writer(fout); w.writerow(h)
                for row in r:
                    w.writerow(row); total += 1
    return total

n6 = stitch('', 'eclipse_catalog_full_-13198_17189.csv')
nd = stitch('_detailed', 'eclipse_catalog_full_-13198_17189_detailed.csv')
print(f'6-col    : {n6} rows -> eclipse_catalog_full_-13198_17189.csv')
print(f'detailed : {nd} rows -> eclipse_catalog_full_-13198_17189_detailed.csv')

# verify stitched 6-col: chronological order, span, solar/lunar tally
MONTHS = {m: i+1 for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}
def key(d):
    p = d.split(); return (int(p[0]), MONTHS[p[1]], int(p[2]))
prev = None; out_of_order = 0; first = last = None; solar = lunar = 0
with open('eclipse_catalog_full_-13198_17189.csv', newline='') as f:
    for row in csv.DictReader(f):
        k = key(row['Date'])
        if first is None: first = row['Date']
        last = row['Date']
        if prev is not None and k < prev: out_of_order += 1
        prev = k
        if row['Solar or Lunar'] == 'Solar': solar += 1
        else: lunar += 1
print(f'verify   : {solar+lunar} eclipses (solar {solar}, lunar {lunar}); '
      f'out-of-order rows: {out_of_order}')
print(f'  span: {first!r} .. {last!r}')
