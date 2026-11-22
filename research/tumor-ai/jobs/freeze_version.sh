#!/bin/bash
# Freeze a model version: copy exactly the files that make it into ~/tumor-ai/versions/<name>/, write a MANIFEST
# (recipe in words + sha256 of every file) and make it read-only. A frozen version is never changed or overwritten.
#   cd ~/tumor-ai && bash ~/ips/research/tumor-ai/jobs/freeze_version.sh <name> "<recipe>" <paths relative to ~/tumor-ai>...
# v1 (Lung1, the final-test recipe):
#   R=runs/nnunet_full/Dataset001_LungGTV
#   bash ~/ips/research/tumor-ai/jobs/freeze_version.sh v1 "0.25 x our U-Net (b3_long_fold0, b5_long_fold1-4, centre-weighted) + 0.75 x nnU-Net (ResEnc L 250 ep + nnU-Net 1000 ep, 5 folds each), cut-off 0.3, most-confident piece. Final test 0.677 (job 3609438), outside E11 0.670" \
#     $R/nnUNetTrainer_250epochs__nnUNetResEncUNetLPlans__3d_fullres/{plans.json,dataset.json,fold_?/checkpoint_final.pth} \
#     $R/nnUNetTrainer__nnUNetPlans__3d_fullres/{plans.json,dataset.json,fold_?/checkpoint_final.pth} \
#     model/runs/{b3_long_fold0,b5_long_fold1,b5_long_fold2,b5_long_fold3,b5_long_fold4}/{best.pt,settings.json} data/full/splits.json
set -euo pipefail
[ $# -ge 3 ] || { echo "usage: freeze_version.sh <name> \"<recipe>\" <paths...>"; exit 1; }
V=$1; R=$2; shift 2
cd ~/tumor-ai
D=versions/$V
[ -e "$D" ] && { echo "$D already exists: a version is frozen once"; exit 1; }
for p in "$@"; do [ -f "$p" ] || { echo "missing: $p (nothing copied)"; exit 1; }; done
mkdir -p "$D"
cp --parents "$@" "$D/"
{ echo "version: $V"; echo "frozen: $(date '+%Y-%m-%d %H:%M')"; echo "recipe: $R"; echo "files (sha256):"
  (cd "$D" && find . -type f ! -name MANIFEST.txt | sort | xargs sha256sum); } > "$D/MANIFEST.txt"
chmod -R a-w "$D"
echo "$D frozen: $(find "$D" -type f | wc -l) files, $(du -sh "$D" | cut -f1)"
