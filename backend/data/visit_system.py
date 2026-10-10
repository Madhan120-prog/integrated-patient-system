"""
Simulated front-desk and nursing visit log. A seventh separate system: one JSON
file keyed by this system's own local id, holding what happened on each visit
day in order (check-in, vitals, blood draw, consultation, infusion, check-out).

It records the ORDER of events on a day, not clock times. Like the other
systems it knows only its own local id, never the canonical patient_id.
"""
import json
import os
from pathlib import Path

DB_PATH = Path(os.environ.get("DATA_DIR") or Path(__file__).parent) / "visit_log_store.json"


def reset_and_seed(records_by_local_id: dict) -> int:
    # Only this system's own fields are stored; the canonical patient_id stays in the MPI.
    stored = {local_id: [{"visit_date": r["visit_date"], "steps": r["steps"]} for r in recs]
              for local_id, recs in records_by_local_id.items()}
    with open(DB_PATH, "w") as f:
        json.dump(stored, f)
    return sum(len(recs) for recs in stored.values())


def clear():
    if DB_PATH.exists():
        DB_PATH.unlink()


def query_by_local_id(local_id: str) -> list[dict]:
    if not DB_PATH.exists():
        return []
    with open(DB_PATH) as f:
        return json.load(f).get(local_id, [])
