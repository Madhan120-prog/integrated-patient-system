# Small-scale plan: first results on university HPC

> Last updated: 2026-10-27
> Goal: prove the whole loop works on **50 patients** before spending days of GPU time on all 422.
> The learning guide and experiment table are in `README.md`; this file is the order of work.

## Experiment tracker
Live page: https://claude.ai/artifact/3SiwC4T6AfLfb8jw2VV39y (private until shared). Its data files are kept in `results/experiments.json` and `results/training_curves.json`; update both after each run.

## How to work on HPC: which tool for what

| Tool | What it is | Use it for | Don't use it for |
|---|---|---|---|
| **Open OnDemand** (web page, if your HPC offers it; most do) | HPC in the browser: file browser, Jupyter, VS Code in the browser, job list | **Recommended start.** Interactive GPU sessions for short tests, looking at QC pictures, editing files | Runs longer than the session time limit |
| **VS Code Remote-SSH** (from your Mac) | Your normal VS Code, but the files live on HPC | Comfortable editing and submitting jobs | Training: it connects to the *login node*, which is shared; heavy work there is usually banned |
| **SSH + `sbatch`** (terminal) | Send a job to the queue; it runs on a GPU node while you're away | **All long training runs** (hours to days) | Quick trial and error |

**Suggested setup:** learn and test in **OnDemand** (Jupyter or VS Code app on a GPU node), then send real
training as **`sbatch` jobs**. If you prefer your own VS Code, use Remote-SSH for editing and `sbatch` for running.

## Our HPC: BigBlue (University of Memphis)
- OnDemand: https://bigblueweb.memphis.edu (Files, Jobs, Clusters → shell, Interactive Apps: VSCode, Jupyter)
- GPUs: 12 × V100 (Intel nodes), 8 × A100 (AMD nodes); scheduler SLURM
- Confirmed 2026-10-28 with `sinfo`: `agpuq` = 4 nodes × 2 GPUs (A100), max 17 days; `igpuq` = 6 nodes × 2 GPUs (V100). Request with `--gres=gpu:1`
- Python: `module load python/3.12.9/gcc.8.5.0` (load it before every use of `.venv`)
- Quotas: home 50 GB, project 1 TB, scratch 10 TB. Scratch: `/scratch/$USER` (not backed up). Internet works from the login node
- Help: hpcadmins@memphis.edu

## Check these on your HPC first (one-time, ~30 min, from its user docs or help desk)
- [ ] Is there **Open OnDemand**? What's its web address?
- [ ] Name of the **GPU partition** and the GPU type (A100, V100, ...), and the **max job time**
- [ ] **Storage:** home quota, and the **scratch** path (big, fast, but often auto-deleted after N days)
- [ ] Do **compute nodes have internet**? Often they don't, so downloads run on the login node or a "data transfer node"
- [ ] How to load Python / CUDA (`module avail python`, `module avail cuda`)

## Phase A: done on your Mac ✅
- [x] Pipeline written: download, data check, conversion + QC pictures, patient split
- [x] Own 3D U-Net and training script
- [x] Tested on 6 local patients; QC pictures confirmed masks sit on the tumours
- [x] Download tested with 1 patient from TCIA

## Phase B: set up on HPC (day 1)
- [x] Copy the code (not data) to HPC (done 2026-10-28 by uploading `tumor-ai-code.zip` in OnDemand Files), or from the project root on your Mac:
  `rsync -av --exclude data --exclude runs --exclude .venv research/tumor-ai/ <you>@<hpc-address>:~/tumor-ai/`
