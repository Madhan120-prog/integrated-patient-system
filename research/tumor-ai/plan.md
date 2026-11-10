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

## After batch 3: more lung data (E11 first, then E10) (planned 2026-11-05)
Why: E9 showed more patients *of the same kind* add little (25% scored like 100%). What can help is *different*
data (other hospitals, scanners, tumour sizes). So first measure how our best model does on another hospital (E11),
then add data where it fails (E10).

| Dataset (public, TCIA) | What it has | Use | Check before use |
|---|---|---|---|
| NSCLC-Radiogenomics (Stanford / Palo Alto VA) | ~211 patients, ~144 with a primary-tumour mask (DICOM SEG, 1 class) | **E11 outside test** first; later half to training (E10) | counts and licence (listed CC BY 3.0) on the TCIA page |
| Medical Segmentation Decathlon, Task06 Lung | ~63 training CTs with tumour masks, already NIfTI | E10: add to training | may share patients with Radiogenomics: match before splitting; CC BY-SA 4.0 |
| NSCLC-Radiomics-Interobserver1 (Maastro) | 22 patients, 21 with GTVs from 5 oncologists each (RTSTRUCT + SEG) | **Evaluation only**: how well doctors agree = realistic ceiling; compare model vs each doctor | same hospital as our data: check those patients are not in our training folds |
| LIDC-IDRI | ~1,000 chest CTs, small nodules outlined by up to 4 radiologists | Optional (E10b): small-tumour practice | label means "nodule", not radiotherapy GTV: train as a separate run, never mixed blindly |

Preparation, so new data lines up with what we have (same steps as `prep/01`-`03`):
1. **Download** with `prep/00_download.py` (TCIA) or the MSD archive; one folder per dataset under `data/<dataset>/`.
2. **Inventory**: slices, spacing, scanner, label names; flag uneven spacing and missing tumour masks (as for Lung1).
3. **Convert** to the same NIfTI layout: CT in HU as `imagesTr/<id>_0000.nii.gz`, label 1 = tumour as `labelsTr/<id>.nii.gz`.
   New readers: DICOM SEG (Radiogenomics, Interobserver) via `highdicom` or `pydicom-seg`; MSD is NIfTI already (check HU and orientation).
4. **Same meaning of "tumour"**: primary tumour only (like GTV-1); drop node labels; note where the source drew differently.
5. **Remove duplicates** across datasets (same patient in two sets) by matching IDs and scan dates/sizes.
6. **QC picture** for every case, as for Lung1.
7. **Split**: keep our 60 locked Lung1 test patients unchanged; new training data only goes into the training folds;
   an outside-test dataset stays wholly separate and is used once.
8. **Spacing**: keep native spacing like now (our model is built for 3 mm slices); flag scans with thin slices (~1 mm)
   and decide then whether to resample them to 3 mm.

## Next 4 experiments (revised 2026-11-10)
Where we are: nnU-Net ResEnc L leads (0.638 on validation); our U-Net 0.579 at its best setting, 0.594 on fold 0 with
the even bigger block; on test our U-Net already ties the first nnU-Net (0.589 vs 0.591) and is better on small tumours.
- [ ] **1. Strongest nnU-Net**: ResEnc L trained 1000 epochs (its two best gains together), 5 folds
- [ ] **2. Our best U-Net on all folds**: even bigger block + 100,000 steps, folds 1-4, then pick its best prediction setting
- [ ] **3. Team up**: average the best nnU-Net with our U-Net (ours is better on small tumours); mix chosen on validation
- [ ] **4. MedSAM2 (foundation model, box hint)**: (a) box from the doctor's outline = best case; (b) box from our model = real case. Scored apart, as a doctor-guided tool
- [ ] **5. E7, pre-trained vs from scratch** (added, runs alongside): Swin UNETR starting from MONAI's weights
  learned on ~5,000 CTs vs the same Swin from scratch (`b4_swin_big_fold0`, 0.531), fold 0, 2 seeds; STU-Net later
- [ ] **Then one final test** with the winner, on the 60 locked patients
- Later: STU-Net (second E7 model), outside data (E11), look at the 3 large always-missed patients

