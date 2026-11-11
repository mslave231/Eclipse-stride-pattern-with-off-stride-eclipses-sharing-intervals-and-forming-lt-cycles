"""Reformat the consolidated catalog:
  1. Date  '-13198 Jun 22' -> '06/22/(13198)'  (negative astronomical years shown as (abs);
     (13198) = year -13198 = 13199 BCE, since year 0 = 1 BCE; positive years as-is)
  2. add 'cum. seconds' = whole TD seconds of greatest eclipse since -15000 Jan 1
     00:00:00, counted on the catalog's own calendar: Julian before 1582 Oct 15,
     Gregorian after (NASA convention) -- NOT a pure proleptic Julian count.

Checks: (a) round-trip every row through the engine's own jd_to_cal, and
(b) cross-check the second-counting against the 'Cum. Seconds' column (epoch -7000) of
the workbook Matt Slavik compiled from Yuk Tung Liu's catalogs
(https://ytliu.epizy.com/eclipse/).
Calendar arithmetic (cal_to_jd / jd_to_cal): Meeus, Astronomical Algorithms (1998), Ch. 7.
Writes a NEW file; the original consolidated CSV is left untouched.
"""
import csv, math

MONTHS = {m: i+1 for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}

# calendar -> JD (Meeus Ch.7): Julian before 1582 Oct 15, Gregorian after; floor
# throughout so it is the exact inverse of the engine's jd_to_cal for negative JD.
def cal_to_jd(year, month, day, hour=0, minute=0, second=0):
    Y, M = year, month
    if M <= 2:
        Y -= 1; M += 12
    if (year, month, day) >= (1582, 10, 15):
        A = math.floor(Y/100); B = 2 - A + math.floor(A/4)
    else:
        B = 0
    jd0 = math.floor(365.25*(Y+4716)) + math.floor(30.6001*(M+1)) + day + B - 1524.5
    return jd0 + (hour*3600 + minute*60 + second)/86400.0

# JD -> calendar: exact copy of eclipse_catalog.jd_to_cal (for round-trip checking).
def jd_to_cal(jd_tt):
    jd = jd_tt + 0.5; z = math.floor(jd); f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = math.floor((z-1867216.25)/36524.25); a = z + 1 + alpha - math.floor(alpha/4)
    b = a + 1524; c = math.floor((b-122.1)/365.25); d = math.floor(365.25*c)
    e = math.floor((b-d)/30.6001); dy = b - d - math.floor(30.6001*e)
    month = e-1 if e < 14 else e-13
    year = c-4716 if month > 2 else c-4715
    hours = f*24; h = int(hours); mins = (hours-h)*60; mi = int(mins); secs = (mins-mi)*60
    return year, month, dy, h, mi, secs

EPOCH_JD = cal_to_jd(-15000, 1, 1)

def parse_date(s):
    p = s.split(); return int(p[0]), MONTHS[p[1]], int(p[2])
def parse_td(s):
    h, mi, sec = s.split(':'); return int(h), int(mi), int(sec)
def fmt_date(y, m, d):
    return f"{m:02d}/{d:02d}/" + (f"({abs(y)})" if y < 0 else f"{y}")
def cum_seconds(y, m, d, h, mi, sec):
    days = round(cal_to_jd(y, m, d) - EPOCH_JD)
    return days*86400 + h*3600 + mi*60 + sec

# (b) cross-check vs Liu's Cum. Seconds (epoch -7000 Jan 1; -3999 Jun 14 02:19:58 = 94718600398)
liu = round(cal_to_jd(-3999,6,14) - cal_to_jd(-7000,1,1))*86400 + (2*3600+19*60+58)
print(f"Liu cross-check: computed {liu}  vs published 94718600398  diff {liu-94718600398}")

INFILE  = 'eclipse_catalog_full_-13198_17189.csv'
OUTFILE = 'eclipse_catalog_full_formatted.csv'
mism = nonmono = n = 0; prev = None; first = last = None
with open(INFILE, newline='') as fin, open(OUTFILE, 'w', newline='') as fout:
    r = csv.reader(fin); w = csv.writer(fout)
    w.writerow(next(r) + ['cum. seconds'])
    for row in r:
        y, m, d = parse_date(row[0]); h, mi, sec = parse_td(row[1])
        ry, rm, rd, rh, rmi, rs = jd_to_cal(cal_to_jd(y, m, d, h, mi, sec))
        if (ry, rm, rd, rh, rmi) != (y, m, d, h, mi) or round(rs) != sec:
            mism += 1
        cs = cum_seconds(y, m, d, h, mi, sec)
        if prev is not None and cs <= prev: nonmono += 1
        prev = cs
        row[0] = fmt_date(y, m, d)
        w.writerow(row + [cs]); n += 1
        if first is None: first = (row[0], row[1], cs)
        last = (row[0], row[1], cs)
print(f"rows written: {n}  ->  {OUTFILE}")
print(f"round-trip mismatches: {mism}   non-monotonic cum.sec: {nonmono}")
print(f"first: date {first[0]:>14}  TD {first[1]}  cum.sec {first[2]}")
print(f"last : date {last[0]:>14}  TD {last[1]}  cum.sec {last[2]}")
