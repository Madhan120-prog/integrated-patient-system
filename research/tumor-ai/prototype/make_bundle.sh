#!/bin/bash
# Run on BigBlue: packs what the review desk needs into ONE file in scratch (not home, so no quota is used):
#   models: nnU-Net ResEnc L 1000 ep fold 0, our U-Net (b5_huge_long_fold0), splits.json
#   samples: 2 fold-0 VALIDATION patients (CT + doctor's RTSTRUCT), never seen by these fold-0 models
#     bash ~/ips/research/tumor-ai/prototype/make_bundle.sh
# Then download /scratch/$USER/demo_bundle.tgz (OnDemand -> Files) and unpack it in prototype/ on the Mac.
set -euo pipefail
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
B=/scratch/$USER/demo_bundle
rm -rf "$B" && mkdir -p "$B/models/nnunet/fold_0" "$B/samples"
R=runs/nnunet_full/Dataset001_LungGTV/nnUNetTrainer__nnUNetResEncUNetLPlans__3d_fullres
cp $R/plans.json $R/dataset.json "$B/models/nnunet/"
cp $R/fold_0/checkpoint_final.pth "$B/models/nnunet/fold_0/"
cp model/runs/b5_huge_long_fold0/best.pt "$B/models/unet.pt"
cp data/full/splits.json "$B/models/splits.json"
.venv/bin/python - "$B/samples" <<'EOF'
import csv, json, sys, zipfile
from pathlib import Path
out = Path(sys.argv[1])
val = json.load(open("data/full/splits.json"))["folds"][0]["val"]
rows = {r["patient"]: r for r in csv.DictReader(open("data/full/inventory.csv"))}
picked = [p for p in val if p in rows and rows[p]["has_primary_gtv"] == "True" and not rows[p]["issues"]][:2]
for p in picked:
    r = rows[p]
    with zipfile.ZipFile(out / f"{p}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(Path(r["ct_dir"]).iterdir()):
            z.write(f, f"ct/{f.name}")
        z.write(r["rtstruct"], "rtstruct.dcm")
    print(p, "->", out / f"{p}.zip")
EOF
cd /scratch/$USER && tar czf demo_bundle.tgz demo_bundle && rm -rf demo_bundle
ls -lh /scratch/$USER/demo_bundle.tgz
