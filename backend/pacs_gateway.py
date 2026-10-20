"""Integration gateway to the picture archive (PACS). Same MPI lookup as the
other gateways; returns the DICOM series held for the patient."""
import asyncio
from data import pacs_system


async def get_series(db, patient_id: str) -> list[dict]:
    mpi_row = await db.mpi.find_one({"patient_id": patient_id}, {"_id": 0})
    if not mpi_row or not mpi_row.get("pacs_local_id"):   # MPI rows seeded before this system existed
        return []
    return await asyncio.to_thread(pacs_system.list_series, mpi_row["pacs_local_id"])
