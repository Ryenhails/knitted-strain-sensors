"""Joint-angle estimation from one bending recording (paper Section VI-A).

  1. Windows: 0.25 s (25 samples) every 0.125 s (12 samples), cut separately from
     each of the three rate blocks.  Target = the mean measured angle of the window.
  2. Split: inside each block the first 80 % of the windows train, the last 20 %
     test.  The three training parts train one model; the three test parts are
     pooled for scoring.
  3. Input: each window low-pass filtered (2nd-order Butterworth, 20 Hz) and
     z-scored with the mean and SD of the training windows.
  4. Three estimators:
       mlp   MLP, 3 hidden layers x 128 ReLU, Adam (learning rate 1e-4),
             early stopping on 10 % of the training windows
       detr  the same MLP on windows from which one straight line, fitted to the
             resistance of the whole recording (its three blocks), was subtracted
       rf    random forest, 200 trees, maximum depth 20

The paper's results use regression ('reg': predict the angle).  The 10-degree
classification of the reference study ('cls': predict the class) is run the same
way and only enters the comparison in the last paragraph of Section VI-C.
"""
import numpy as np
from scipy.signal import butter, filtfilt
from scipy.stats import linregress

from . import config
from .data import read_recording

WINDOW, STEP = 25, 12
TRAIN_SHARE = 0.8
CLASS_WIDTH = 10.0                    # degrees; 16 classes over 0-150 deg
ESTIMATORS = ('mlp', 'detr', 'rf')


def new_model(head, estimator):
    """A fresh, unfitted model.  random_state is fixed, so results are repeatable."""
    if estimator == 'rf':
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        model = RandomForestRegressor if head == 'reg' else RandomForestClassifier
        return model(n_estimators=200, max_depth=20, random_state=42)
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    model = MLPRegressor if head == 'reg' else MLPClassifier
    return model(hidden_layer_sizes=(128, 128, 128), learning_rate_init=1e-4, max_iter=5000,
                 early_stopping=True, validation_fraction=0.1, n_iter_no_change=20, random_state=42)


def cut_windows(sample_index, angle, resistance):
    """Sliding windows over one rate block -> (windows, mean angle, sample indices)."""
    n = (len(resistance) - WINDOW) // STEP + 1
    starts = np.arange(n) * STEP
    take = starts[:, None] + np.arange(WINDOW)
    X, idx = resistance[take], sample_index[take].astype(float)
    target = np.array([angle[s:s + WINDOW].mean() for s in starts])
    ok = np.isfinite(X).all(axis=1)                         # drop windows with invalid readings
    return X[ok], target[ok], idx[ok]


def prepare(path):
    """The filtered (and detrended) windows of the three rate blocks of a recording."""
    segment, cycle, angle, resistance = read_recording(path)
    sample_index = np.arange(len(resistance))
    b, a = butter(2, 20.0, fs=config.FS, btype='low')

    blocks, in_blocks = [], np.zeros(len(resistance), bool)
    for s in np.unique(segment):
        here = segment == s
        if cycle[here].max() + 1 != 30:                      # rate blocks have 30 cycles
            continue
        in_blocks |= here
        steps = np.abs(np.diff(angle[here]))
        rate = config.BENDING_RATE_BY_STEP[round(float(np.median(steps[steps > 0])), 2)]
        X, target, idx = cut_windows(sample_index[here], angle[here], resistance[here])
        blocks.append(dict(rate=rate, angle=target, idx=idx, filtered=filtfilt(b, a, X, axis=1)))

    ok = in_blocks & np.isfinite(resistance)
    slope, intercept = linregress(sample_index[ok], resistance[ok])[:2]
    for blk in blocks:
        blk['detrended'] = blk['filtered'] - (slope * blk['idx'] + intercept)
    return blocks


def run_recording(path, head):
    """Train and test the three estimators of one head on one recording.

    Returns {estimator: dict(angle, pred, rate)} over the pooled test windows
    (classification adds true_class and pred_class; pred is then the class centre).
    """
    blocks = prepare(path)
    cut = [int(len(blk['angle']) * TRAIN_SHARE) for blk in blocks]
    out = {}
    for estimator in ESTIMATORS:
        feature = 'detrended' if estimator == 'detr' else 'filtered'
        X_train = np.vstack([blk[feature][:k] for blk, k in zip(blocks, cut)])
        X_test = np.vstack([blk[feature][k:] for blk, k in zip(blocks, cut)])
        angle_train = np.concatenate([blk['angle'][:k] for blk, k in zip(blocks, cut)])
        angle_test = np.concatenate([blk['angle'][k:] for blk, k in zip(blocks, cut)])
        mean, sd = X_train.mean(), X_train.std()
        X_train, X_test = (X_train - mean) / sd, (X_test - mean) / sd

        res = dict(angle=angle_test,
                   rate=np.concatenate([[blk['rate']] * (len(blk['angle']) - k) for blk, k in zip(blocks, cut)]))
        if head == 'reg':
            model = new_model(head, estimator).fit(X_train, angle_train)
            res['pred'] = np.clip(model.predict(X_test), 0.0, config.STROKE_DEG)
        else:
            to_class = lambda ang: np.clip(np.round(ang / CLASS_WIDTH), 0, 15).astype(int)
            model = new_model(head, estimator).fit(X_train, to_class(angle_train))
            res['true_class'], res['pred_class'] = to_class(angle_test), model.predict(X_test)
            res['pred'] = res['pred_class'] * CLASS_WIDTH
        out[estimator] = res
    return out


def scores(res):
    """Error of the pooled test windows of one estimator, in degrees."""
    error = res['pred'] - res['angle']
    out = dict(n_test=len(error),
               rmse=float(np.sqrt(np.mean(error ** 2))),
               mae=float(np.mean(np.abs(error))),
               r2=float(1 - np.sum(error ** 2) / np.sum((res['angle'] - res['angle'].mean()) ** 2)),
               within5=float(np.mean(np.abs(error) <= 5.0) * 100))
    if 'pred_class' in res:      # RMSE between class centres, as in the reference study
        out['rmse_class'] = float(np.sqrt(np.mean(((res['pred_class'] - res['true_class']) * CLASS_WIDTH) ** 2)))
    return out


def rmse_interval(error):
    """Bootstrap 95 % interval of the RMSE: resample the test windows 10^4 times."""
    squared = np.asarray(error, float) ** 2
    rng = np.random.default_rng(config.BOOT_SEED_RMSE)
    draws = rng.integers(0, len(squared), size=(config.N_BOOT, len(squared)))
    rmse = np.sqrt(squared[draws].mean(axis=1))
    return float(np.percentile(rmse, 2.5)), float(np.percentile(rmse, 97.5))
