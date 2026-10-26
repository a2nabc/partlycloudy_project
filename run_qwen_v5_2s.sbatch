#!/bin/bash -l
#SBATCH --job-name=qwen-v5-2s
#SBATCH --partition=gpu-v100-32g
#SBATCH --gpus=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --chdir=/scratch/work/bernada4/partlycloudy_project
#SBATCH --output=/scratch/work/bernada4/partlycloudy_project/qwen-v5-2s-%j.log

set -euo pipefail

module load scicomp-python-env/2025.2
export HF_HOME=/scratch/work/bernada4/hf_cache
unset HF_HUB_CACHE HF_XET_CACHE
export PYTHONUNBUFFERED=1

SCRIPT=code/annotation/qwen_whole_movie_scores_v5_2s.py

echo "Job ${SLURM_JOB_ID} started on $(hostname) at $(date)"
python -m py_compile "$SCRIPT"
python "$SCRIPT" prepare
srun python "$SCRIPT" infer

python "$SCRIPT" rank --top 20 --min-score 7 --max-other 10
python "$SCRIPT" rank --top 20 --min-score 7 --max-other 3
echo "Job ${SLURM_JOB_ID} completed at $(date)"