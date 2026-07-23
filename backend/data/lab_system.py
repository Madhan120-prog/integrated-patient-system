"""
Simulated third-party lab vendor ("Sunquest") — its own SQLite database, not a Mongo
collection. Real lab vendors (Sunquest, PathNet) are relational systems, not document
stores, so this is a genuinely different storage paradigm from the hospital's main
Mongo database — not just a second collection pretending to be a different vendor.

This module only knows about vendor-local IDs (sunquest_id) and never sees the
hospital's canonical patient_id. That translation happens one layer up, in
backend/lab_gateway.py, via the Master Patient Index (MPI).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "sunquest.db"

SCHEMA = """
CREATE TABLE lab_results (
    sunquest_id TEXT NOT NULL,
    patient_name TEXT NOT NULL,
    test_name TEXT NOT NULL,
    test_date TEXT NOT NULL,
    result TEXT NOT NULL,
    doctor TEXT NOT NULL,
    report_image TEXT
)
"""


def reset_and_seed(records_by_local_id: dict) -> int:
    """records_by_local_id: {sunquest_id: [record dict, ...]}. Wipes and reseeds
    the whole table. Returns the number of rows inserted."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS lab_results")
    conn.execute(SCHEMA)
    rows = [
        (local_id, r["name"], r["test_name"], r["test_date"], r["result"], r["doctor"], r.get("report_image"))
        for local_id, records in records_by_local_id.items()
        for r in records
    ]
    conn.executemany(
        "INSERT INTO lab_results (sunquest_id, patient_name, test_name, test_date, result, doctor, report_image) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    conn.close()
    return len(rows)


def clear():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS lab_results")
    conn.commit()
    conn.close()


def query_by_local_id(local_id: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM lab_results WHERE sunquest_id = ?", (local_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_all() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM lab_results").fetchall()
    conn.close()
    return [dict(r) for r in rows]
