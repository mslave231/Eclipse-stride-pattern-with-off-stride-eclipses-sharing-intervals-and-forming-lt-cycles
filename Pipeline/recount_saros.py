"""Recompute Fwd/Rev Saros Count grouping by TRUE series (kind, residue, time-cluster)
rather than by saros number -- so the one deep-BCE number collision (two different
series sharing -66) is counted as two series, and the 21 legitimate within-series
edge gaps stay as one series. Overwrites the two count columns in place.
Saros numbers themselves come from apply_saros.py (inside -3999..+4000: Matt Slavik's
reference numbering, matched to NASA's where verifiable; outside: this catalog's own extension)."""
import csv, math, os
from collections import defaultdict
EPOCH, SYN = 2451550.09766, 29.530588853

def cal_to_jd(y, mo, d, fr=0.0):
    Y, M = y, mo
    if M <= 2: Y -= 1; M += 12
    A = math.floor(Y/100); B = (2 - A + math.floor(A/4)) if (y, mo, d) >= (1582,10,15) else 0
    return math.floor(365.25*(Y+4716)) + math.floor(30.6001*(M+1)) + d + B - 1524.5 + fr
def pdate(s):
    mm, dd, yy = s.split('/'); return (-int(yy.strip('()')) if yy.startswith('(') else int(yy)), int(mm), int(dd)
def nfor(r):
    y, m, d = pdate(r['Date']); h, mi, se = map(int, r['TD of Greatest Eclipse'].split(':'))
    jd = cal_to_jd(y, m, d, (h*3600+mi*60+se)/86400.0)
    return round((jd-EPOCH)/SYN) if r['Solar or Lunar'] == 'Solar' else round((jd-EPOCH)/SYN - 0.5)

F = 'eclipse_catalog_full_formatted.csv'
with open(F, newline='') as f:
    rdr = csv.DictReader(f); fields = rdr.fieldnames; rows = list(rdr)

groups = defaultdict(list)
for i, r in enumerate(rows):
    n = nfor(r); C = 112 if r['Solar or Lunar'] == 'Solar' else 124
    groups[(r['Solar or Lunar'], (38*n + C) % 223)].append((n, i))

SPLIT = 50 * 223                                   # cluster break: >50 saros periods in n
fwd = [0]*len(rows); rev = [0]*len(rows)
n_series = 0; sizes = []; maxgap = 0
for key, lst in groups.items():
    lst.sort()
    clusters, cur = [], [lst[0]]
    for a, b in zip(lst, lst[1:]):
        gap = b[0] - a[0]
        if gap > SPLIT:
            clusters.append(cur); cur = [b]
        else:
            cur.append(b); maxgap = max(maxgap, gap // 223)
    clusters.append(cur)
    for cl in clusters:
        n_series += 1; M = len(cl); sizes.append(M)
        for pos, (n, i) in enumerate(cl):
            fwd[i] = pos + 1; rev[i] = M - pos

bad = sum(1 for i in range(len(rows)) if fwd[i] < 1 or rev[i] < 1)
print(f"true series: {n_series}   size min/median/max: {min(sizes)}/{sorted(sizes)[len(sizes)//2]}/{max(sizes)}")
print(f"max within-series gap: {maxgap} saros periods (must be small; clusters split at >50)")
print(f"rows with fwd/rev unset: {bad}")

tmp = F + '.tmp'
with open(tmp, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(fields)
    for i, r in enumerate(rows):
        r['Fwd Saros Count'] = fwd[i]; r['Rev Saros Count'] = rev[i]
        w.writerow([r[c] for c in fields])
os.replace(tmp, F)
print("rewrote Fwd/Rev Saros Count grouped by true series")
