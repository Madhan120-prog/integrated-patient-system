#!/bin/bash
#SBATCH --job-name=e11_outside
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/%x_%j.out
# E11, the "before" number: today's models, NO retraining, on outside test A (Radiogenomics half A, another hospital,
# never seen by any model). Run ONCE, after e10_prep. Nothing is chosen on these patients.
#   1. nnU-Net probabilities on outside A: ResEnc L 250 ep + nnU-Net 1000 ep, 5 folds each (Dataset001 models)
#   2. the final recipe (b6_avg_v1: 0.25 ours + 0.75 both nnU-Nets, cut-off 0.3, confident piece) -> outside_A_e11_recipe.csv
#   3. the same with ResEnc L 250 ep only -> outside_A_e11_resencL.csv: the like-for-like "before" for E10,
#      which retrains exactly these two models (ResEnc L 250 ep + our U-Net) with the new data.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
[ -f data/full/splits_multi.json ] || { echo "run e10_prep first"; exit 1; }
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_compile=f
for v in "resencL nnUNetTrainer_250epochs nnUNetResEncUNetLPlans" "1000ep nnUNetTrainer nnUNetPlans"; do
    set -- $v
    OUT=data/full/prob_nnunet_$1/outside_A
    [ -n "$(ls -A $OUT 2>/dev/null)" ] && { echo "$OUT already has files, not overwriting"; exit 1; }
    mkdir -p $OUT
    .venv/bin/nnUNetv2_predict -i data/full/outside_A/imagesTr -o $OUT -d 1 -c 3d_fullres -tr $2 -p $3 -f 0 1 2 3 4 --save_probabilities
done
cd model
OURS="b3_long_fold0 b5_long_fold1 b5_long_fold2 b5_long_fold3 b5_long_fold4"
ARGS="--data ../data/full/outside_A --splits ../data/full/splits_multi.json --key outside_test --gauss --cutoff 0.3 --piece confident --weight 0.25"
echo "=== final recipe"
../.venv/bin/python -u evaluate.py $ARGS --ours $OURS \
    --nnunet-prob ../data/full/prob_nnunet_resencL/outside_A ../data/full/prob_nnunet_1000ep/outside_A --out ../results/outside_A_e11_recipe.csv
echo "=== ResEnc L 250 ep only (like-for-like before E10)"
../.venv/bin/python -u evaluate.py $ARGS --ours $OURS \
    --nnunet-prob ../data/full/prob_nnunet_resencL/outside_A --out ../results/outside_A_e11_resencL.csv
