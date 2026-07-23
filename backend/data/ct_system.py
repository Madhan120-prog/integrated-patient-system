"""
Simulated third-party CT Scan system. Uses `shelve` — a persisted-object store,
different again from labs (relational), MRI (JSON files), and X-Ray (key-value
dbm). Values are native Python objects, not manually serialized JSON/text.

Only knows about ct_local_id, never the hospital's canonical patient_id.
"""
import glob
import shelve
from pathlib import Path

DB_PATH = Path(__file__).parent / "ct_store"


def reset_and_seed(records_by_local_id: dict) -> int:
    clear()
    count = 0
    with shelve.open(str(DB_PATH)) as db:
        for local_id, records in records_by_local_id.items():
            db[local_id] = records
            count += len(records)
    return count


def clear():
    # shelve's underlying dbm backend varies by platform (some write "ct_store",
    # others "ct_store.db"/".dir"/".dat") — glob instead of guessing the suffix.
    for f in glob.glob(str(DB_PATH) + "*"):
        Path(f).unlink()


def _exists() -> bool:
    return len(glob.glob(str(DB_PATH) + "*")) > 0


def query_by_local_id(local_id: str) -> list[dict]:
    if not _exists():
        return []
    with shelve.open(str(DB_PATH), flag='r') as db:
        return db.get(local_id, [])


def query_all() -> list[dict]:
    if not _exists():
        return []
    records = []
    with shelve.open(str(DB_PATH), flag='r') as db:
        for local_id, recs in db.items():
            for r in recs:
                records.append({**r, "_local_id": local_id})
    return records
