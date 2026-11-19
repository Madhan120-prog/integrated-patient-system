#!/bin/bash
#SBATCH --job-name=e10_outside
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/%x_%j.out
# E10 on outside test A, ONCE, after all e10_nnunet and e10_unet folds finished. The same recipe as E11's
# like-for-like row (0.25 ours + 0.75 ResEnc L 250 ep, cut-off 0.3, confident piece), only the models are retrained.
# Compare with results/outside_A_e11_resencL.csv. Nothing is chosen on these patients.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_compile=f
OUT=data/full/prob_nnunet_e10_resencL/outside_A
[ -n "$(ls -A $OUT 2>/dev/null)" ] && { echo "$OUT already has files, not overwriting"; exit 1; }
mkdir -p $OUT
.venv/bin/nnUNetv2_predict -i data/full/outside_A/imagesTr -o $OUT -d 2 -c 3d_fullres \
    -tr nnUNetTrainer_250epochs -p nnUNetResEncUNetLPlans -f 0 1 2 3 4 --save_probabilities
cd model
../.venv/bin/python -u evaluate.py --data ../data/full/outside_A --splits ../data/full/splits_multi.json --key outside_test \
    --ours e10_unet_fold0 e10_unet_fold1 e10_unet_fold2 e10_unet_fold3 e10_unet_fold4 --gauss --cutoff 0.3 --piece confident \
    --nnunet-prob ../$OUT --weight 0.25 --out ../results/outside_A_e10.csv
