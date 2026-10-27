"""Electromechanical metric definitions (paper Table I), shared by both rigs.

Following Schepers et al., computed on the cycle-averaged loading curve of
dR/R0 against position.  Position is strain in percent (tensile rig, and the
bending rig after angle-to-strain conversion) or the joint angle in degrees.
Both rigs pass their own grid and window, chosen so that the stroke always
spans 600 grid bins and the sliding window 20 bins (1/30 of the stroke):

    strain axis   grid 0.1 %,   window 2 %,  stroke 60 %
    angle axis    grid 0.25 deg, window 5 deg, stroke 150 deg
"""
from dataclasses import dataclass

import numpy as np

WR_RISE = 2e-3          # dR/R0 must rise by more than this across one window
R2_MIN = 0.96           # linear-range criterion


@dataclass(frozen=True)
class Axis:
    grid: float         # bin width
    span: float         # sliding-window width
    xmax: float         # samples outside [0, xmax] are dropped
    slope_scale: float  # converts the fitted slope to the reported gauge factor
    back_off: float     # end of stroke for the fall-from-peak reading


STRAIN = Axis(grid=0.1, span=2.0, xmax=100.0, slope_scale=100.0, back_off=1.0)  # GF per unit strain
ANGLE = Axis(grid=0.25, span=5.0, xmax=150.0, slope_scale=1.0, back_off=2.5)    # GF per degree


# ---------------------------------------------------------------- curves

def avg_curves(x, y, C, cycles, grid, xmax):
    """Mean loading and unloading curve on the position grid.

    Each cycle is split at its maximum position into a loading and an unloading
    half; samples are binned by position and averaged over the listed cycles.
    Returns (grid values, loading, unloading, counts loading, counts unloading,
    number of samples dropped outside [0, xmax]).
    """
    nb = int(round(xmax / grid)) + 1
    accL, cntL = np.zeros(nb), np.zeros(nb)
    accU, cntU = np.zeros(nb), np.zeros(nb)
    dropped = 0
    for cy in cycles:
        m = C == cy
        e, v = x[m], y[m]
        good = np.isfinite(v)
        e, v = e[good], v[good]
        if len(e) < 10:
            continue
        pk = int(np.argmax(e))
        for sl, acc, cnt in ((slice(0, pk + 1), accL, cntL),
                             (slice(pk, None), accU, cntU)):
            ee, vv = e[sl], v[sl]
            keep = (ee >= 0) & (ee <= xmax)
            dropped += int((~keep).sum())
            ee, vv = ee[keep], vv[keep]
            if not len(ee):
                continue
            i = np.clip((ee / grid + 0.5).astype(int), 0, nb - 1)
            np.add.at(acc, i, vv)
            np.add.at(cnt, i, 1)
    with np.errstate(invalid='ignore'):
        L = np.where(cntL > 0, accL / np.maximum(cntL, 1), np.nan)
        U = np.where(cntU > 0, accU / np.maximum(cntU, 1), np.nan)
    return np.arange(nb) * grid, L, U, cntL, cntU, dropped


def fill_gaps(g, y):
    """Linear interpolation across empty bins inside the covered range."""
    ok = np.isfinite(y)
    if ok.sum() < 5:
        return y, 0
    i0, i1 = np.where(ok)[0][[0, -1]]
    out = y.copy()
    hole = (~ok) & (np.arange(len(y)) > i0) & (np.arange(len(y)) < i1)
    if hole.any():
        out[hole] = np.interp(g[hole], g[ok], y[ok])
    return out, int(hole.sum())


# ---------------------------------------------------------------- metrics

def working_range(g, y, span, rise=WR_RISE):
    """Longest interval over which dR/R0 rises by more than `rise` per window.

    The curve is smoothed with a moving average one window wide and the rise is
    taken between two positions one window apart.  Returns (start, end, index of
    start, index of end) or None.
    """
    ok = np.isfinite(y)
    idx = np.where(ok)[0]
    if len(idx) < 5:
        return None
    gg, v = g[idx], y[idx]
    step = g[1] - g[0]
    K = max(2, int(round(span / step)))
    h = K // 2
    if len(v) < 2 * K + 2:
        return None
    cs = np.concatenate([[0.0], np.cumsum(v)])
    sm = (cs[K:] - cs[:-K]) / K              # mean of v[i:i+K], centred at i+h
    n = len(sm) - K
    if n <= 0:
        return None
    r = sm[K:K + n] - sm[0:n]                # rise between positions one window apart
    good = r > rise
    best, cur = (0, -1, -1), None
    for i, gd in enumerate(good):
        if gd and cur is None:
            cur = i
        elif not gd and cur is not None:
            if i - cur > best[0]:
                best = (i - cur, cur, i - 1)
            cur = None
    if cur is not None and len(good) - cur > best[0]:
        best = (len(good) - cur, cur, len(good) - 1)
    if best[0] < 1:
        return None
    lo_i = best[1] + h
    hi_i = min(best[2] + h + K, len(gg) - 1)
    a, b = float(gg[lo_i]), float(gg[hi_i])
    if b - a < span:                         # shorter than one window: no range
        return None
    return a, b, idx[lo_i], idx[hi_i]


