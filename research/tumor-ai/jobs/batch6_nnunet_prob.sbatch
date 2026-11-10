#!/bin/bash
#SBATCH --job-name=b6_nnunet_prob
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --array=0-5
#SBATCH --output=logs/%x_task%a_%A.out
# 6.3 prep: one nnU-Net variant's prediction again with probabilities saved (no training), like b4_nnunet_prob.
# Tasks 0-4: fold k on its own validation patients; task 5: 5 folds averaged on the test patients.
# Choose the variant when submitting:
#   sbatch --export=ALL,TAG=resencL,TR=nnUNetTrainer_250epochs,PL=nnUNetResEncUNetLPlans jobs/batch6_nnunet_prob.sbatch
#   sbatch --export=ALL,TAG=1000ep,TR=nnUNetTrainer,PL=nnUNetPlans jobs/batch6_nnunet_prob.sbatch
# Output: data/full/prob_nnunet_<TAG>/{val_fold<k>,test}. Refuses an output folder that already holds anything.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
[ -n "$TAG" ] && [ -n "$TR" ] && [ -n "$PL" ] || { echo "set TAG, TR and PL with --export"; exit 1; }
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_compile=f
D=data/full/nnunet/Dataset001_LungGTV
K=$SLURM_ARRAY_TASK_ID
if [ "$K" = 5 ]; then NAME=test; FOLDS="0 1 2 3 4"; else NAME=val_fold$K; FOLDS=$K; fi
OUT=data/full/prob_nnunet_$TAG/$NAME IN=data/full/prob_nnunet/images_$NAME
[ -n "$(ls -A $OUT 2>/dev/null)" ] && { echo "$OUT already has files, not overwriting"; exit 1; }
mkdir -p $OUT $IN
.venv/bin/python -c "
import json, os
s = json.load(open('data/full/splits.json'))
ids = s['test'] if '$NAME' == 'test' else s['folds'][$K]['val']
for p in ids:
    dst = f'$IN/{p}_0000.nii.gz'
    if not os.path.exists(dst): os.symlink(os.path.abspath(f'$D/imagesTr/{p}_0000.nii.gz'), dst)
print(len(ids), 'patients')
"
.venv/bin/nnUNetv2_predict -i $IN -o $OUT -d 1 -c 3d_fullres -tr $TR -p $PL -f $FOLDS --save_probabilities
