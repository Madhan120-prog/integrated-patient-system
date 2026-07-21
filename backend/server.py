from fastapi import FastAPI, APIRouter, Query, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import io
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
import random
from collections import Counter
from google import genai
from google.genai import types as genai_types
from google.genai import errors as genai_errors
from gtts import gTTS
import asyncio
import json
import shutil
import uuid

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Gemini LLM client (used by /deep-query and /analyze-document)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_MODEL = "gemini-3-flash-preview"
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

async def generate_content_with_retry(**kwargs):
    """Gemini's free tier occasionally returns 503 'high demand' — one retry
    resolves it almost every time (observed repeatedly in testing)."""
    try:
        return await gemini_client.aio.models.generate_content(**kwargs)
    except genai_errors.ServerError:
        await asyncio.sleep(1)
        try:
            return await gemini_client.aio.models.generate_content(**kwargs)
        except genai_errors.ServerError:
            raise HTTPException(
                status_code=503,
                detail="The AI is temporarily overloaded. Please try again in a moment."
            )

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Create uploads directory for file analysis
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Define Models
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

class DeepQueryRequest(BaseModel):
    patient_id: str
    question: str

class DeepQueryResponse(BaseModel):
    answer: str
    evidence: List[dict] = []
    matched_departments: List[str] = []

class TTSRequest(BaseModel):
    text: str

@api_router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Server-side text-to-speech — sidesteps flaky browser SpeechSynthesis engines"""
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', request.text)
    clean_text = re.sub(r'[*#_`]', '', clean_text).strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="No text to speak")

    buffer = io.BytesIO()
    gTTS(text=clean_text, lang='en').write_to_fp(buffer)
    return Response(content=buffer.getvalue(), media_type="audio/mpeg")

from data.seed import build_seed_data

async def populate_sample_data():
    """Populate all department collections with curated oncology patient data"""

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

    seed_data = build_seed_data(extra_count=488)

    await db.profiles.insert_many(seed_data["profiles"])
    for coll_name in ["mri_records", "xray_records", "ecg_records",
                       "blood_profile_records", "ct_scan_records", "treatment_records"]:
        if seed_data[coll_name]:
            await db[coll_name].insert_many(seed_data[coll_name])

    return {"message": "Sample data populated successfully", "patients_created": len(seed_data["profiles"])}

# Routes
@api_router.get("/")
async def root():
    """Root endpoint"""
    return {"message": "United Patient Record System API"}

@api_router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Simple demo login endpoint"""
    # Demo credentials
    valid_users = {
        "doctor": {"password": "doctor123", "role": "Doctor", "name": "Dr. Smith"},
        "nurse": {"password": "nurse123", "role": "Nurse", "name": "Nurse Johnson"},
        "admin": {"password": "admin123", "role": "Administrator", "name": "Admin Davis"}
    }
    
    if credentials.username in valid_users:
        user_data = valid_users[credentials.username]
        if credentials.password == user_data["password"]:
            return LoginResponse(
                success=True,
                message="Login successful",
                user={
                    "username": credentials.username,
                    "role": user_data["role"],
                    "name": user_data["name"]
                }
            )
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@api_router.post("/init-data")
async def initialize_data():
    """Initialize database with sample patient data"""
    result = await populate_sample_data()
    return result

@api_router.post("/clear-data")
async def clear_data():
    """Clear all patient data from database"""
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
    blood_profile_records = await db.blood_profile_records.find(query, {"_id": 0}).to_list(1000)
    ct_scan_records = await db.ct_scan_records.find(query, {"_id": 0}).to_list(1000)
    
    # Sort records by date (ascending)
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
        "ct_scan_records": ct_scan_records
    }

