#!/bin/bash
# The whole analysis as one CPU job on Triton (about 20 minutes with 16 CPUs).
#   cd <repository>; sbatch slurm/run_all.sbatch
# The conda environment is the one of environment.yml; change the name below if yours differs.
#SBATCH --job-name=knit-sensors
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --output=%x_%j.out

module load mamba
source activate "${KNIT_ENV:-knit-sensors}"

echo "Start: $(date) on $(hostname)"
JOBS=$SLURM_CPUS_PER_TASK bash run_all.sh
EXIT_CODE=$?
echo "Exit Code: $EXIT_CODE"
echo "End Time: $(date)"
exit $EXIT_CODE
