"""Shared helpers for the pattern scripts. Everything is read from the repository's Outputs/ folder.

Time axis: cumulative seconds from -15000 Jan 01 00:00:00 TD (see DATA_DICTIONARY.md).
Direction convention: Direction A -> target = start - interval; Direction B -> target = start + interval.
"""
import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Outputs'
CUM = 'Cum. Seconds from -15000 Jan 01 00:00:00 TD'
DAY = 86400.0
YEAR = 31556925.0                         # 365.2422 days, used for interval years
CYCLE_YEAR = 365.242 * DAY                # used for cycle statistics
TEST_MIN, TEST_MAX = 56881000000.0, 1015815000000.0   # test range for interval targets
SIGN = {'A': -1.0, 'B': 1.0}              # target = start + SIGN[direction] * interval


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def count_value(s):
    """'~12' -> (12, True); '12' -> (12, False)."""
    return (int(s[1:]), True) if s.startswith('~') else (int(s), False)


def load_catalog():
    """All 145,356 eclipses in time order, as a dict of numpy arrays / lists."""
    stride = read_csv(OUT / '694-1,019 Stride Calculation.csv')
    det = read_csv(OUT / 'eclipse_catalog_full_-13198_17189_detailed.csv')
    assert len(stride) == len(det) == 145356
    fwd = [count_value(r['Forward Saros Count']) for r in det]
    rev = [count_value(r['Reverse Saros Count']) for r in det]
    return dict(
        date=[r['Date'] for r in stride], td=[r['TD of GE'] for r in stride],
        cum=np.array([int(r[CUM]) for r in stride], dtype=np.float64),
        kind=[r['Solar or Lunar'] for r in stride], type=[r['Type'] for r in stride],
        gamma=np.array([float(r['Gamma']) for r in stride]),
        solar_saros=[r['Solar Saros #'] for r in stride], lunar_saros=[r['Lunar Saros #'] for r in stride],
        fwd=np.array([v for v, _ in fwd]), fwd_est=np.array([e for _, e in fwd]),
        rev=np.array([v for v, _ in rev]), rev_est=np.array([e for _, e in rev]),
        stride_rows=stride)


def nearest_gap(cat, t):
    """Distance (s) from each time in t to the nearest catalog eclipse time."""
    k = np.clip(np.searchsorted(cat, t), 1, len(cat) - 1)
    return np.minimum(np.abs(cat[k] - t), np.abs(cat[k - 1] - t))


def load_intervals(path=OUT / 'Off-Stride Shared Intervals.csv'):
    """Shared intervals: band centres (mid of Max and Min) and averages, in seconds."""
    rows = read_csv(path)
    mx = np.array([float(r['Max (Seconds)']) for r in rows])
    mn = np.array([float(r['Min (Seconds)']) for r in rows])
    avg = np.array([float(r['Average (Seconds)']) for r in rows])
    return dict(avg=avg, mid=(mx + mn) / 2, max=mx, min=mn)