@api_router.get("/analytics/{patient_id}")
async def get_patient_analytics(patient_id: str):
    """Get patient analytics and statistics"""
    
    query = {"patient_id": patient_id}
    
    # Get all records
    mri_records = await db.mri_records.find(query, {"_id": 0}).to_list(1000)
    xray_records = await db.xray_records.find(query, {"_id": 0}).to_list(1000)
    ecg_records = await db.ecg_records.find(query, {"_id": 0}).to_list(1000)
    treatment_records = await db.treatment_records.find(query, {"_id": 0}).to_list(1000)
    blood_profile_records = await db.blood_profile_records.find(query, {"_id": 0}).to_list(1000)
    ct_scan_records = await db.ct_scan_records.find(query, {"_id": 0}).to_list(1000)
    
    # Calculate total tests
    total_tests = len(mri_records) + len(xray_records) + len(ecg_records) + len(blood_profile_records) + len(ct_scan_records)
    
    # Department breakdown
    departments_visited = {
        "MRI": len(mri_records),
        "X-Ray": len(xray_records),
        "ECG": len(ecg_records),
        "Blood Profile": len(blood_profile_records),
        "CT Scan": len(ct_scan_records),
        "Treatment": len(treatment_records)
    }
    
    # Create visit timeline (all tests combined and sorted)
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
    
    # Treatment summary
    completed = sum(1 for r in treatment_records if "Completed" in r.get("result", "") or "Successful" in r.get("result", ""))
    in_progress = sum(1 for r in treatment_records if "Progress" in r.get("result", ""))
    scheduled = sum(1 for r in treatment_records if "Scheduled" in r.get("result", ""))
    
    treatment_summary = {
        "total": len(treatment_records),
        "completed": completed,
        "in_progress": in_progress,
        "scheduled": scheduled
    }
    
    # Health trend analysis (based on recent test results)
    normal_count = 0
    abnormal_count = 0
    
    for record in mri_records + xray_records + ecg_records + blood_profile_records + ct_scan_records:
        result = record.get("result", "").lower()
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
    
    # Recent results (last 5)
    recent_results = all_visits[-5:] if len(all_visits) >= 5 else all_visits
    
    return {
        "total_visits": len(all_visits),
        "total_tests": total_tests,
        "departments_visited": departments_visited,
        "visit_timeline": all_visits,
        "treatment_summary": treatment_summary,
        "health_trend": health_trend,
        "recent_results": recent_results
    }

@api_router.get("/department/{department_name}")
async def get_department_records(department_name: str):
    """Get all patient records for a specific department
    
    Args:
        department_name: Name of department (mri, xray, ecg, blood_profile, ct_scan, treatment)
    
    Returns:
        All records from that department with patient info
    """
    
    department_map = {
        "mri": "mri_records",
        "xray": "xray_records",
        "x-ray": "xray_records",
        "ecg": "ecg_records",
        "blood_profile": "blood_profile_records",
        "blood-test": "blood_profile_records",
        "ct_scan": "ct_scan_records",
        "ct-scan": "ct_scan_records",
        "treatment": "treatment_records"
    }
    
    collection_name = department_map.get(department_name.lower())
    if not collection_name:
        raise HTTPException(status_code=404, detail="Department not found")
    
    collection = db[collection_name]
    records = await collection.find({}, {"_id": 0}).to_list(None)
    
    # Sort by date
    if collection_name == "treatment_records":
        records = sorted(records, key=lambda x: x.get("treatment_date", ""))
    else:
        records = sorted(records, key=lambda x: x.get("test_date", ""))
    
    return {
        "department": department_name,
        "records": records,
        "total": len(records)
    }

@api_router.get("/patients")
async def get_all_patients():
    """Get list of all patient IDs and names for reference"""
    profiles = await db.profiles.find({}, {"_id": 0, "patient_id": 1, "name": 1}).to_list(None)
    return {"patients": profiles}

