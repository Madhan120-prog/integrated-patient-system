from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, Query, HTTPException
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from faker import Faker
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB connection
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize Faker
fake = Faker()

# Sample medical report image URLs
MEDICAL_IMAGES = {
    "xray": [
        "https://images.unsplash.com/photo-1564725075388-cc8338732289",
        "https://images.unsplash.com/photo-1648025487795-2f7bd6d620bf",
    ],
    "ecg": [
        "https://images.unsplash.com/photo-1682706841281-f723c5bfcd83",
        "https://images.unsplash.com/photo-1682706841289-9d7ddf5eb999",
    ],
    "mri": [
        "https://images.pexels.com/photos/7089020/pexels-photo-7089020.jpeg",
    ],
    "ct": [
        "https://images.unsplash.com/photo-1631563019676-dade0dbdb8fc",
    ],
    "blood": [
        "https://images.unsplash.com/photo-1639772823849-6efbd173043c",
        "https://images.unsplash.com/photo-1606206591513-adbfbdd7a177",
    ],
}

# Medicine lists
MEDICINES = [
    "Amoxicillin 500mg",
    "Ibuprofen 400mg",
    "Metformin 850mg",
    "Lisinopril 10mg",
    "Atorvastatin 20mg",
    "Omeprazole 20mg",
    "Aspirin 75mg",
    "Paracetamol 500mg",
    "Ciprofloxacin 500mg",
    "Levothyroxine 50mcg",
]

# =========================
# Models
# =========================
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None


class Profile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    age: int
    gender: str
    blood_group: str
    address: str
    phone: str
    registration_date: str


class MRIRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    test_name: str
    test_date: str
    result: str
    doctor: str
    report_image: str


class XRayRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    test_name: str
    test_date: str
    result: str
    doctor: str
    report_image: str


class ECGRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    test_name: str
    test_date: str
    result: str
    doctor: str
    report_image: str


class TreatmentRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    treatment_name: str
    treatment_date: str
    result: str
    doctor: str
    medicines: str


class BloodProfileRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    test_name: str
    test_date: str
    result: str
    doctor: str
    report_image: str


class CTScanRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    test_name: str
    test_date: str
    result: str
    doctor: str
    report_image: str


class SearchResponse(BaseModel):
    profile: Optional[Profile] = None
    mri_records: List[MRIRecord] = []
    xray_records: List[XRayRecord] = []
    ecg_records: List[ECGRecord] = []
    treatment_records: List[TreatmentRecord] = []
    blood_profile_records: List[BloodProfileRecord] = []
    ct_scan_records: List[CTScanRecord] = []


class PatientAnalytics(BaseModel):
    total_visits: int
    total_tests: int
    departments_visited: dict
    visit_timeline: List[dict]
    treatment_summary: dict
    health_trend: str
    recent_results: List[dict]


# =========================
# Deep Query Models (B1)
# =========================
class DeepQueryRequest(BaseModel):
    patient_id: str
    question: str


class EvidenceItem(BaseModel):
    department: str
    date: str
    title: str
    result: str
    doctor: Optional[str] = None
    extra: Optional[dict] = None


class DeepQueryResponse(BaseModel):
    patient_id: str
    question: str
    detected_departments: List[str] = []
    answer: str
    evidence: List[EvidenceItem] = []
    matched_count: int = 0


# =========================
# Deep Query Helpers (B1)
# =========================
def _normalize_text(s: str) -> str:
    return (s or "").strip().lower()


def _detect_departments(question: str) -> List[str]:
    q = _normalize_text(question)

    rules = {
        "mri": ["mri", "brain", "spine", "knee", "shoulder", "abdomen"],
        "xray": ["xray", "x-ray", "fracture", "chest", "pelvis", "dental"],
        "ecg": ["ecg", "ekg", "arrhythmia", "tachycardia", "holter", "sinus"],
        "blood": ["blood", "cbc", "lipid", "thyroid", "liver", "kidney", "hemoglobin", "wbc", "platelet"],
        "ct": ["ct", "ct scan", "head", "chest", "abdomen", "pelvic", "spine"],
        "treatment": ["treatment", "medicine", "medicines", "medication", "prescription", "therapy", "surgery", "vaccination", "dialysis"],
    }

    detected = []
    for dept, keywords in rules.items():
        if any(k in q for k in keywords):
            detected.append(dept)

    return detected  # can be [] meaning "search all"


