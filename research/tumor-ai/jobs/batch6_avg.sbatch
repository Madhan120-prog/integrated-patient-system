#!/bin/bash
#SBATCH --job-name=b6_avg
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/%x_task%a_%A.out
# 6.3: average our U-Net with nnU-Net on each fold's VALIDATION patients, every weight / cut-off / piece (ensemble.py).
# Choose which models when submitting (defaults = today's best: our 100k U-Net + nnU-Net ResEnc L and 1000 epochs):
#   OURS=b5   our bigger block + 100k (b3_long_fold0, b5_long_fold1-4)      OURS=b6  even bigger block + 100k (6.2)
#   NN="resencL 1000ep"   tags of data/full/prob_nnunet_<tag> folders, averaged together
# e.g. sbatch --export=ALL,OURS=b5,NN="resencL 1000ep",TAG=v1 --dependency=afterok:<prob jobs> jobs/batch6_avg.sbatch
# Each fold writes runs/b6_avg_<TAG>_fold<k>/ and refuses an existing name.
OURS=${OURS:-b5}; NN=${NN:-resencL 1000ep}; TAG=${TAG:-v1}; K=$SLURM_ARRAY_TASK_ID
if [ "$OURS" = b6 ]; then RUN=b6_huge_long_fold$K; [ "$K" = 0 ] && RUN=b5_huge_long_fold0
else RUN=b5_long_fold$K; [ "$K" = 0 ] && RUN=b3_long_fold0; fi
DIRS=""; for t in $NN; do DIRS="$DIRS ../data/full/prob_nnunet_$t/val_fold$K"; done
echo "fold $K: ours $RUN + nnU-Net $NN"
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u ensemble.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold $K --ours $RUN --nnunet $DIRS --name b6_avg_${TAG}_fold$K
