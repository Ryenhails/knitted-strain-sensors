#!/bin/bash
# The whole analysis as parallel Triton jobs (about 10 minutes in total):
#   steps 0-2                one job      } run at the same time
#   step 3                   7 array jobs }
#   steps 4-5                one job, starts when all of the above have finished
# Run from the repository root:   bash slurm/submit_parallel.sh
set -euo pipefail
cd "$(dirname "$0")/.."
LOG="${KNIT_LOG_DIR:-.}"

a=$(sbatch --parsable --job-name=knit-steps0-2 --output="$LOG/%x_%j.out" slurm/job.sbatch \
    'python scripts/0_check_data.py && python scripts/1_block_metrics.py --jobs 8 && python scripts/2_electromechanical.py')
b=$(sbatch --parsable --job-name=knit-step3 --array=0-6 --output="$LOG/%x_%A_%a.out" slurm/job.sbatch \
    'python scripts/3_train_estimators.py --jobs 8 --part $SLURM_ARRAY_TASK_ID/7')
c=$(sbatch --parsable --job-name=knit-steps4-5 --dependency=afterok:$a:$b --cpus-per-task=2 --mem=8G \
    --output="$LOG/%x_%j.out" slurm/job.sbatch \
    'python scripts/4_joint_angle_error.py && python scripts/5_verify.py')
echo "submitted: steps 0-2 = $a, step 3 = $b (array 0-6), steps 4-5 = $c (waits for the others)"