async def _fetch_patient_profile(patient_id: str):
    return await db.profiles.find_one({"patient_id": patient_id}, {"_id": 0})


async def _fetch_patient_records(patient_id: str):
    q = {"patient_id": patient_id}

    mri = await db.mri_records.find(q, {"_id": 0}).to_list(1000)
    xray = await db.xray_records.find(q, {"_id": 0}).to_list(1000)
    ecg = await db.ecg_records.find(q, {"_id": 0}).to_list(1000)
    blood = await db.blood_profile_records.find(q, {"_id": 0}).to_list(1000)
    ct = await db.ct_scan_records.find(q, {"_id": 0}).to_list(1000)
    treatment = await db.treatment_records.find(q, {"_id": 0}).to_list(1000)

    mri = sorted(mri, key=lambda r: r.get("test_date", ""))
    xray = sorted(xray, key=lambda r: r.get("test_date", ""))
    ecg = sorted(ecg, key=lambda r: r.get("test_date", ""))
    blood = sorted(blood, key=lambda r: r.get("test_date", ""))
    ct = sorted(ct, key=lambda r: r.get("test_date", ""))
    treatment = sorted(treatment, key=lambda r: r.get("treatment_date", ""))

    return {"mri": mri, "xray": xray, "ecg": ecg, "blood": blood, "ct": ct, "treatment": treatment}


def _record_to_evidence(dept: str, r: dict) -> EvidenceItem:
    if dept == "treatment":
        return EvidenceItem(
            department="Treatment",
            date=r.get("treatment_date", ""),
            title=r.get("treatment_name", "Treatment"),
            result=r.get("result", ""),
            doctor=r.get("doctor"),
            extra={"medicines": r.get("medicines")},
        )

    label = dept.upper() if dept != "xray" else "X-RAY"
    return EvidenceItem(
        department=label,
        date=r.get("test_date", ""),
        title=r.get("test_name", "Test"),
        result=r.get("result", ""),
        doctor=r.get("doctor"),
        extra={"report_image": r.get("report_image")},
    )


def _score_record(question: str, r: dict) -> int:
    q = _normalize_text(question)

    hay = " ".join(
        [
            _normalize_text(r.get("test_name", "")),
            _normalize_text(r.get("treatment_name", "")),
            _normalize_text(r.get("result", "")),
            _normalize_text(r.get("doctor", "")),
            _normalize_text(r.get("medicines", "")),
        ]
    )

    score = 0
    for token in [t for t in q.split() if len(t) >= 3]:
        if token in hay:
            score += 2

    return score


