"""Step 3 - paper Section VI-A: train and test the joint-angle estimators.

For each of the 28 bending recordings, three estimators (MLP, detrended MLP,
random forest) are trained on 80 % and tested on 20 % of every rate block, once
as regression (predict the angle; the paper's results) and once as 10-degree
classification (only for the comparison at the end of Section VI-C).
The test-window predictions are saved for step 4:

  results/predictions/reg/<sample>.npz   arrays mlp_angle, mlp_pred, mlp_rate, detr_..., rf_...
  results/predictions/cls/<sample>.npz   the same, plus *_true_class, *_pred_class

This is the slow step: about 3 CPU-minutes per recording and head, 3 CPU-hours
in total.  Recordings are independent, so they run in parallel.

    python scripts/3_train_estimators.py --jobs 8         all 28 recordings, both heads
    python scripts/3_train_estimators.py --sample A5      one recording (a quick test)
    python scripts/3_train_estimators.py --head reg       regression only
    python scripts/3_train_estimators.py --part 2/7       every 7th recording, starting with the 3rd
                                                          (how slurm/submit_parallel.sh splits the work)
"""
import argparse
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '1')        # one BLAS thread per worker process
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # makes `knitsensor` importable
from knitsensor import config, data, estimation  # noqa: E402


def run(task):
    rec, head = task
    results = estimation.run_recording(rec['path'], head)
    path = config.PREDICTIONS / head / (rec['sample'] + '.npz')
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **{'%s_%s' % (est, key): array
                                 for est, res in results.items() for key, array in res.items()})
    rmse = {est: estimation.scores(res)['rmse'] for est, res in results.items()}
    return '  %-3s %s  RMSE (deg): MLP %.2f, detrended MLP %.2f, RF %.2f -> %s' % (
        rec['sample'], head, rmse['mlp'], rmse['detr'], rmse['rf'], path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--jobs', type=int, default=4, help='recordings processed in parallel (default 4)')
    parser.add_argument('--head', choices=['reg', 'cls', 'both'], default='both')
    parser.add_argument('--sample', help='run only this recording, e.g. A5')
    parser.add_argument('--part', help='K/N: run only part K (0..N-1) of the recordings split into N parts')
    args = parser.parse_args()

    recordings = [r for r in data.bending_recordings() if args.sample in (None, r['sample'])]
    if args.part:
        k, n = map(int, args.part.split('/'))
        recordings = recordings[k::n]
    heads = ['reg', 'cls'] if args.head == 'both' else [args.head]
    tasks = [(rec, head) for rec in recordings for head in heads]
    print('training on %d recording(s) x %d head(s) ...' % (len(recordings), len(heads)), flush=True)
    with Pool(args.jobs) as pool:
        for line in pool.imap_unordered(run, tasks):
            print(line, flush=True)


if __name__ == '__main__':
    main()
