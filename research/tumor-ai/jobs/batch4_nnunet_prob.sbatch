#!/bin/bash
#SBATCH --job-name=b4_nnunet_prob
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --array=0-5
#SBATCH --output=logs/%x_task%a_%A.out
# Batch 4 prep: nnU-Net prediction again (no training), this time saving how sure it is about every voxel
# (--save_probabilities, .npz), so later we can average it with our U-Net.
# Tasks 0-4: fold k model on its OWN validation patients -> data/full/prob_nnunet/val_fold<k>
# Task 5: 5 folds averaged on the 60 locked test patients -> data/full/prob_nnunet/test
# Writes new folders only; refuses to start if the output folder already holds anything.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_compile=f
D=data/full/nnunet/Dataset001_LungGTV
K=$SLURM_ARRAY_TASK_ID
if [ "$K" = 5 ]; then NAME=test; FOLDS="0 1 2 3 4"; else NAME=val_fold$K; FOLDS=$K; fi
OUT=data/full/prob_nnunet/$NAME IN=data/full/prob_nnunet/images_$NAME
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
.venv/bin/nnUNetv2_predict -i $IN -o $OUT -d 1 -c 3d_fullres -tr nnUNetTrainer_250epochs -f $FOLDS --save_probabilities