# =========================
# Helper: sample data
# =========================
async def populate_sample_data():
    """Populate all department collections with sample patient data using Faker"""

    existing_count = await db.profiles.count_documents({})
    if existing_count > 0:
        return {"message": "Data already exists", "patients_created": existing_count}

    await db.profiles.delete_many({})
    await db.mri_records.delete_many({})
    await db.xray_records.delete_many({})
    await db.ecg_records.delete_many({})
    await db.treatment_records.delete_many({})
    await db.blood_profile_records.delete_many({})
    await db.ct_scan_records.delete_many({})

    patients = []
    for i in range(1, 16):
        patient_id = f"P{1000 + i}"
        name = fake.name()
        patients.append(
            {
                "patient_id": patient_id,
                "name": name,
                "age": random.randint(18, 85),
                "gender": random.choice(["Male", "Female"]),
                "blood_group": random.choice(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]),
                "address": fake.address().replace("\n", ", "),
                "phone": fake.phone_number(),
                "registration_date": fake.date_between(start_date="-2y", end_date="today").isoformat(),
            }
        )

    await db.profiles.insert_many(patients)

    mri_tests = ["Brain MRI", "Spine MRI", "Knee MRI", "Shoulder MRI", "Abdominal MRI"]
    mri_records = []
    for patient in patients:
        if random.random() > 0.3:
            for _ in range(random.randint(1, 3)):
                mri_records.append(
                    {
                        "patient_id": patient["patient_id"],
                        "name": patient["name"],
                        "test_name": random.choice(mri_tests),
                        "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                        "result": random.choice(["Normal", "Abnormal - Minor", "Requires Follow-up", "Critical"]),
                        "doctor": f"Dr. {fake.last_name()}",
                        "report_image": random.choice(MEDICAL_IMAGES["mri"]),
                    }
                )
    if mri_records:
        await db.mri_records.insert_many(mri_records)

    xray_tests = ["Chest X-Ray", "Dental X-Ray", "Hand X-Ray", "Foot X-Ray", "Pelvis X-Ray"]
    xray_records = []
    for patient in patients:
        if random.random() > 0.2:
            for _ in range(random.randint(1, 4)):
                xray_records.append(
                    {
                        "patient_id": patient["patient_id"],
                        "name": patient["name"],
                        "test_name": random.choice(xray_tests),
                        "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                        "result": random.choice(["Clear", "Fracture Detected", "Inflammation", "Normal"]),
                        "doctor": f"Dr. {fake.last_name()}",
                        "report_image": random.choice(MEDICAL_IMAGES["xray"]),
                    }
                )
    if xray_records:
        await db.xray_records.insert_many(xray_records)

    ecg_tests = ["Resting ECG", "Stress ECG", "Holter Monitor", "Event Monitor"]
    ecg_records = []
    for patient in patients:
        if random.random() > 0.4:
            for _ in range(random.randint(1, 2)):
                ecg_records.append(
                    {
                        "patient_id": patient["patient_id"],
                        "name": patient["name"],
                        "test_name": random.choice(ecg_tests),
                        "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                        "result": random.choice(["Normal Sinus Rhythm", "Arrhythmia Detected", "Tachycardia", "Normal"]),
                        "doctor": f"Dr. {fake.last_name()}",
                        "report_image": random.choice(MEDICAL_IMAGES["ecg"]),
                    }
                )
    if ecg_records:
        await db.ecg_records.insert_many(ecg_records)

    treatments = ["Physical Therapy", "Medication - Antibiotics", "Surgery - Minor", "Chemotherapy", "Dialysis", "Vaccination"]
    treatment_records = []
    for patient in patients:
        if random.random() > 0.1:
            for _ in range(random.randint(1, 5)):
                medicines_str = ", ".join(random.sample(MEDICINES, random.randint(1, 3)))
                treatment_records.append(
                    {
                        "patient_id": patient["patient_id"],
                        "name": patient["name"],
                        "treatment_name": random.choice(treatments),
                        "treatment_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                        "result": random.choice(["Completed", "In Progress", "Successful", "Scheduled"]),
                        "doctor": f"Dr. {fake.last_name()}",
                        "medicines": medicines_str,
                    }
                )
    if treatment_records:
        await db.treatment_records.insert_many(treatment_records)

    blood_tests = ["Complete Blood Count", "Lipid Profile", "Liver Function Test", "Kidney Function Test", "Thyroid Panel"]
    blood_records = []
    for patient in patients:
        if random.random() > 0.2:
            for _ in range(random.randint(1, 3)):
                blood_records.append(
                    {
                        "patient_id": patient["patient_id"],
                        "name": patient["name"],
                        "test_name": random.choice(blood_tests),
                        "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                        "result": random.choice(["Normal", "Abnormal - High", "Abnormal - Low", "Within Range"]),
                        "doctor": f"Dr. {fake.last_name()}",
                        "report_image": random.choice(MEDICAL_IMAGES["blood"]),
                    }
                )
    if blood_records:
        await db.blood_profile_records.insert_many(blood_records)

    ct_tests = ["Head CT Scan", "Chest CT Scan", "Abdominal CT Scan", "Pelvic CT Scan", "Spine CT Scan"]
    ct_records = []
    for patient in patients:
        if random.random() > 0.5:
            for _ in range(random.randint(1, 2)):
                ct_records.append(
                    {
                        "patient_id": patient["patient_id"],
                        "name": patient["name"],
                        "test_name": random.choice(ct_tests),
                        "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                        "result": random.choice(["Normal", "Abnormality Detected", "Requires Further Investigation", "Clear"]),
                        "doctor": f"Dr. {fake.last_name()}",
                        "report_image": random.choice(MEDICAL_IMAGES["ct"]),
                    }
                )
    if ct_records:
        await db.ct_scan_records.insert_many(ct_records)

    return {"message": "Sample data populated successfully", "patients_created": len(patients)}


