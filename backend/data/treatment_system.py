"""
Simulated third-party Treatment/EMR module. A single JSON file holding one
serialized blob — different again from the other four vendors (relational,
per-patient JSON files, key-value dbm, flat CSV). Mimics a legacy system that only
exposes a periodic data dump rather than a live query interface.

Only knows about treatment_local_id, never the hospital's canonical patient_id.

V3 note: was pickle in V2. Switched to JSON — same file-based pattern,
no deserialization code-execution risk.
"""
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "treatment_store.json"


def reset_and_seed(records_by_local_id: dict) -> int:
    with open(DB_PATH, "w") as f:
        json.dump(records_by_local_id, f)
    return sum(len(recs) for recs in records_by_local_id.values())


def clear():
    if DB_PATH.exists():
        DB_PATH.unlink()


def _load() -> dict:
    if not DB_PATH.exists():
        return {}
    with open(DB_PATH) as f:
        return json.load(f)


def query_by_local_id(local_id: str) -> list[dict]:
    return _load().get(local_id, [])


def query_all() -> list[dict]:
    records = []
    for local_id, recs in _load().items():
        for r in recs:
            records.append({**r, "_local_id": local_id})
    return records
