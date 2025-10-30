from fastapi import FastAPI, APIRouter, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
from faker import Faker
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize Faker
fake = Faker()

# Define Models
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

class XRayRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    test_name: str
    test_date: str
    result: str
    doctor: str

class ECGRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    test_name: str
    test_date: str
    result: str
    doctor: str

class TreatmentRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    name: str
    treatment_name: str
    treatment_date: str
    result: str
    doctor: str

class SearchResponse(BaseModel):
    profile: Optional[Profile] = None
    mri_records: List[MRIRecord] = []
    xray_records: List[XRayRecord] = []
    ecg_records: List[ECGRecord] = []
    treatment_records: List[TreatmentRecord] = []

# Helper function to generate sample data
async def populate_sample_data():
    """Populate all department collections with sample patient data using Faker"""
    
    # Clear existing data
    await db.profiles.delete_many({})
    await db.mri_records.delete_many({})
    await db.xray_records.delete_many({})
    await db.ecg_records.delete_many({})
    await db.treatment_records.delete_many({})
    
    # Generate 15 patients
    patients = []
    for i in range(1, 16):
        patient_id = f"P{1000 + i}"
        name = fake.name()
        patients.append({
            "patient_id": patient_id,
            "name": name,
            "age": random.randint(18, 85),
            "gender": random.choice(["Male", "Female"]),
            "blood_group": random.choice(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]),
            "address": fake.address().replace('\n', ', '),
            "phone": fake.phone_number(),
            "registration_date": fake.date_between(start_date="-2y", end_date="today").isoformat()
        })
    
    # Insert profiles
    await db.profiles.insert_many(patients)
    
    # Generate MRI records
    mri_tests = ["Brain MRI", "Spine MRI", "Knee MRI", "Shoulder MRI", "Abdominal MRI"]
    mri_records = []
    for patient in patients:
        if random.random() > 0.3:  # 70% chance of having MRI
            for _ in range(random.randint(1, 3)):
                mri_records.append({
                    "patient_id": patient["patient_id"],
                    "name": patient["name"],
                    "test_name": random.choice(mri_tests),
                    "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                    "result": random.choice(["Normal", "Abnormal - Minor", "Requires Follow-up", "Critical"]),
                    "doctor": f"Dr. {fake.last_name()}"
                })
    if mri_records:
        await db.mri_records.insert_many(mri_records)
    
    # Generate X-Ray records
    xray_tests = ["Chest X-Ray", "Dental X-Ray", "Hand X-Ray", "Foot X-Ray", "Pelvis X-Ray"]
    xray_records = []
    for patient in patients:
        if random.random() > 0.2:  # 80% chance of having X-Ray
            for _ in range(random.randint(1, 4)):
                xray_records.append({
                    "patient_id": patient["patient_id"],
                    "name": patient["name"],
                    "test_name": random.choice(xray_tests),
                    "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                    "result": random.choice(["Clear", "Fracture Detected", "Inflammation", "Normal"]),
                    "doctor": f"Dr. {fake.last_name()}"
                })
    if xray_records:
        await db.xray_records.insert_many(xray_records)
    
    # Generate ECG records
    ecg_tests = ["Resting ECG", "Stress ECG", "Holter Monitor", "Event Monitor"]
    ecg_records = []
    for patient in patients:
        if random.random() > 0.4:  # 60% chance of having ECG
            for _ in range(random.randint(1, 2)):
                ecg_records.append({
                    "patient_id": patient["patient_id"],
                    "name": patient["name"],
                    "test_name": random.choice(ecg_tests),
                    "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                    "result": random.choice(["Normal Sinus Rhythm", "Arrhythmia Detected", "Tachycardia", "Normal"]),
                    "doctor": f"Dr. {fake.last_name()}"
                })
    if ecg_records:
        await db.ecg_records.insert_many(ecg_records)
    
    # Generate Treatment records
    treatments = ["Physical Therapy", "Medication - Antibiotics", "Surgery - Minor", "Chemotherapy", "Dialysis", "Vaccination"]
    treatment_records = []
    for patient in patients:
        if random.random() > 0.1:  # 90% chance of having treatment
            for _ in range(random.randint(1, 5)):
                treatment_records.append({
                    "patient_id": patient["patient_id"],
                    "name": patient["name"],
                    "treatment_name": random.choice(treatments),
                    "treatment_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
                    "result": random.choice(["Completed", "In Progress", "Successful", "Scheduled"]),
                    "doctor": f"Dr. {fake.last_name()}"
                })
    if treatment_records:
        await db.treatment_records.insert_many(treatment_records)
    
    return {"message": "Sample data populated successfully", "patients_created": len(patients)}

# Routes
@api_router.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Hospital Patient Data Retrieval System API"}

@api_router.post("/init-data")
async def initialize_data():
    """Initialize database with sample patient data"""
    result = await populate_sample_data()
    return result

@api_router.get("/search")
async def search_patient(term: str = Query(..., description="Patient ID or Name to search")):
    """Search patient records across all departments
    
    Args:
        term: Patient ID (e.g., P1001) or Name (partial match supported)
    
    Returns:
        Unified patient data from all departments sorted by date
    """
    
    # Create search query for patient_id exact match or name partial match (case-insensitive)
    query = {
        "$or": [
            {"patient_id": term},
            {"name": {"$regex": term, "$options": "i"}}
        ]
    }
    
    # Search profile
    profile = await db.profiles.find_one(query, {"_id": 0})
    
    # Search all department records
    mri_records = await db.mri_records.find(query, {"_id": 0}).to_list(1000)
    xray_records = await db.xray_records.find(query, {"_id": 0}).to_list(1000)
    ecg_records = await db.ecg_records.find(query, {"_id": 0}).to_list(1000)
    treatment_records = await db.treatment_records.find(query, {"_id": 0}).to_list(1000)
    
    # Sort records by date (ascending)
    mri_records = sorted(mri_records, key=lambda x: x.get("test_date", ""))
    xray_records = sorted(xray_records, key=lambda x: x.get("test_date", ""))
    ecg_records = sorted(ecg_records, key=lambda x: x.get("test_date", ""))
    treatment_records = sorted(treatment_records, key=lambda x: x.get("treatment_date", ""))
    
    return {
        "profile": profile,
        "mri_records": mri_records,
        "xray_records": xray_records,
        "ecg_records": ecg_records,
        "treatment_records": treatment_records
    }

@api_router.get("/patients")
async def get_all_patients():
    """Get list of all patient IDs and names for reference"""
    profiles = await db.profiles.find({}, {"_id": 0, "patient_id": 1, "name": 1}).to_list(1000)
    return {"patients": profiles}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