@api_router.post("/deep-query", response_model=DeepQueryResponse)
async def deep_query(request: DeepQueryRequest):
    """AI-powered clinical assistant to analyze patient records and answer questions"""
    
    patient_id = request.patient_id
    question = request.question
    
    query = {"patient_id": patient_id}

    profile = await db.profiles.find_one(query, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Smart context: only fetch/send departments the question actually needs —
    # cuts tokens and DB queries for narrow questions, and keeps greetings/general
    # questions from pulling in patient data at all.
    question_lower = question.lower()
    dept_keywords = {
        'MRI': ['mri', 'brain', 'spine', 'magnetic'],
        'X-Ray': ['xray', 'x-ray', 'chest', 'bone', 'fracture'],
        'ECG': ['ecg', 'heart', 'cardiac', 'rhythm'],
        'Blood Profile': ['blood', 'hemoglobin', 'platelet', 'wbc', 'rbc', 'lipid', 'liver', 'kidney', 'thyroid'],
        'CT Scan': ['ct', 'scan', 'computed tomography'],
        'Treatment': ['treatment', 'medicine', 'medication', 'prescription', 'therapy'],
    }
    overview_keywords = ['summarize', 'summary', 'overview', 'status', 'records',
                          'details', 'history', 'everything', 'concerns', 'concerning']
    keyword_matched = [d for d, kws in dept_keywords.items() if any(k in question_lower for k in kws)]
    is_overview = not keyword_matched and any(w in question_lower for w in overview_keywords)
    needs_dept = lambda d: d in keyword_matched or is_overview

    async def fetch(coll, name):
        if not needs_dept(name):
            return []
        return await db[coll].find(query, {"_id": 0}).to_list(1000)

    mri_records = await fetch("mri_records", "MRI")
    xray_records = await fetch("xray_records", "X-Ray")
    ecg_records = await fetch("ecg_records", "ECG")
    blood_profile_records = await fetch("blood_profile_records", "Blood Profile")
    ct_scan_records = await fetch("ct_scan_records", "CT Scan")
    treatment_records = await fetch("treatment_records", "Treatment")

    patient_context = f"""
PATIENT PROFILE:
- Name: {profile.get('name')}
- Patient ID: {profile.get('patient_id')}
- Age: {profile.get('age')} years
- Gender: {profile.get('gender')}
- Blood Group: {profile.get('blood_group')}
- Address: {profile.get('address')}
- Phone: {profile.get('phone')}
- Registration Date: {profile.get('registration_date')}
"""
    if needs_dept('MRI'):
        patient_context += f"\nMRI RECORDS ({len(mri_records)} records):\n{json.dumps(mri_records, indent=2) if mri_records else 'No MRI records'}\n"
    if needs_dept('X-Ray'):
        patient_context += f"\nX-RAY RECORDS ({len(xray_records)} records):\n{json.dumps(xray_records, indent=2) if xray_records else 'No X-Ray records'}\n"
    if needs_dept('ECG'):
        patient_context += f"\nECG RECORDS ({len(ecg_records)} records):\n{json.dumps(ecg_records, indent=2) if ecg_records else 'No ECG records'}\n"
    if needs_dept('Blood Profile'):
        patient_context += f"\nBLOOD PROFILE RECORDS ({len(blood_profile_records)} records):\n{json.dumps(blood_profile_records, indent=2) if blood_profile_records else 'No blood profile records'}\n"
    if needs_dept('CT Scan'):
        patient_context += f"\nCT SCAN RECORDS ({len(ct_scan_records)} records):\n{json.dumps(ct_scan_records, indent=2) if ct_scan_records else 'No CT scan records'}\n"
    if needs_dept('Treatment'):
        patient_context += f"\nTREATMENT RECORDS ({len(treatment_records)} records):\n{json.dumps(treatment_records, indent=2) if treatment_records else 'No treatment records'}\n"

    system_message = """You are DocAssist, an AI clinical assistant for XYZ Hospital, a cancer
treatment center. You have access to a patient's complete medical records including MRI scans,
X-Rays, ECG tests, blood profiles, CT scans, and treatment history.

You are talking to a doctor or nurse mid-shift — write like a chart note, not an essay.

Formatting:
- Lead with the answer. No "Based on the medical records..." preamble.
- If any finding is abnormal or concerning, put it first, flagged clearly (e.g. "⚠").
- Use standard clinical shorthand doctors already know: WBC, Hgb, LFT, CBC, Hx, Tx, f/u, q3w — don't spell these out.
- Short bullets over paragraphs. Bold only abnormal values, not every term.
- End with one relevant next step or follow-up question, only if it adds value — skip it for simple factual lookups.

Guidelines:
- Always reference specific records (dates, values) when answering
- If asked about something not in the records, say so directly — don't pad
- Never make diagnoses - only summarize and analyze existing data

Scope — read this carefully, it controls when patient data appears in your answer:
- Greetings ("hi", "hello", "how are you") → reply naturally in one short sentence.
  Do NOT mention the patient, do NOT list any records, do NOT summarize anything.
- General/medical knowledge questions unrelated to this specific patient (e.g. "what
  is neutropenia?", "what does CEA measure?") → answer generally, like any knowledgeable
  clinical assistant would. Do NOT pull in this patient's specific values unless asked.
- Anything about the patient — their records, status, results, treatment, or an
  explicit request like "summarize" / "what do you have on this patient" → this is
  when the full chart-note style above applies.
Patient data is available in every turn, but only use it when the question actually
calls for it. Including it in a reply to "hi" is a failure mode — do not do that."""

    try:
        if not gemini_client:
            raise HTTPException(status_code=500, detail="LLM API key not configured")

        # Create user message with patient context
        prompt = f"""Based on the following patient records, please answer this question: {question}

{patient_context}"""

        # Get LLM response
        result = await generate_content_with_retry(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(system_instruction=system_message),
        )
        response = result.text

        # Evidence departments: keyword matches, or (for overview questions) every
        # department that actually has data — computed earlier alongside fetching
        matched_departments = list(keyword_matched)
        if is_overview:
            for dept, records in [('MRI', mri_records), ('X-Ray', xray_records), ('ECG', ecg_records),
                                   ('Blood Profile', blood_profile_records), ('CT Scan', ct_scan_records),
                                   ('Treatment', treatment_records)]:
                if records:
                    matched_departments.append(dept)

        # Collect relevant evidence records (most recent from each matched department)
        evidence = []
        if 'MRI' in matched_departments and mri_records:
            evidence.extend(sorted(mri_records, key=lambda x: x.get('test_date', ''), reverse=True)[:2])
        if 'X-Ray' in matched_departments and xray_records:
            evidence.extend(sorted(xray_records, key=lambda x: x.get('test_date', ''), reverse=True)[:2])
        if 'ECG' in matched_departments and ecg_records:
            evidence.extend(sorted(ecg_records, key=lambda x: x.get('test_date', ''), reverse=True)[:2])
        if 'Blood Profile' in matched_departments and blood_profile_records:
            evidence.extend(sorted(blood_profile_records, key=lambda x: x.get('test_date', ''), reverse=True)[:2])
        if 'CT Scan' in matched_departments and ct_scan_records:
            evidence.extend(sorted(ct_scan_records, key=lambda x: x.get('test_date', ''), reverse=True)[:2])
        if 'Treatment' in matched_departments and treatment_records:
            evidence.extend(sorted(treatment_records, key=lambda x: x.get('treatment_date', ''), reverse=True)[:2])
        
        return DeepQueryResponse(
            answer=response,
            evidence=evidence[:6],  # Limit to 6 evidence cards
            matched_departments=matched_departments
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deep query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

class FileAnalysisResponse(BaseModel):
    analysis: str
    file_type: str
    suggestions: List[str] = []

@api_router.post("/analyze-document", response_model=FileAnalysisResponse)
async def analyze_document(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    question: str = Form(default="Analyze this medical document and provide a detailed summary.")
):
    """Analyze uploaded medical documents (images, PDFs) using Gemini AI"""
    
    # Validate file type
    allowed_types = {
        'image/png': 'image/png',
        'image/jpeg': 'image/jpeg',
        'image/jpg': 'image/jpeg',
        'image/webp': 'image/webp',
        'application/pdf': 'application/pdf'
    }
    
    content_type = file.content_type
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {content_type}. Allowed: PNG, JPEG, WebP, PDF"
        )
    
    # Get patient context
    query = {"patient_id": patient_id}
    profile = await db.profiles.find_one(query, {"_id": 0})
    
    patient_context = ""
    if profile:
        patient_context = f"""
Patient Context:
- Name: {profile.get('name')}
- Patient ID: {profile.get('patient_id')}
- Age: {profile.get('age')} years
- Gender: {profile.get('gender')}
- Blood Group: {profile.get('blood_group')}
"""
    
    # Save uploaded file temporarily
    file_id = str(uuid.uuid4())
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
    temp_file_path = UPLOAD_DIR / f"{file_id}.{file_extension}"
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        if not gemini_client:
            raise HTTPException(status_code=500, detail="LLM API key not configured")

        system_message = """You are DocAssist, an AI medical document analyzer for XYZ Hospital.
You are analyzing a medical document (X-ray, MRI, CT scan, lab report PDF, etc.).

Your role is to:
1. Identify the type of medical document
2. Describe what you observe in the image/document
3. Highlight any notable findings or areas of concern
4. Provide a professional medical summary

Guidelines:
- Be thorough but concise
- Use appropriate medical terminology
- Note any abnormalities or areas requiring attention
- DO NOT make definitive diagnoses - provide observations and suggest follow-up
- Always recommend consulting with the appropriate specialist
- Be professional and objective"""

        # Create file content for Gemini
        file_part = genai_types.Part.from_bytes(
            data=temp_file_path.read_bytes(),
            mime_type=allowed_types[content_type]
        )

        # Create message with file attachment
        full_question = f"{patient_context}\n\nDoctor's Question: {question}"

        # Get AI analysis
        result = await generate_content_with_retry(
            model=GEMINI_MODEL,
            contents=[full_question, file_part],
            config=genai_types.GenerateContentConfig(system_instruction=system_message),
        )
        analysis = result.text
        
        # Determine file type for response
        file_type_map = {
            'image/png': 'Medical Image',
            'image/jpeg': 'Medical Image',
            'image/webp': 'Medical Image',
            'application/pdf': 'PDF Document'
        }
        
        # Generate suggestions based on content
        suggestions = [
            "Review findings with attending physician",
            "Compare with previous imaging if available",
            "Document observations in patient record"
        ]
        
        return FileAnalysisResponse(
            analysis=analysis,
            file_type=file_type_map.get(content_type, 'Unknown'),
            suggestions=suggestions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing document: {str(e)}")
    
    finally:
        # Clean up temp file
        if temp_file_path.exists():
            temp_file_path.unlink()

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