- [x] On HPC: `cd ~/tumor-ai && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- [x] Point `data/` at scratch so big files don't fill your home quota:
  `mkdir -p <scratch>/tumor-ai-data && ln -s <scratch>/tumor-ai-data data`
- [x] Self-check on a GPU node (A100 80 GB, `GPU ready: True`): `.venv/bin/python model/unet3d.py` → prints `ok`

## Phase C: 50 patients of data (day 1-2)
- [x] Download (login / transfer node): `.venv/bin/python prep/00_download.py data/raw --patients 50` → 100 series, 0 failed, 5.7 GB on disk, 5,664 files (API size 3.0 GB understates it)
- [x] Data check: `.venv/bin/python prep/01_inventory.py data/raw data/inventory.csv`
- [x] Convert (48 converted; skipped LUNG1-014 and LUNG1-021, 021 = uneven slice spacing 3-6 mm): `.venv/bin/python prep/02_convert.py data/inventory.csv data`
- [x] **Open every picture in `data/qc/`** (OnDemand file browser). All 48 sit on a lesion. Very small: LUNG1-027 (1.0 cc), 049 (3.0 cc), 050 (6.5 cc)
- [x] Split: `.venv/bin/python prep/03_split.py data/cases.csv data/splits.json` → 7 test, 41 in 5 folds

## Phase D: E0, "can it learn one patient?" (day 2, ~30 min, interactive) ✅
Done 2026-10-28 on A100: Dice 0.16 (step 250) → 0.90 (step 2,000). Pipeline and GPU proven.
Train and validate on the same single patient. Dice should climb towards 1.0. If it doesn't, there is a bug.
```bash
python -c "import json; json.dump({'test': [], 'folds': [{'train': ['LUNG1-001'], 'val': ['LUNG1-001']}]}, open('data/splits_e0.json', 'w'))"
cd model && ../.venv/bin/python train.py --data ../data/nnunet/Dataset001_LungGTV --splits ../data/splits_e0.json --steps 2000 --val-every 250 --name e0_overfit
```

## Phase E: first two real runs, fold 0 only (day 2-4, batch jobs)
| Run | Command (inside an `sbatch` job, see README section 3) | Rough time on one modern GPU |
|---|---|---|
| **E3-small**: our U-Net (`jobs/e3_small_fold0.sbatch`) | `train.py ... --fold 0 --base 32 --patch 48 160 160 --steps 20000 --name e3_small_fold0` | a few hours |
| **E1-small**: nnU-Net, shortened (`jobs/e1_small_fold0.sbatch`) | `nnUNetv2_plan_and_preprocess -d 1` then `nnUNetv2_train 1 3d_fullres 0 -tr nnUNetTrainer_100epochs` | a few hours |

(Times are estimates; the first run tells us the real speed. Use the same `splits.json` for both, see README section 3.)

- Submitted 2026-10-28: E3-small = job 3516111 (ag01), E1-small = job 3516113 (ag02, nnunetv2 2.8.1); both started. E1 crashed at training start (torch.compile error: "Attempting to use a closed pool"); preprocessing finished; rerun with `nnUNet_compile=f`. E3 step 1,000: val Dice 0.10 (normal this early)
- [ ] Record both in `results.csv` (columns in README section 4)
- [ ] Look at 3-4 predicted outlines next to the doctor's, especially one small tumour

## Phase F: review, then scale (end of week 1)
- [ ] Show Dr. Dasgupta: QC pictures, E0 curve, E1 vs E3 on 50 patients
- [ ] Decide: fix anything found, then download all 422 (27.5 GB) and run all 5 folds of E1 and E3
- [ ] Then continue with the experiment table (E2, E4 ...)

- [x] Full runs done 2026-10-30: E1 and E3 on 415 patients, 5 folds each, plus the final test (results in EXPERIMENTS.md)

## Later: report learning and pelvis (added 2026-10-30, details in README section 6)
- [ ] Apply for Stanford AIMI data use agreement for Merlin Plus (pelvis/abdomen CT + reports)
- [ ] E14: report supervision (R-Super idea) on lung, using ReXGroundingCT / CT-RATE reports
- [ ] E15: pelvis model on Merlin Plus, Merlin-Cancer-Super as baseline

## Rules
- Only public data on HPC. Clinic data stays off it until the hospital and university both approve.
- Never run training on the login node.
- Every run uses `data/splits.json` and records its seed; the test patients are used once, at the very end.
