"""Integration gateway to the CT Scan system. Same MPI-lookup + normalize shape as
backend/lab_gateway.py and backend/mri_gateway.py."""
import asyncio
from data import ct_system


def _normalize(row: dict, patient_id: str) -> dict:
    return {
        "patient_id": patient_id,
        "name": row["name"],
        "test_name": row["test_name"],
        "test_date": row["test_date"],
        "result": row["result"],
        "doctor": row["doctor"],
        "report_image": row["report_image"],
    }


async def get_records_for_patient(db, patient_id: str) -> list[dict]:
    mpi_row = await db.mpi.find_one({"patient_id": patient_id}, {"_id": 0})
    if not mpi_row:
        return []
    rows = await asyncio.to_thread(ct_system.query_by_local_id, mpi_row["ct_local_id"])
    return [_normalize(r, patient_id) for r in rows]


async def get_all_records(db) -> list[dict]:
    mpi_rows = await db.mpi.find({}, {"_id": 0}).to_list(None)
    local_to_canonical = {m["ct_local_id"]: m["patient_id"] for m in mpi_rows}
    rows = await asyncio.to_thread(ct_system.query_all)
    records = []
    for r in rows:
        patient_id = local_to_canonical.get(r["_local_id"])
        if not patient_id:
            continue
        records.append(_normalize(r, patient_id))
    return records