def linear_range(g, y, i0, i1, r2_min=R2_MIN, slope_scale=1.0):
    """Longest sub-interval of [i0, i1] whose straight-line fit has R2 >= r2_min.

    Returns (start, end, gauge factor = slope * slope_scale, R2) or None.
    """
    sel = np.arange(i0, i1 + 1)
    sel = sel[np.isfinite(y[sel])]
    if len(sel) < 5:
        return None
    x, v = g[sel], y[sel]
    n = len(x)
    cx = np.concatenate([[0.0], np.cumsum(x)])
    cy = np.concatenate([[0.0], np.cumsum(v)])
    cxx = np.concatenate([[0.0], np.cumsum(x * x)])
    cyy = np.concatenate([[0.0], np.cumsum(v * v)])
    cxy = np.concatenate([[0.0], np.cumsum(x * v)])
    for span in range(n, 4, -1):             # longest first
        a = np.arange(0, n - span + 1)
        b = a + span
        m = float(span)
        sx = cx[b] - cx[a]; sy = cy[b] - cy[a]
        sxx = cxx[b] - cxx[a]; syy = cyy[b] - cyy[a]
        sxy = cxy[b] - cxy[a]
        vxx = sxx - sx * sx / m
        vyy = syy - sy * sy / m
        vxy = sxy - sx * sy / m
        with np.errstate(invalid='ignore', divide='ignore'):
            r2 = np.where((vxx > 0) & (vyy > 0), vxy * vxy / (vxx * vyy), -1.0)
        hit = np.where(r2 >= r2_min)[0]
        if len(hit):
            k = int(hit[np.argmax(r2[hit])])
            slope = vxy[k] / vxx[k]
            return (float(x[a[k]]), float(x[b[k] - 1]),
                    float(slope * slope_scale), float(r2[k]))
    return None


def hysteresis(g, L, U, i0, i1):
    """Largest position gap between loading and unloading at equal dR/R0,
    inside the working range [i0, i1]."""
    sl = np.arange(i0, i1 + 1)
    ok = np.isfinite(L[sl]) & np.isfinite(U[sl])
    sl = sl[ok]
    if len(sl) < 5:
        return np.nan
    gg = g[sl]
    lo = max(np.min(L[sl]), np.min(U[sl]))
    hi = min(np.max(L[sl]), np.max(U[sl]))
    if not np.isfinite(lo) or hi <= lo:
        return np.nan
    levels = np.linspace(lo, hi, 400)
    oL, oU = np.argsort(L[sl]), np.argsort(U[sl])
    gl = np.interp(levels, L[sl][oL], gg[oL])
    gu = np.interp(levels, U[sl][oU], gg[oU])
    return float(np.max(np.abs(gl - gu)))


def cyclic_stability(r, C, cycles):
    """SD of the resistance across cycles at each point of the cycle, averaged.

    Returns (raw SD, SD after removing a linear trend across cycles at each
    point of the cycle).  The paper reports the detrended value.
    """
    segs = [r[C == cy] for cy in cycles]
    segs = [v for v in segs if len(v)]
    if len(segs) < 5:
        return np.nan, np.nan
    n = min(len(v) for v in segs)
    if n < 10:
        return np.nan, np.nan
    M = np.vstack([v[:n] for v in segs])
    with np.errstate(invalid='ignore'):
        raw = float(np.nanmean(np.nanstd(M, axis=0)))
        t = np.arange(M.shape[0], dtype=float)
        tm = t - t.mean()
        slope = np.nansum(tm[:, None] * (M - np.nanmean(M, axis=0)), axis=0) / np.sum(tm ** 2)
        det = float(np.nanmean(np.nanstd(M - tm[:, None] * slope[None, :], axis=0)))
    return raw, det


def fall_from_peak(g, L, back_off):
    """How far (% of the peak) the loading curve has come down by the end of the
    stroke, read `back_off` short of the maximum position to skip the reversal."""
    ok = np.isfinite(L)
    if ok.sum() < 5:
        return np.nan
    emax = g[ok][-1]
    j = int(np.argmin(np.abs(g - (emax - back_off))))
    pk = float(np.nanmax(L[g <= emax - back_off]))
    return (100.0 * (pk - L[j]) / pk) if pk else np.nan


def curve_metrics(x, y, C, cycles, axis):
    """All curve-based metrics of one analysis window, loading direction.

    x position on `axis`, y = dR/R0, C cycle number of each sample.
    Returns a dict and the averaged loading curve (grid, L).
    """
    grid, L, U, _, _, _ = avg_curves(x, y, C, cycles, axis.grid, axis.xmax)
    L, _ = fill_gaps(grid, L)
    U, _ = fill_gaps(grid, U)
    out = dict(peak_dRR0=float(np.nanmax(L)), peak_x=float(grid[int(np.nanargmax(L))]),
               fall_pct=fall_from_peak(grid, L, axis.back_off))
    w = working_range(grid, L, axis.span)
    if w:
        lo, hi, i0, i1 = w
        out.update(WR_lo=lo, WR_hi=hi, WR=hi - lo, H=hysteresis(grid, L, U, i0, i1))
        lr = linear_range(grid, L, i0, i1, slope_scale=axis.slope_scale)
        if lr:
            out.update(LR_lo=lr[0], LR_hi=lr[1], LR=lr[1] - lr[0], GF=lr[2], R2=lr[3])
    return out, (grid, L)
