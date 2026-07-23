"""
Simulated third-party imaging system for MRI ("RIS" — Radiology Information
System). Stores exam data as discrete JSON files, one per patient's RIS-local ID,
mirroring how real PACS/RIS systems keep study data as files rather than rows in
a relational table. A different storage paradigm from labs' SQLite on purpose —
real hospital vendors aren't all built the same way.

Only knows about RIS-local IDs, never the hospital's canonical patient_id. That
translation happens in backend/mri_gateway.py via the Master Patient Index (MPI).
"""
import json
from pathlib import Path

STORE_DIR = Path(__file__).parent / "mri_store"


def reset_and_seed(records_by_local_id: dict) -> int:
    """records_by_local_id: {ris_mri_id: [record dict, ...]}. Wipes and reseeds
    the whole directory. Returns the number of records written."""
    clear()
    STORE_DIR.mkdir(exist_ok=True)
    count = 0
    for local_id, records in records_by_local_id.items():
        (STORE_DIR / f"{local_id}.json").write_text(json.dumps(records))
        count += len(records)
    return count


def clear():
    if STORE_DIR.exists():
        for f in STORE_DIR.glob("*.json"):
            f.unlink()


def query_by_local_id(local_id: str) -> list[dict]:
    path = STORE_DIR / f"{local_id}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def query_all() -> list[dict]:
    if not STORE_DIR.exists():
        return []
    records = []
    for f in STORE_DIR.glob("*.json"):
        local_id = f.stem
        for r in json.loads(f.read_text()):
            records.append({**r, "_local_id": local_id})
    return records
