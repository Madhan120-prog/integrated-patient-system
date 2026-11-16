# Review desk (prototype)

Drop a CT scan → the AI outlines the main lung tumour → a doctor reviews it slice by slice, chooses how sure
the AI must be, and signs it off → download an **RTSTRUCT** that a treatment planning system opens.

Research draft only. It runs on this computer (`127.0.0.1`); no scan goes to any online service.
**Public data only** (NSCLC-Radiomics) until the hospital and the university approve.

## What's on the page

- **Film viewer** (centre): the CT with the AI outline (amber), the doctor's outline (blue, dashed) when the upload
  includes it, and thin "height lines" showing where the AI is 10% / 50% / 90% sure. Hover a spot to read its HU
  value and how sure the AI is there. "Where they differ" shades AI-only areas amber and doctor-only areas blue.
- **Slice ribbon** (under the viewer): one column per slice, from feet to head; amber = AI outline area,
  blue line = doctor's. It shows where the tumour is along the body; click or drag to jump.
- **Worksheet** (right): the scan, the sureness slider (10–90%, our tests picked 30%), what the AI found (volume,
  size, slices, overlap with the doctor), a fair-check note (was this patient used to train the model?),
  sign-off (accept / needs changes / reject, name, note) and downloads (RTSTRUCT and mask at the chosen sureness,
  numbers, printable worksheet).
- Keys: `↑` `↓` slices, `[` `]` sureness, `Z` zoom to tumour, `D` doctor, `R` rings, `F` differences, `W` window.

## Set up (once, on the Mac)

```bash
cd ~/Desktop/Projects/integrated-patient-system/research/tumor-ai
.venv/bin/python -m pip install -r prototype/requirements.txt
```

### Models: copy them from BigBlue into `prototype/models/` (git-ignored)

Easiest: one bundle with the models and 2 fair demo patients. On BigBlue run
`bash ~/ips/research/tumor-ai/prototype/make_bundle.sh`, download `/scratch/<user>/demo_bundle.tgz`
(OnDemand → Files), then on the Mac: `cd research/tumor-ai/prototype && tar xzf ~/Downloads/demo_bundle.tgz --strip-components=1`
(gives `models/` and `samples/<patient>.zip`). Or copy the files one by one:

Run on the **Mac** (it pulls from BigBlue; public-data weights only). Put your BigBlue user name and login address
in `B`. No ssh from the Mac? Download the same five files in OnDemand → Files instead and place them as below.

```bash
cd ~/Desktop/Projects/integrated-patient-system/research/tumor-ai/prototype && mkdir -p models/nnunet/fold_0
B=<user>@<bigblue-login-address>:tumor-ai
scp $B/runs/nnunet_full/Dataset001_LungGTV/nnUNetTrainer__nnUNetResEncUNetLPlans__3d_fullres/{plans.json,dataset.json} models/nnunet/
scp $B/runs/nnunet_full/Dataset001_LungGTV/nnUNetTrainer__nnUNetResEncUNetLPlans__3d_fullres/fold_0/checkpoint_final.pth models/nnunet/fold_0/
scp $B/model/runs/b5_huge_long_fold0/best.pt models/unet.pt
scp $B/data/full/splits.json models/splits.json
```

- `nnunet/` = ResEnc L, 1000 epochs (6.1). With both models the outline is 25% ours + 75% nnU-Net, the batch 6
  winner. Only **fold 0** is copied: a fold-0 model has never seen fold 0's validation patients, so those patients
  give a fair demo. (All 5 folds would be stronger, but then every patient except the locked test ones was seen
  in training by some fold.)
- `splits.json` lets the page say whether a patient was used in training. Do **not** demo on the locked test
  patients: that spends the one-time test.
- No models yet? `cp ../model/runs/local_demo/best.pt models/unet.pt` runs the tiny laptop U-Net (weak, but shows
  the whole flow).

### A scan to try

Copy one fold-0 validation patient's raw DICOM (CT + its RTSTRUCT) from BigBlue and zip it, or make a sample from a
local NIfTI case:

```bash
../.venv/bin/python make_sample.py ../data/nnunet/Dataset001_LungGTV LUNG1-006 samples
```

## Run

```bash
cd ~/Desktop/Projects/integrated-patient-system/research/tumor-ai && .venv/bin/python prototype/server.py
```

Open http://127.0.0.1:8765 and drop the zip on "New scan". On a Mac, our U-Net takes about a minute; nnU-Net fold 0
a few minutes (test-time mirroring is off for speed; the validation scores used it).

Command line only, no page (Step 1 in `plan.md`):

```bash
.venv/bin/python prototype/engine.py prototype/samples/LUNG1-006_sample.zip --out prototype/cases/try1
```

Writes `out/AI_outline_<patient>_cut30.dcm` (RTSTRUCT, ROI `GTV_AI_DRAFT`), `out/AI_mask_...nii.gz`,
`overview.png` and `summary.json`.

## Files

| File | What it does |
|---|---|
| `engine.py` | DICOM in → models → outlines at every sureness level → numbers → RTSTRUCT / mask |
| `server.py` | local web server: upload, one scan at a time in the background, review, downloads |
| `static/index.html` | the page (one file, no internet needed) |
| `make_sample.py` | turns a NIfTI case back into a DICOM CT + doctor's RTSTRUCT, for trying it out |
| `cases/`, `inbox/`, `models/`, `samples/` | scans, models and results: git-ignored, never committed |
