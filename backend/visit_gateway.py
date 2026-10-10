"""Integration gateway to the visit log (front desk and nursing). Same MPI lookup
as the six clinical gateways; returns one entry per visit day with its ordered steps."""
import asyncio
from data import visit_system


async def get_records_for_patient(db, patient_id: str) -> list[dict]:
    mpi_row = await db.mpi.find_one({"patient_id": patient_id}, {"_id": 0})
    if not mpi_row or not mpi_row.get("visit_local_id"):   # MPI rows seeded before this system existed
        return []
    rows = await asyncio.to_thread(visit_system.query_by_local_id, mpi_row["visit_local_id"])
    return [{"patient_id": patient_id, "visit_date": r["visit_date"], "steps": r["steps"]} for r in rows]
