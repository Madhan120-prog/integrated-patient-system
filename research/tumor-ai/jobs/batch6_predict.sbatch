#!/bin/bash
#SBATCH --job-name=batch6_predict
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/%x_fold%a_%A.out
# 6.2, prediction-only on the 5 even-bigger-block + 100,000-step models, each on its own VALIDATION patients:
# cut-off 0.2-0.5, plain or centre-weighted, largest or most confident piece. No test here: the test waits for the final recipe.
# Submit with --dependency=afterok:<batch6_folds job> so all 5 models exist.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
SRC=b6_huge_long_fold$SLURM_ARRAY_TASK_ID
[ "$SLURM_ARRAY_TASK_ID" = 0 ] && SRC=b5_huge_long_fold0
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --eval-only --from $SRC --name b6_predict_fold$SLURM_ARRAY_TASK_ID \
    --exp "B6 predict" --change "even bigger block + 100k steps: cut-off, centre-weighting, piece choice" \
    --cutoffs 0.2 0.3 0.4 0.5 --gauss --pieces largest confident
