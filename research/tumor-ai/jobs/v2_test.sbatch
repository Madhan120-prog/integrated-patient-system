#!/bin/bash
#SBATCH --job-name=v2_test
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/%x_%j.out
# v2's locked Anhui test slice, ONCE, after all 5 v2 folds AND anhui_v1 finished. Nothing is chosen here.
# Same model type (ResEnc L 250 ep) trained on three data sizes, on the same locked patients:
#   v1 data (Lung1) -> E10 data (+ Radiogenomics B + MSD) -> v2 data (+ Anhui training)  + the full v1 recipe
# Also v2 on outside test A (compare: E11 0.672, E10 outside_A_e10.csv).
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_compile=f
V1=data/full/prob_nnunet_resencL/anhui_asls
[ -n "$(ls $V1/*.npz 2>/dev/null)" ] || { echo "run anhui_v1 first"; exit 1; }
for k in 0 1 2 3 4; do
    [ -f runs/nnunet_full/Dataset003_LungV2/nnUNetTrainer_250epochs__nnUNetResEncUNetLPlans__3d_fullres/fold_$k/checkpoint_final.pth ] \
        || { echo "v2 fold $k not finished"; exit 1; }
done
pred() {   # dataset, input folder, output folder
    [ -n "$(ls -A $3 2>/dev/null)" ] && { echo "$3 already has files, not overwriting"; exit 1; }
    mkdir -p $3
    .venv/bin/nnUNetv2_predict -i $2 -o $3 -d $1 -c 3d_fullres -tr nnUNetTrainer_250epochs -p nnUNetResEncUNetLPlans -f 0 1 2 3 4 --save_probabilities
}
E10A=data/full/prob_nnunet_e10_resencL/anhui_v2test
V2A=data/full/prob_nnunet_v2_resencL/anhui_v2test
V2O=data/full/prob_nnunet_v2_resencL/outside_A
pred 2 data/anhui/v2_test/imagesTr $E10A
pred 3 data/anhui/v2_test/imagesTr $V2A
pred 3 data/full/outside_A/imagesTr $V2O
cd model
EV="../.venv/bin/python -u evaluate.py --cutoff 0.3 --piece confident"
A="--data ../data/anhui/nnunet --splits ../data/anhui/splits_v2.json --key test"
echo "=== Anhui locked test: ResEnc L on v1 data";  $EV $A --nnunet-prob ../$V1  --out ../results/v2test_resencL_v1data.csv
echo "=== Anhui locked test: ResEnc L on E10 data"; $EV $A --nnunet-prob ../$E10A --out ../results/v2test_resencL_e10data.csv
echo "=== Anhui locked test: ResEnc L on v2 data";  $EV $A --nnunet-prob ../$V2A --out ../results/v2test_resencL_v2data.csv
echo "=== Anhui locked test: full v1 recipe"
$EV $A --ours b3_long_fold0 b5_long_fold1 b5_long_fold2 b5_long_fold3 b5_long_fold4 --gauss --weight 0.25 \
    --nnunet-prob ../$V1 ../data/full/prob_nnunet_1000ep/anhui_asls --out ../results/v2test_v1recipe.csv
echo "=== outside A: v2"
$EV --data ../data/full/outside_A --splits ../data/full/splits_multi.json --key outside_test --nnunet-prob ../$V2O \
    --out ../results/outside_A_v2.csv
