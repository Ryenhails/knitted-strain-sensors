"""Spearman rank correlation with a bootstrap interval over designs (Figs. 6 and 7)."""
import numpy as np
from scipy.stats import spearmanr

from . import config


def spearman(x, y):
    """dict(n, rho, p, ci_lo, ci_hi).

    The 95 % interval comes from resampling the (x, y) pairs with replacement
    10^4 times; resamples with fewer than three distinct values on either side
    are skipped.  Pairs with a missing value are left out.
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    rho, p = spearmanr(x, y)
    rng = np.random.default_rng(config.BOOT_SEED_RHO)
    draws = []
    for _ in range(config.N_BOOT):
        i = rng.integers(0, len(x), len(x))
        if len(np.unique(x[i])) >= 3 and len(np.unique(y[i])) >= 3:
            draws.append(spearmanr(x[i], y[i]).correlation)
    draws = np.array(draws)
    draws = draws[np.isfinite(draws)]
    return dict(n=len(x), rho=float(rho), p=float(p),
                ci_lo=float(np.percentile(draws, 2.5)), ci_hi=float(np.percentile(draws, 97.5)))
