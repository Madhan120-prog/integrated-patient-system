"""
Simulated third-party X-Ray system. A key-value store (dbm) — a different
persistence paradigm again from labs (relational) and MRI (per-patient JSON
files), since real hospital vendors don't all pick the same kind of database.

Only knows about xray_local_id, never the hospital's canonical patient_id.
"""
import dbm.dumb as dbmmod
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "xray_store"


def reset_and_seed(records_by_local_id: dict) -> int:
    clear()
    db = dbmmod.open(str(DB_PATH), 'c')
    count = 0
    for local_id, records in records_by_local_id.items():
        db[local_id] = json.dumps(records)
        count += len(records)
    db.close()
    return count


def clear():
    for ext in ('.dir', '.dat', '.bak'):
        p = Path(str(DB_PATH) + ext)
        if p.exists():
            p.unlink()


def query_by_local_id(local_id: str) -> list[dict]:
    if not Path(str(DB_PATH) + '.dir').exists():
        return []
    db = dbmmod.open(str(DB_PATH), 'r')
    raw = db.get(local_id)
    db.close()
    return json.loads(raw) if raw else []


def query_all() -> list[dict]:
    if not Path(str(DB_PATH) + '.dir').exists():
        return []
    db = dbmmod.open(str(DB_PATH), 'r')
    records = []
    for key in db.keys():
        local_id = key.decode('utf-8') if isinstance(key, bytes) else key
        for r in json.loads(db[key]):
            records.append({**r, "_local_id": local_id})
    db.close()
    return records