# =========================
# Routes
# =========================
@api_router.get("/")
async def root():
    return {"message": "United Patient Record System API"}


@api_router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    valid_users = {
        "doctor": {"password": "doctor123", "role": "Doctor", "name": "Dr. Smith"},
        "nurse": {"password": "nurse123", "role": "Nurse", "name": "Nurse Johnson"},
        "admin": {"password": "admin123", "role": "Administrator", "name": "Admin Davis"},
    }

    if credentials.username in valid_users:
        user_data = valid_users[credentials.username]
        if credentials.password == user_data["password"]:
            return LoginResponse(
                success=True,
                message="Login successful",
                user={"username": credentials.username, "role": user_data["role"], "name": user_data["name"]},
            )

    raise HTTPException(status_code=401, detail="Invalid credentials")


@api_router.post("/init-data")
async def initialize_data():
    return await populate_sample_data()


@api_router.post("/clear-data")
async def clear_data():
    await db.profiles.delete_many({})
    await db.mri_records.delete_many({})
    await db.xray_records.delete_many({})
    await db.ecg_records.delete_many({})
    await db.treatment_records.delete_many({})
    await db.blood_profile_records.delete_many({})
    await db.ct_scan_records.delete_many({})
    return {"message": "All data cleared successfully"}


@api_router.get("/search")
async def search_patient(term: str = Query(..., description="Patient ID or Name to search")):
    query = {"$or": [{"patient_id": term}, {"name": {"$regex": term, "$options": "i"}}]}

    profile = await db.profiles.find_one(query, {"_id": 0})

    mri_records = await db.mri_records.find(query, {"_id": 0}).to_list(1000)
    xray_records = await db.xray_records.find(query, {"_id": 0}).to_list(1000)
    ecg_records = await db.ecg_records.find(query, {"_id": 0}).to_list(1000)
    treatment_records = await db.treatment_records.find(query, {"_id": 0}).to_list(1000)
    blood_profile_records = await db.blood_profile_records.find(query, {"_id": 0}).to_list(1000)
    ct_scan_records = await db.ct_scan_records.find(query, {"_id": 0}).to_list(1000)

    mri_records = sorted(mri_records, key=lambda x: x.get("test_date", ""))
    xray_records = sorted(xray_records, key=lambda x: x.get("test_date", ""))
    ecg_records = sorted(ecg_records, key=lambda x: x.get("test_date", ""))
    treatment_records = sorted(treatment_records, key=lambda x: x.get("treatment_date", ""))
    blood_profile_records = sorted(blood_profile_records, key=lambda x: x.get("test_date", ""))
    ct_scan_records = sorted(ct_scan_records, key=lambda x: x.get("test_date", ""))

    return {
        "profile": profile,
        "mri_records": mri_records,
        "xray_records": xray_records,
        "ecg_records": ecg_records,
        "treatment_records": treatment_records,
        "blood_profile_records": blood_profile_records,
        "ct_scan_records": ct_scan_records,
    }


# ✅ NEW: B1 endpoint
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

# ---------- Deep Query Models ----------
class DeepQueryRequest(BaseModel):
    # accept multiple names soDict keys so frontend mismatch won't break
    patient_id: Optional[str] = None
    term: Optional[str] = None
    query: str

class EvidenceItem(BaseModel):
    department: str
    date: str
    title: str
    result: str
    doctor: str
    record: Dict[str, Any]

class DeepQueryResponse(BaseModel):
    patient_id: str
    matched_departments: List[str]
    answer: str
    evidence: List[EvidenceItem]


