#!/bin/bash
#SBATCH --job-name=anhui_v1
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/%x_%j.out
# Outside test 2, ONCE: v1 unchanged (the final-test recipe) on Anhui ASLS26, after anhui_prep. Nothing is chosen here.
#   1. nnU-Net probabilities: ResEnc L 250 ep + nnU-Net 1000 ep, 5 folds each
#   2. the recipe (0.25 ours + 0.75 both nnU-Nets, cut-off 0.3, confident piece) + each model alone -> results/anhui_asls_v1.csv
#   3. the four-level explanations on the same patients -> results/levels_eval_anhui_asls.csv
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
[ -f data/anhui/splits_asls.json ] || { echo "run anhui_prep first"; exit 1; }
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_compile=f
for v in "resencL nnUNetTrainer_250epochs nnUNetResEncUNetLPlans" "1000ep nnUNetTrainer nnUNetPlans"; do
    set -- $v
    OUT=data/full/prob_nnunet_$1/anhui_asls
    [ -n "$(ls -A $OUT 2>/dev/null)" ] && { echo "$OUT already has files, not overwriting"; exit 1; }
    mkdir -p $OUT
    .venv/bin/nnUNetv2_predict -i data/anhui/nnunet/imagesTr -o $OUT -d 1 -c 3d_fullres -tr $2 -p $3 -f 0 1 2 3 4 --save_probabilities
done
OURS="b3_long_fold0 b5_long_fold1 b5_long_fold2 b5_long_fold3 b5_long_fold4"
PROB="$PWD/data/full/prob_nnunet_resencL/anhui_asls $PWD/data/full/prob_nnunet_1000ep/anhui_asls"
cd model
../.venv/bin/python -u evaluate.py --data ../data/anhui/nnunet --splits ../data/anhui/splits_asls.json --key test \
    --ours $OURS --gauss --cutoff 0.3 --piece confident --nnunet-prob $PROB --weight 0.25 --out ../results/anhui_asls_v1.csv
cd ~/ips/research/tumor-ai/prototype
~/tumor-ai/.venv/bin/python -u levels_eval.py --set outside --data ~/tumor-ai/data/anhui/nnunet \
    --splits ~/tumor-ai/data/anhui/splits_asls.json --runs ~/tumor-ai/model/runs --cut 0.3 --ours $OURS --nnunet-prob $PROB \
    --model-text "25% our U-Net + 75% nnU-Net (ResEnc L 250 ep + nnU-Net 1000 ep), 5 folds" \
    --out ~/tumor-ai/results/levels_eval_anhui_asls.csv
