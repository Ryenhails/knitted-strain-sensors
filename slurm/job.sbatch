#!/bin/bash
# Generic job wrapper used by submit_parallel.sh: activates the environment and
# runs the command given after the script name.
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --output=%x_%j.out

module load mamba
source activate "${KNIT_ENV:-knit-sensors}"
echo "Start: $(date) on $(hostname): $*"
bash -c "$*"
EXIT_CODE=$?
echo "Exit Code: $EXIT_CODE"
echo "End Time: $(date)"
exit $EXIT_CODE