Run side by side (no step waits for another, except where noted):
- GPU now: 6.1 ResEnc L 1000 epochs, 6.2 our U-Net folds 1-4, E7 Swin pre-trained (one-time weight download first)
- Build now, try on today's models: 6.3 averaging (ResEnc L 250 + nnU-Net 1000 + our U-Net), 6.4 MedSAM2 on validation
  patients (one-time install + weight download)
- Waits: 6.3 is re-run with the 6.1 / 6.2 models when they finish; the final test waits for everything
- One-time setup on BigBlue (public files only): E7 weights `~/tumor-ai/weights/model_swinvit.pt` (MONAI release 0.8.1);
  MedSAM2 in its OWN environment `~/tumor-ai/.venv-medsam2` (torch 2.5.1, code pinned to commit 332f30d, checkpoint
  `MedSAM2_latest.pt`), so the main `.venv` and every other job stay unchanged

## Pick the final model from any network, not only ours (added 2026-11-06)
Goal: the final tool is whichever model scores best on validation (then tested once), nnU-Net included. Our own U-Net
stays as the learning reference. Same patients, folds and locked test for every model; choose on validation only.
- [ ] **nnU-Net, stronger presets**: ResEnc M / L (`nnUNetPlannerResEncM/L`, the nnU-Net team's own 2024 recommendation), 5 folds
- [ ] **nnU-Net, full length**: 1000 epochs (its default; we ran 250)
- [ ] **nnU-Net, best combination**: 2D + 3D ensemble (`nnUNetv2_find_best_configuration`)
- [ ] **Other networks**: MedNeXt, SegResNet (MONAI), STU-Net (pre-trained, nnU-Net based)
- [ ] **Pre-trained on many CTs**: Swin UNETR self-supervised weights (E7), STU-Net, VISTA3D (check it has a lung tumour class)
- [ ] **Doctor-guided (box or click)**: MedSAM / SAM-Med3D / nnInteractive (E8); a separate use (semi-automatic), compare apart
- [ ] **Average the best two or three** (batch 4 starts this with our U-Net + nnU-Net)

## After a winner: upload, review, download (added 2026-11-06)
DICOM in, a doctor reviews the AI outline, a file the planning system opens comes out. Public DICOM only until
hospital and university approve; the model runs locally (never a cloud AI service); every outline is a research draft.
- [ ] **Step 1, `predict_dicom.py`** (command line): DICOM CT folder -> winning model -> `RTSTRUCT.dcm` (via `rt-utils`,
  tied to that CT), plus `mask.nii.gz`, a few overview pictures and a small `summary.json` (tumour size, how sure)
- [ ] **Step 2, small review page** (local, research): upload a zipped DICOM folder; view the CT slice by slice with the
  AI outline on top (NiiVue, reads DICOM in the browser); slider for the cut-off; accept / reject / note;
  download RTSTRUCT, mask and a one-page PDF. FastAPI endpoint + one React page, like the portal
- [ ] **Step 3, inside the portal** (needs approval): "Tumour outline" in the patient chart; pick the CT from PACS
  (`backend/pacs_gateway.py`) instead of uploading; reuse the DocAssist review pattern (AI draft -> doctor reviews ->
  save to chart, AI original kept, audit log); explain at role levels (`/api/explain-levels`); dose effect via
  `backend/radiation.py` (E13). The portal's file-upload analysis sends files to Gemini, so scans must NOT use that route
- Where it runs: our U-Net is small and runs on a normal CPU in about a minute per CT; nnU-Net (5 folds) on CPU is
  slower (minutes to tens of minutes); a GPU box at the hospital if needed

## Later: report learning and pelvis (added 2026-10-30, details in README section 6)
- [ ] Apply for Stanford AIMI data use agreement for Merlin Plus (pelvis/abdomen CT + reports)
- [ ] E14: report supervision (R-Super idea) on lung, using ReXGroundingCT / CT-RATE reports
- [ ] E15: pelvis model on Merlin Plus, Merlin-Cancer-Super as baseline

## Rules
- Only public data on HPC. Clinic data stays off it until the hospital and university both approve.
- Never run training on the login node.
- Every run uses `data/splits.json` and records its seed; the test patients are used once, at the very end.
