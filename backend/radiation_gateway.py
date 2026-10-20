"""Integration gateway to the radiation oncology system. Same MPI lookup as the
other gateways; returns the plan's DICOM RT files and the delivery log."""
import asyncio
from data import radiation_system


async def get_course(db, patient_id: str) -> dict | None:
    mpi_row = await db.mpi.find_one({"patient_id": patient_id}, {"_id": 0})
    if not mpi_row or not mpi_row.get("ro_local_id"):
        return None
    local_id = mpi_row["ro_local_id"]
    files = await asyncio.to_thread(radiation_system.course_files, local_id)
    if not files:
        return None
    return {"local_id": local_id, "files": files, "delivery": await asyncio.to_thread(radiation_system.delivery, local_id)}


async def get_all_courses(db) -> list[dict]:
    """One row per patient with a course, for the department list."""
    rows = []
    async for m in db.mpi.find({"ro_local_id": {"$exists": True}}, {"_id": 0, "patient_id": 1, "ro_local_id": 1, "pacs_local_id": 1}):
        files = await asyncio.to_thread(radiation_system.course_files, m["ro_local_id"])
        if files:
            rows.append({"patient_id": m["patient_id"], "local_id": m["ro_local_id"], "files": files,
                         "delivery": await asyncio.to_thread(radiation_system.delivery, m["ro_local_id"])})
    return rows
