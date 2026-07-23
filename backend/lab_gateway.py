"""
Integration gateway to the lab vendor system ("Sunquest").

Real hospital departments don't query each other's databases directly. A request
has to go through: look up the patient's ID *in that vendor's own system* via the
Master Patient Index (MPI), query the vendor with that local ID, then normalize the
response back into the hospital's shared record shape. This module is that
translation layer for labs — everything else in the app keeps treating blood
profile records exactly like MRI/X-Ray/etc, unaware they're coming from a
completely different database underneath.
"""
import asyncio
from data import lab_system


def _normalize(row: dict, patient_id: str) -> dict:
    return {
        "patient_id": patient_id,
        "name": row["patient_name"],
        "test_name": row["test_name"],
        "test_date": row["test_date"],
        "result": row["result"],
        "doctor": row["doctor"],
        "report_image": row["report_image"],
    }


async def get_records_for_patient(db, patient_id: str) -> list[dict]:
    """MPI lookup -> query the separate lab system -> normalize."""
    mpi_row = await db.mpi.find_one({"patient_id": patient_id}, {"_id": 0})
    if not mpi_row:
        return []
    rows = await asyncio.to_thread(lab_system.query_by_local_id, mpi_row["sunquest_lab_id"])
    return [_normalize(r, patient_id) for r in rows]


async def get_all_records(db) -> list[dict]:
    """Used by the department-wide 'All Patient Records' view — pulls every lab
    result across every patient and translates each vendor-local ID back to our
    canonical patient_id via the MPI."""
    mpi_rows = await db.mpi.find({}, {"_id": 0}).to_list(None)
    local_to_canonical = {m["sunquest_lab_id"]: m["patient_id"] for m in mpi_rows}
    rows = await asyncio.to_thread(lab_system.query_all)
    records = []
    for r in rows:
        patient_id = local_to_canonical.get(r["sunquest_id"])
        if not patient_id:
            continue
        records.append(_normalize(r, patient_id))
    return records
