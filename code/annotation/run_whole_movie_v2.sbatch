#!/bin/bash
#SBATCH --job-name=qwen-movie-v2
#SBATCH --partition=gpu-v100-32g
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/qwen_whole_movie_scores_v2_no_context/slurm-%j.log
set -euo pipefail
cd /scratch/work/bernada4/partlycloudy_project
export HF_HOME=/scratch/work/bernada4/hf_cache
export HF_HUB_OFFLINE=1
export OMP_NUM_THREADS=4
export USE_TF=0
export USE_FLAX=0
python code/annotation/qwen_whole_movie_scores.py infer
python code/annotation/qwen_whole_movie_scores.py rank
