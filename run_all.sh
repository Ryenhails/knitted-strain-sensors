#!/usr/bin/env bash
# Run the whole analysis, from the raw data to the check against the paper.
#   bash run_all.sh              4 parallel workers
#   JOBS=16 bash run_all.sh      16 parallel workers
set -euo pipefail
cd "$(dirname "$0")"
JOBS="${JOBS:-4}"

python scripts/0_check_data.py
python scripts/1_block_metrics.py --jobs "$JOBS"      # Section IV-C
python scripts/2_electromechanical.py                 # Section V   (Table IV, Figs. 5-6)
python scripts/3_train_estimators.py --jobs "$JOBS"   # Section VI-A (slow)
python scripts/4_joint_angle_error.py                 # Section VI-B, VI-C (Table V, Fig. 7)
python scripts/5_verify.py