# ---------- Helper: choose which department(s) based on doctor question ----------
def infer_departments_from_query(q: str) -> List[str]:
    ql = (q or "").lower()

    dept_map = {
        "blood_profile_records": ["blood", "cbc", "lipid", "liver", "kidney", "thyroid", "hemoglobin"],
        "mri_records": ["mri", "brain mri", "spine mri"],
        "xray_records": ["xray", "x-ray", "chest xray", "fracture"],
        "ecg_records": ["ecg", "ekg", "arrhythmia", "tachycardia", "heart"],
        "ct_scan_records": ["ct", "ct scan", "head ct", "chest ct"],
        "treatment_records": ["treatment", "medicine", "medication", "surgery", "therapy", "vaccination", "dialysis"],
    }

    matched = []
    for dept, keywords in dept_map.items():
        if any(k in ql for k in keywords):
            matched.append(dept)

    # If doctor asked something generic like "fetch reports" or "latest reports"
    # return all departments
    if not matched:
        generic_triggers = ["report", "reports", "latest", "recent", "history", "records", "summary", "summarize"]
        if any(k in ql for k in generic_triggers):
            return list(dept_map.keys())

    return matched


# ---------- Deep Query Endpoint ----------
@api_router.post("/deep-query", response_model=DeepQueryResponse)
async def deep_query(payload: DeepQueryRequest):
    """
    Doctor asks ANY question -> backend decides what to fetch for that patient.
    For now: rule-based routing + return relevant records from MongoDB.
    Later: plug AI summarizer.
    """

    # resolve patient_id
    pid = (payload.patient_id or payload.term or "").strip()
    if not pid:
        raise HTTPException(status_code=400, detail="patient_id (or term) is required")

    q = (payload.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="query is required")

    # find patient profile
    profile = await db.profiles.find_one({"patient_id": pid}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail=f"Patient not found: {pid}")

    # decide which department(s) to fetch based on query
    departments = infer_departments_from_query(q)

    # if nothing matched and not generic -> still return basic "no match"
    if not departments:
        return DeepQueryResponse(
            patient_id=pid,
            matched_departments=[],
            answer="I understood your question, but I couldn't map it to a department yet. Try words like blood/mri/xray/ecg/ct/treatment or 'latest reports'.",
            evidence=[]
        )

    evidence: List[EvidenceItem] = []

    # fetch records from each department
    for dept in departments:
        collection = db[dept]
        records = await collection.find({"patient_id": pid}, {"_id": 0}).to_list(1000)

        # pick date field
        date_key = "treatment_date" if dept == "treatment_records" else "test_date"
        records_sorted = sorted(records, key=lambda r: r.get(date_key, ""), reverse=True)

        # take top 3 most recent
        top = records_sorted[:3]

        for r in top:
            # build a readable title
            if dept == "treatment_records":
                title = r.get("treatment_name", "Treatment")
                result = r.get("result", "")
            else:
                title = r.get("test_name", "Test")
                result = r.get("result", "")

            evidence.append(
                EvidenceItem(
                    department=dept,
                    date=r.get(date_key, ""),
                    title=title,
                    result=result,
                    doctor=r.get("doctor", ""),
                    record=r
                )
            )

    # prepare a simple answer (later replace with AI summary)
    dept_names = [d.replace("_records", "").replace("_", " ").title() for d in departments]
    answer = (
        f"Fetched {len(evidence)} recent record(s) for patient {profile.get('name')} ({pid}) "
        f"from: {', '.join(dept_names)}. "
        f"Next step: add a real summarizer (AI) to interpret these results."
    )

    return DeepQueryResponse(
        patient_id=pid,
        matched_departments=departments,
        answer=answer,
        evidence=evidence
    )

