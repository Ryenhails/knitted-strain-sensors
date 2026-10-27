"""The analysis protocol of paper Section IV-C: from one recording to the
metrics of its three rate blocks.

A recording is a sequence of segments (the `Segment` column):

  tensile   precondition 200 cycles | rest 5 min | reference 20 | block 200 | rest
            | block 200 | rest | block 200 | rest | reference 20
  bending   reference 20 | rest 2 min | block 30 | rest | block 30 | rest
            | block 30 | rest | reference 20

The three blocks run the slow (A), medium (B) and fast (C) rate in the order of
the file name, e.g. 'BCA'.  For every block:

  1. R0 = mean resistance over the last half of the rest before the block.  The
     first block has no rest of its own and uses the nearest one: on the tensile
     rig the rest before the first reference, on the bending rig the rest after it.
  2. The first cycles are discarded (50 of 200 tensile, 10 of 30 bending).
  3. dR/R0 of the remaining cycles is averaged into one loading curve against
     strain, and the metrics of Table I are computed on it (see metrics.py).
"""
import numpy as np

from . import config
from .data import read_recording
from .metrics import ANGLE, STRAIN, curve_metrics, cyclic_stability


def list_segments(segment, cycle, position, rate_by_step):
    """One entry per segment, in recording order: dict(segment, kind, rate, n_cycles).

    kind is 'rest' (1 cycle), 'reference' (20 cycles) or 'block'.  The rate is
    recognised from the median position step between consecutive samples.
    """
    out = []
    for s in np.unique(segment):
        here = segment == s
        n_cycles = int(cycle[here].max()) + 1
        steps = np.abs(np.diff(position[here]))
        steps = steps[steps > 0]
        step = round(float(np.median(steps)), 2) if len(steps) else 0.0
        kind = 'rest' if n_cycles == 1 else ('reference' if n_cycles == 20 else 'block')
        out.append(dict(segment=int(s), kind=kind, rate=rate_by_step.get(step, ''), n_cycles=n_cycles))
    return out


