"""
Simulated picture archive (PACS). An eighth separate system: real DICOM files on
disk, one folder per patient under this archive's own local id, one sub-folder
per series. Like the other systems it knows only its own local id, never the
canonical patient_id. The images are synthetic phantoms, not real scans.
"""
import os
import shutil
from pathlib import Path

from functools import lru_cache

import pydicom

DB_PATH = Path(os.environ.get("DATA_DIR") or Path(__file__).parent) / "pacs_store"


def store_series(local_id: str, datasets: list) -> int:
    folder = DB_PATH / local_id / datasets[0].SeriesInstanceUID
    folder.mkdir(parents=True, exist_ok=True)
    for k, ds in enumerate(sorted(datasets, key=lambda d: float(d.ImagePositionPatient[2])), start=1):
        ds.save_as(folder / f"CT_{k:03d}.dcm", enforce_file_format=True)
    return len(datasets)


def clear():
    shutil.rmtree(DB_PATH, ignore_errors=True)


def list_series(local_id: str) -> list[dict]:
    folder = DB_PATH / local_id
    return _list_series(str(folder), folder.stat().st_mtime if folder.exists() else 0)


@lru_cache(maxsize=32)
def _list_series(folder_str: str, mtime: float) -> list[dict]:
    """Series held in this folder, with the files of each in slice order."""
    local_id = Path(folder_str).name
    out = []
    for folder in sorted((DB_PATH / local_id).glob("*")) if (DB_PATH / local_id).exists() else []:
        files = sorted(folder.glob("*.dcm"))
        if not files:
            continue
        head = pydicom.dcmread(files[0], stop_before_pixels=True)
        zs = [float(pydicom.dcmread(f, stop_before_pixels=True).ImagePositionPatient[2]) for f in files]
        out.append({"series_uid": folder.name, "modality": head.Modality, "files": [str(f) for f in files], "zs": zs,
                    "description": str(head.get("SeriesDescription", "")), "study_date": str(head.get("StudyDate", ""))})
    return out
