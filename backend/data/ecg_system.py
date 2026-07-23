"""
Simulated third-party ECG system. A single flat CSV file — a tabular,
human-readable export format, different again from the other three vendors.
Mirrors how some legacy hospital systems only expose data via scheduled file
exports rather than a live query API.

Only knows about ecg_local_id, never the hospital's canonical patient_id.
"""
import csv
from pathlib import Path

DB_PATH = Path(__file__).parent / "ecg_store.csv"
FIELDS = ["local_id", "name", "test_name", "test_date", "result", "doctor", "report_image"]


def reset_and_seed(records_by_local_id: dict) -> int:
    count = 0
    with open(DB_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for local_id, records in records_by_local_id.items():
            for r in records:
                writer.writerow({
                    "local_id": local_id,
                    "name": r["name"],
                    "test_name": r["test_name"],
                    "test_date": r["test_date"],
                    "result": r["result"],
                    "doctor": r["doctor"],
                    "report_image": r.get("report_image") or "",
                })
                count += 1
    return count


def clear():
    if DB_PATH.exists():
        DB_PATH.unlink()


def _read_all() -> list[dict]:
    if not DB_PATH.exists():
        return []
    with open(DB_PATH, newline="") as f:
        return list(csv.DictReader(f))


def query_by_local_id(local_id: str) -> list[dict]:
    return [row for row in _read_all() if row["local_id"] == local_id]


def query_all() -> list[dict]:
    records = []
    for row in _read_all():
        records.append({**row, "_local_id": row["local_id"]})
    return records