def rest_r0(segment, resistance, rest):
    """R0: mean resistance over the last half of a rest segment."""
    r = resistance[segment == rest['segment']]
    r = r[np.isfinite(r)]
    return float(np.mean(r[len(r) // 2:]))


def block_metrics(segment, cycle, position, resistance, block, rest, drop, axis):
    """Metrics of one rate block on one position axis.

    Returns (dict of metrics, averaged loading curve as (grid, dR/R0)).
    """
    R0 = rest_r0(segment, resistance, rest)
    here = segment == block['segment']
    r, c = resistance[here], cycle[here]
    kept = np.arange(drop, block['n_cycles'])               # cycles after the discarded ones
    out, curve = curve_metrics(position[here], (r - R0) / R0, c, kept, axis)
    out['R0'] = R0
    out['stab_raw'], out['stab'] = cyclic_stability(r, c, kept)
    out['stab_drift_share'] = 1 - (out['stab'] / out['stab_raw']) ** 2
    return out, curve


# ---------------------------------------------------------------- tensile rig

def analyse_tensile(rec):
    """One tensile recording -> dict(blocks=[3 rows], curve=medium-block curve,
    settling=[4 rows], see `settling` below)."""
    segment, cycle, distance, resistance = read_recording(rec['path'])
    strain = distance / rec['L0'] * 100.0                    # percent
    segs = list_segments(segment, cycle, distance, config.TENSILE_RATE_BY_STEP)
    rests = [s for s in segs if s['kind'] == 'rest']
    first_reference = [s for s in segs if s['kind'] == 'reference'][0]
    precondition, *rate_blocks = [s for s in segs if s['kind'] == 'block']

    rows, curve = [], None
    for position, block in enumerate(rate_blocks, start=1):
        if position == 1:
            rest = [s for s in rests if s['segment'] < first_reference['segment']][-1]
        else:
            rest = [s for s in rests if s['segment'] < block['segment']][-1]
        m, c = block_metrics(segment, cycle, strain, resistance, block, rest,
                             config.TENSILE_DROP_CYCLES, STRAIN)
        rows.append(dict(sample=rec['sample'], design=rec['design'], rate=block['rate'],
                         position=position, L0=rec['L0'], **m))
        if block['rate'] == config.MEDIUM:
            curve = c

    settle = [settling(rec, name, segment, cycle, strain, resistance, block)
              for name, block in zip(['precondition', 'block1', 'block2', 'block3'],
                                     [precondition] + rate_blocks)]
    return dict(blocks=rows, curve=curve, settling=settle)


def settling(rec, name, segment, cycle, strain, resistance, block):
    """How much R0 and GF still change inside a block (paper Section V-A).

    Per cycle: R0 = mean resistance below 1 % strain, GF = slope of dR/R0 against
    strain between 10 and 50 % on the loading half.  Reported as the mean of the
    last 50 cycles relative to the mean of the first 50, minus one.
    """
    here = segment == block['segment']
    eps, r, c = strain[here], resistance[here], cycle[here]
    r0_per_cycle, gf_per_cycle = [], []
    for cy in np.unique(c):
        e, x = eps[c == cy], r[c == cy]
        ok = np.isfinite(x)
        e, x = e[ok], x[ok]
        if len(x) < 20 or not (e <= 1.0).any() or not (e >= 59.0).any():
            continue
        r0 = float(x[e <= 1.0].mean())
        if not r0 > 0:
            continue
        top = int(np.argmax(e))                              # end of the loading half
        e, x = e[:top + 1], x[:top + 1]
        fit = (e >= 10.0) & (e <= 50.0)
        gf = np.polyfit(e[fit] / 100.0, (x[fit] - r0) / r0, 1)[0] if fit.sum() >= 10 else np.nan
        r0_per_cycle.append(r0)
        gf_per_cycle.append(gf)

    def change(values):
        first, last = np.nanmean(values[:50]), np.nanmean(values[-50:])
        return last / first - 1.0

    return dict(sample=rec['sample'], block=name, rate=block['rate'], cycles=len(r0_per_cycle),
                R0_change=change(r0_per_cycle), GF_change=change(gf_per_cycle))


# ---------------------------------------------------------------- bending rig

def analyse_bending(rec):
    """One bending recording -> dict(blocks=[3 rows], curve=medium-block curve).

    The metrics are computed on the strain axis, after converting the joint
    angle with the robot calibration: strain = angle * 61 mm / 150 deg / L0.
    On the angle axis only the peak angle and the start of the working range
    are kept (paper Section V-B).
    """
    segment, cycle, angle, resistance = read_recording(rec['path'])
    strain = angle * (config.STROKE_MM / config.STROKE_DEG) / rec['L0'] * 100.0
    segs = list_segments(segment, cycle, angle, config.BENDING_RATE_BY_STEP)
    rests = [s for s in segs if s['kind'] == 'rest']
    rate_blocks = [s for s in segs if s['kind'] == 'block']

    rows, curve = [], None
    for position, block in enumerate(rate_blocks, start=1):
        if position == 1:
            rest = rests[0]
        else:
            rest = [s for s in rests if s['segment'] < block['segment']][-1]
        m, c = block_metrics(segment, cycle, strain, resistance, block, rest,
                             config.BENDING_DROP_CYCLES, STRAIN)
        a, _ = block_metrics(segment, cycle, angle, resistance, block, rest,
                             config.BENDING_DROP_CYCLES, ANGLE)
        rows.append(dict(sample=rec['sample'], design=rec['design'], history=rec['history'],
                         rate=block['rate'], position=position, L0=rec['L0'],
                         stroke_strain=config.STROKE_MM / rec['L0'] * 100.0,
                         peak_angle=a['peak_x'], WR_start_angle=a.get('WR_lo', np.nan), **m))
        if block['rate'] == config.MEDIUM:
            curve = c
    return dict(blocks=rows, curve=curve)