@api_router.get("/analytics/{patient_id}")
async def get_patient_analytics(patient_id: str):
    query = {"patient_id": patient_id}

    mri_records = await db.mri_records.find(query, {"_id": 0}).to_list(1000)
    xray_records = await db.xray_records.find(query, {"_id": 0}).to_list(1000)
    ecg_records = await db.ecg_records.find(query, {"_id": 0}).to_list(1000)
    treatment_records = await db.treatment_records.find(query, {"_id": 0}).to_list(1000)
    blood_profile_records = await db.blood_profile_records.find(query, {"_id": 0}).to_list(1000)
    ct_scan_records = await db.ct_scan_records.find(query, {"_id": 0}).to_list(1000)

    total_tests = len(mri_records) + len(xray_records) + len(ecg_records) + len(blood_profile_records) + len(ct_scan_records)

    departments_visited = {
        "MRI": len(mri_records),
        "X-Ray": len(xray_records),
        "ECG": len(ecg_records),
        "Blood Profile": len(blood_profile_records),
        "CT Scan": len(ct_scan_records),
        "Treatment": len(treatment_records),
    }

    all_visits = []
    for record in mri_records:
        all_visits.append({"date": record["test_date"], "type": "MRI", "test": record["test_name"]})
    for record in xray_records:
        all_visits.append({"date": record["test_date"], "type": "X-Ray", "test": record["test_name"]})
    for record in ecg_records:
        all_visits.append({"date": record["test_date"], "type": "ECG", "test": record["test_name"]})
    for record in blood_profile_records:
        all_visits.append({"date": record["test_date"], "type": "Blood Profile", "test": record["test_name"]})
    for record in ct_scan_records:
        all_visits.append({"date": record["test_date"], "type": "CT Scan", "test": record["test_name"]})
    for record in treatment_records:
        all_visits.append({"date": record["treatment_date"], "type": "Treatment", "test": record["treatment_name"]})

    all_visits = sorted(all_visits, key=lambda x: x["date"])

    completed = sum(1 for r in treatment_records if "Completed" in r.get("result", "") or "Successful" in r.get("result", ""))
    in_progress = sum(1 for r in treatment_records if "Progress" in r.get("result", ""))
    scheduled = sum(1 for r in treatment_records if "Scheduled" in r.get("result", ""))

    treatment_summary = {"total": len(treatment_records), "completed": completed, "in_progress": in_progress, "scheduled": scheduled}

    normal_count = 0
    abnormal_count = 0
    for record in mri_records + xray_records + ecg_records + blood_profile_records + ct_scan_records:
        result = (record.get("result", "") or "").lower()
        if "normal" in result or "clear" in result or "within range" in result:
            normal_count += 1
        else:
            abnormal_count += 1

    if normal_count > abnormal_count * 2:
        health_trend = "Excellent"
    elif normal_count > abnormal_count:
        health_trend = "Good"
    elif normal_count == abnormal_count:
        health_trend = "Stable"
    else:
        health_trend = "Needs Attention"

    recent_results = all_visits[-5:] if len(all_visits) >= 5 else all_visits

    return {
        "total_visits": len(all_visits),
        "total_tests": total_tests,
        "departments_visited": departments_visited,
        "visit_timeline": all_visits,
        "treatment_summary": treatment_summary,
        "health_trend": health_trend,
        "recent_results": recent_results,
    }


@api_router.get("/department/{department_name}")
async def get_department_records(department_name: str):
    department_map = {
        "mri": "mri_records",
        "xray": "xray_records",
        "x-ray": "xray_records",
        "ecg": "ecg_records",
        "blood_profile": "blood_profile_records",
        "blood-test": "blood_profile_records",
        "ct_scan": "ct_scan_records",
        "ct-scan": "ct_scan_records",
        "treatment": "treatment_records",
    }

    collection_name = department_map.get(department_name.lower())
    if not collection_name:
        raise HTTPException(status_code=404, detail="Department not found")

    collection = db[collection_name]
    records = await collection.find({}, {"_id": 0}).to_list(1000)

    if collection_name == "treatment_records":
        records = sorted(records, key=lambda x: x.get("treatment_date", ""))
    else:
        records = sorted(records, key=lambda x: x.get("test_date", ""))

    return {"department": department_name, "records": records, "total": len(records)}


@api_router.get("/patients")
async def get_all_patients():
    profiles = await db.profiles.find({}, {"_id": 0, "patient_id": 1, "name": 1}).to_list(1000)
    return {"patients": profiles}


# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()