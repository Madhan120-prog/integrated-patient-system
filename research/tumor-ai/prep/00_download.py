"""Step 0: download NSCLC-Radiomics CT + outline files from TCIA (public, no login).

    python prep/00_download.py data/raw --patients 50     # small start: first 50 patients
    python prep/00_download.py data/raw                   # all 422 (~19 GB)

Already-downloaded series are skipped, so it is safe to re-run after a dropped connection.
Saves the list of what was fetched to data/raw/series.csv (dataset version record).
"""
import argparse
import csv
from pathlib import Path

from tcia_utils import nbia

COLLECTION = "NSCLC-Radiomics"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--patients", type=int, default=0, help="first N patients by ID; 0 = all")
    a = ap.parse_args()

    series = [s for s in nbia.getSeries(collection=COLLECTION) if s["Modality"] in ("CT", "RTSTRUCT")]
    patients = sorted({s["PatientID"] for s in series})
    if a.patients:
        patients = patients[:a.patients]
    chosen = [s for s in series if s["PatientID"] in set(patients)]
    print(f"{len(patients)} patients, {len(chosen)} series, {sum(s['FileSize'] for s in chosen) / 1e9:.1f} GB")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    nbia.downloadSeries([s["SeriesInstanceUID"] for s in chosen], path=str(out), input_type="list")
    keys = ["PatientID", "Modality", "SeriesInstanceUID", "ImageCount", "FileSize", "DateReleased"]
    with open(out / "series.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(chosen)


if __name__ == "__main__":
    main()
