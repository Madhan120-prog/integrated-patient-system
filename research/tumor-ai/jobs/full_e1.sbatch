#!/bin/bash
#SBATCH --job-name=full_e1
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=4-00:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/%x_fold%a_%j.out
# E1: nnU-Net, all patients, one fold per array task (0-4). 250 epochs.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_n_proc_DA=8 nnUNet_compile=f
.venv/bin/nnUNetv2_train 1 3d_fullres $SLURM_ARRAY_TASK_ID -tr nnUNetTrainer_250epochs
