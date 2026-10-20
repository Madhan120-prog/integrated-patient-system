"""
Simulated radiation oncology system, the role an oncology information system
and a planning system play together (for example MOSAIQ and a treatment
planning system). A ninth separate system: the approved plan as standard DICOM
RT files (plan, structure set, dose) per patient, plus a delivery log of
treatment fractions as JSON lines. Knows only its own local id.
"""
import json
import os
import shutil
from pathlib import Path

DB_PATH = Path(os.environ.get("DATA_DIR") or Path(__file__).parent) / "radiation_store"
LOG = "delivery_log.jsonl"


def store_course(local_id: str, struct, plan, dose, fractions: list[dict]) -> int:
    folder = DB_PATH / local_id
    folder.mkdir(parents=True, exist_ok=True)
    for name, ds in (("RTSTRUCT", struct), ("RTPLAN", plan), ("RTDOSE", dose)):
        ds.save_as(folder / f"{name}.dcm", enforce_file_format=True)
    with open(DB_PATH / LOG, "a") as f:
        for row in fractions:
            f.write(json.dumps({"local_id": local_id, **row}) + "\n")
    return len(fractions)


def clear():
    shutil.rmtree(DB_PATH, ignore_errors=True)


def course_files(local_id: str) -> dict | None:
    folder = DB_PATH / local_id
    files = {name: folder / f"{name}.dcm" for name in ("RTSTRUCT", "RTPLAN", "RTDOSE")}
    return {k: str(v) for k, v in files.items()} if all(p.exists() for p in files.values()) else None


def delivery(local_id: str) -> list[dict]:
    if not (DB_PATH / LOG).exists():
        return []
    with open(DB_PATH / LOG) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return [{k: v for k, v in r.items() if k != "local_id"} for r in rows if r["local_id"] == local_id]
