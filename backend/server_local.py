from fastapi import FastAPI, APIRouter, Query, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from faker import Faker
import random
from collections import Counter
import json
import shutil
import uuid
import base64
import httpx

# Optional imports for PDF/Image processing
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    
try:
    from PIL import Image
    import io
    IMAGE_SUPPORT = True
except ImportError:
    IMAGE_SUPPORT = False

# OpenAI import
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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

# Create uploads directory for file analysis
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize OpenAI client
openai_client = None
if OPENAI_AVAILABLE:
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        openai_client = AsyncOpenAI(api_key=api_key)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CLINICAL SYSTEM PROMPTS - Grounded, Safe, Doctor-Friendly
# ============================================================================

DOCASSIST_SYSTEM_PROMPT = """You are DocAssist, an AI clinical assistant for XYZ Hospital designed to help doctors analyze patient records.

## YOUR ROLE
- Summarize and analyze patient medical records accurately
- Flag abnormal values explicitly with clinical context
- Help doctors quickly understand patient history
- Support clinical decision-making with data-driven insights

## SAFETY GUIDELINES (CRITICAL)
1. **NEVER diagnose** - Only summarize existing data and highlight patterns
2. **NEVER prescribe** - Only reference existing prescriptions in records
3. **NEVER speculate** - If data is missing, clearly state "No records available for [X]"
4. **ALWAYS ground answers** - Every statement must reference specific records with dates
5. **FLAG abnormals clearly** - Use format: "⚠️ ABNORMAL: [value] ([normal range])"

## RESPONSE FORMAT
- Be concise but thorough
- Use bullet points for clarity
- Include dates for all referenced records
- Separate findings by department/test type
- End with "📋 Summary" for quick overview

## CAUTIOUS LANGUAGE
- Use: "Records indicate...", "Based on available data...", "The [date] report shows..."
- Avoid: "The patient has...", "You should...", "This means..."
- For abnormals: "This value is outside the normal reference range and may warrant clinical review"

## HANDLING FOLLOW-UP QUESTIONS
- Maintain context from previous messages
- Reference earlier discussed findings when relevant
- If asked about something previously mentioned, provide additional detail"""

DOCUMENT_ANALYSIS_PROMPT = """You are DocAssist analyzing a medical document (report/scan/lab result).

## YOUR TASK
1. **Identify document type** (X-Ray, MRI, CT, ECG, Blood Report, etc.)
2. **Extract key findings** - List all significant observations
3. **Flag abnormalities** - Clearly mark any values outside normal range
4. **Provide summary** - Doctor-friendly overview in 2-3 sentences

## SAFETY RULES
- DO NOT make diagnoses - only describe what you observe
- DO NOT recommend treatments
- DO NOT speculate on conditions not explicitly mentioned
- ALWAYS recommend physician review for any abnormalities

## OUTPUT FORMAT
### Document Type: [type]
### Key Findings:
- [Finding 1]
- [Finding 2]
### ⚠️ Abnormal Values (if any):
- [Value]: [observed] (Normal: [range])
### Summary:
[2-3 sentence summary for quick physician review]
### Recommendation:
[Standard recommendation for follow-up if abnormals present]"""

# ============================================================================
# FALLBACK STRATEGIES - When LLM is unavailable
# ============================================================================

class FallbackAnalyzer:
    """Rule-based fallback when LLM is unavailable"""
    
    @staticmethod
    def analyze_blood_values(records: List[dict]) -> str:
        """Basic rule-based blood value analysis"""
        findings = []
        for record in records:
            result = record.get('result', '').lower()
            test_name = record.get('test_name', 'Unknown Test')
            test_date = record.get('test_date', 'Unknown Date')
            
            if 'abnormal' in result or 'high' in result or 'low' in result:
                findings.append(f"⚠️ {test_name} ({test_date}): {record.get('result')}")
            else:
                findings.append(f"✓ {test_name} ({test_date}): {record.get('result')}")
        
        return "\n".join(findings) if findings else "No blood profile records available."
    
    @staticmethod
    def summarize_patient(profile: dict, records: dict) -> str:
        """Basic patient summary without LLM"""
        summary = f"""
📋 PATIENT SUMMARY (Fallback Mode - LLM Unavailable)

**Patient:** {profile.get('name', 'Unknown')} ({profile.get('patient_id', 'N/A')})
**Age/Gender:** {profile.get('age', 'N/A')} years / {profile.get('gender', 'N/A')}
**Blood Group:** {profile.get('blood_group', 'N/A')}

**Records Available:**
- MRI: {len(records.get('mri', []))} record(s)
- X-Ray: {len(records.get('xray', []))} record(s)
- ECG: {len(records.get('ecg', []))} record(s)
- Blood Profile: {len(records.get('blood', []))} record(s)
- CT Scan: {len(records.get('ct', []))} record(s)
- Treatments: {len(records.get('treatment', []))} record(s)

⚠️ Note: AI analysis is temporarily unavailable. Please review records manually or try again later.
"""
        return summary
    
    @staticmethod
    def get_error_message(error_type: str = "generic") -> str:
        """Safe error messages that don't break UI"""
        messages = {
            "api_key": "AI assistant is not configured. Please check API key settings. You can still view patient records manually.",
            "rate_limit": "AI service is temporarily busy. Please try again in a moment. Patient records are still accessible.",
            "network": "Unable to connect to AI service. Please check your internet connection. Patient data is available offline.",
            "generic": "AI analysis is temporarily unavailable. Please try again or review records manually."
        }
        return messages.get(error_type, messages["generic"])

# ============================================================================
# PDF AND IMAGE PROCESSING
# ============================================================================

def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF using pdfplumber"""
    if not PDF_SUPPORT:
        return "[PDF text extraction not available - install pdfplumber]"
    
    try:
        text_content = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(f"--- Page {page_num} ---\n{page_text}")
        
        return "\n\n".join(text_content) if text_content else "[No text could be extracted from PDF]"
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return f"[PDF extraction failed: {str(e)}]"

def encode_image_to_base64(file_path: Path) -> str:
    """Encode image to base64 for OpenAI Vision API"""
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_mime_type(file_path: Path) -> str:
    """Get MIME type from file extension"""
    extension = file_path.suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
        '.gif': 'image/gif'
    }
    return mime_types.get(extension, 'image/jpeg')

# ============================================================================
# OPENAI API FUNCTIONS
# ============================================================================

async def call_openai_chat(
    messages: List[dict],
    model: str = "gpt-4o",
    max_tokens: int = 2000,
    temperature: float = 0.3
) -> Optional[str]:
    """Call OpenAI Chat API with error handling"""
    if not openai_client:
        return None
    
    try:
        response = await openai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return None

async def call_openai_vision(
    image_base64: str,
    mime_type: str,
    prompt: str,
    model: str = "gpt-4o"
) -> Optional[str]:
    """Call OpenAI Vision API for image analysis"""
    if not openai_client:
        return None
    
    try:
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": DOCUMENT_ANALYSIS_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI Vision API error: {e}")
        return None

# ============================================================================
# SAMPLE DATA AND HELPER FUNCTIONS
# ============================================================================

# Sample medical report image URLs
SAMPLE_REPORT_IMAGES = {
    "mri": [
        "https://images.unsplash.com/photo-1559757175-5700dde675bc",
        "https://images.unsplash.com/photo-1530497610245-94d3c16cda28"
    ],
    "xray": [
        "https://images.unsplash.com/photo-1516069677018-378515003435",
        "https://images.unsplash.com/photo-1631563019676-dade0dbdb8fc"
    ],
    "blood": [
        "https://images.unsplash.com/photo-1579154204601-01588f351e67",
        "https://images.unsplash.com/photo-1615461066841-6116e61058f4"
    ],
    "ecg": [
        "https://images.unsplash.com/photo-1628348070889-cb656235b4eb",
        "https://images.unsplash.com/photo-1631563019676-dade0dbdb8fc"
    ],
    "ct": [
        "https://images.unsplash.com/photo-1559757175-5700dde675bc",
        "https://images.unsplash.com/photo-1530497610245-94d3c16cda28"
    ]
}

# Sample doctors for each department
DEPARTMENT_DOCTORS = {
    "mri": ["Dr. Patel", "Dr. Johnson", "Dr. Williams"],
    "xray": ["Dr. Garcia", "Dr. Smith", "Dr. Brown"],
    "ecg": ["Dr. Davis", "Dr. Miller", "Dr. Wilson"],
    "blood": ["Dr. Anderson", "Dr. Taylor", "Dr. Thomas"],
    "ct": ["Dr. Jackson", "Dr. White", "Dr. Harris"],
    "treatment": ["Dr. Martin", "Dr. Thompson", "Dr. Robinson"]
}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None

class PatientProfile(BaseModel):
    patient_id: str
    name: str
    age: int
    gender: str
    blood_group: str
    address: str
    phone: str
    registration_date: str

class MedicalRecord(BaseModel):
    patient_id: str
    test_name: str
    test_date: str
    result: str
    doctor: str
    notes: Optional[str] = None
    report_image: Optional[str] = None

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

class FileAnalysisResponse(BaseModel):
    analysis: str
    file_type: str
    suggestions: List[str] = []

# ============================================================================
# API ENDPOINTS
# ============================================================================

@api_router.get("/")
async def root():
    return {"message": "United Patient Record System API"}

@api_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = await db.users.find_one(
        {"username": request.username, "password": request.password},
        {"_id": 0}
    )
    if user:
        return LoginResponse(success=True, message="Login successful", user=user)
    return LoginResponse(success=False, message="Invalid credentials")

@api_router.post("/init-data")
async def init_sample_data():
    """Initialize or refresh sample patient data"""
    # Check if data already exists
    existing_count = await db.profiles.count_documents({})
    if existing_count > 0:
        return {"message": "Sample data already exists", "patients_created": existing_count}
    
    # Create sample users
    users = [
        {"username": "doctor", "password": "doctor123", "role": "Doctor", "name": "Dr. Smith"},
        {"username": "nurse", "password": "nurse123", "role": "Nurse", "name": "Nurse Johnson"},
        {"username": "admin", "password": "admin123", "role": "Admin", "name": "Admin User"}
    ]
    await db.users.delete_many({})
    await db.users.insert_many(users)
    
    # Generate sample patients
    blood_groups = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
    genders = ["Male", "Female"]
    
    patients_created = 0
    for i in range(1, 16):
        patient_id = f"P100{i}" if i < 10 else f"P10{i}"
        profile = {
            "patient_id": patient_id,
            "name": fake.name(),
            "age": random.randint(18, 80),
            "gender": random.choice(genders),
            "blood_group": random.choice(blood_groups),
            "address": fake.address().replace("\n", ", "),
            "phone": fake.phone_number(),
            "registration_date": fake.date_between(start_date="-2y", end_date="today").isoformat()
        }
        await db.profiles.insert_one(profile)
        
        # Generate random medical records for each patient
        await generate_patient_records(patient_id)
        patients_created += 1
    
    return {"message": "Sample data populated successfully", "patients_created": patients_created}

async def generate_patient_records(patient_id: str):
    """Generate random medical records for a patient"""
    # MRI Records
    mri_tests = ["Brain MRI", "Spine MRI", "Knee MRI", "Shoulder MRI", "Abdominal MRI"]
    mri_results = ["Normal", "Minor abnormality detected", "Requires follow-up", "Clear"]
    for _ in range(random.randint(0, 3)):
        await db.mri_records.insert_one({
            "patient_id": patient_id,
            "test_name": random.choice(mri_tests),
            "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            "result": random.choice(mri_results),
            "doctor": random.choice(DEPARTMENT_DOCTORS["mri"]),
            "notes": fake.sentence(),
            "report_image": random.choice(SAMPLE_REPORT_IMAGES["mri"])
        })
    
    # X-Ray Records
    xray_tests = ["Chest X-Ray", "Hand X-Ray", "Foot X-Ray", "Dental X-Ray", "Pelvis X-Ray"]
    xray_results = ["Normal", "Fracture Detected", "Clear", "Requires specialist review"]
    for _ in range(random.randint(0, 4)):
        await db.xray_records.insert_one({
            "patient_id": patient_id,
            "test_name": random.choice(xray_tests),
            "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            "result": random.choice(xray_results),
            "doctor": random.choice(DEPARTMENT_DOCTORS["xray"]),
            "notes": fake.sentence(),
            "report_image": random.choice(SAMPLE_REPORT_IMAGES["xray"])
        })
    
    # ECG Records
    ecg_results = ["Normal Sinus Rhythm", "Sinus Bradycardia", "Sinus Tachycardia", "Minor irregularity"]
    for _ in range(random.randint(0, 2)):
        await db.ecg_records.insert_one({
            "patient_id": patient_id,
            "test_name": "12-Lead ECG",
            "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            "result": random.choice(ecg_results),
            "doctor": random.choice(DEPARTMENT_DOCTORS["ecg"]),
            "notes": fake.sentence(),
            "report_image": random.choice(SAMPLE_REPORT_IMAGES["ecg"])
        })
    
    # Blood Profile Records
    blood_tests = ["Complete Blood Count", "Lipid Profile", "Liver Function Test", "Kidney Function Test", "Thyroid Panel"]
    blood_results = ["Normal", "Slightly Elevated", "Within Range", "Abnormal - High", "Abnormal - Low"]
    for _ in range(random.randint(0, 4)):
        await db.blood_profile_records.insert_one({
            "patient_id": patient_id,
            "test_name": random.choice(blood_tests),
            "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            "result": random.choice(blood_results),
            "doctor": random.choice(DEPARTMENT_DOCTORS["blood"]),
            "notes": fake.sentence(),
            "report_image": random.choice(SAMPLE_REPORT_IMAGES["blood"])
        })
    
    # CT Scan Records
    ct_tests = ["Head CT", "Chest CT", "Abdominal CT", "Pelvic CT", "Spine CT"]
    ct_results = ["Normal", "Abnormality detected", "Clear", "Further investigation needed"]
    for _ in range(random.randint(0, 2)):
        await db.ct_scan_records.insert_one({
            "patient_id": patient_id,
            "test_name": random.choice(ct_tests),
            "test_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            "result": random.choice(ct_results),
            "doctor": random.choice(DEPARTMENT_DOCTORS["ct"]),
            "notes": fake.sentence(),
            "report_image": random.choice(SAMPLE_REPORT_IMAGES["ct"])
        })
    
    # Treatment Records
    treatments = ["Physical Therapy", "Medication Course", "Surgery Follow-up", "Preventive Care", "Chronic Disease Management"]
    medicines = ["Aspirin 100mg", "Metformin 500mg", "Lisinopril 10mg", "Atorvastatin 20mg", "Omeprazole 20mg"]
    for _ in range(random.randint(0, 3)):
        await db.treatment_records.insert_one({
            "patient_id": patient_id,
            "treatment_name": random.choice(treatments),
            "treatment_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            "result": "Ongoing" if random.random() > 0.5 else "Completed",
            "doctor": random.choice(DEPARTMENT_DOCTORS["treatment"]),
            "medicines": ", ".join(random.sample(medicines, random.randint(1, 3))),
            "notes": fake.sentence()
        })

@api_router.get("/search")
async def search_patient(term: str = Query(..., description="Patient ID or name to search")):
    """Search for a patient by ID or name"""
    # Try exact patient ID match first
    profile = await db.profiles.find_one({"patient_id": term.upper()}, {"_id": 0})
    
    # If not found, try partial name match
    if not profile:
        profile = await db.profiles.find_one(
            {"name": {"$regex": term, "$options": "i"}},
            {"_id": 0}
        )
    
    if not profile:
        return {"profile": None, "message": "Patient not found"}
    
    patient_id = profile["patient_id"]
    
    # Fetch all records
    mri_records = await db.mri_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    xray_records = await db.xray_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    ecg_records = await db.ecg_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    blood_profile_records = await db.blood_profile_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    ct_scan_records = await db.ct_scan_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    treatment_records = await db.treatment_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    
    return {
        "profile": profile,
        "mri_records": mri_records,
        "xray_records": xray_records,
        "ecg_records": ecg_records,
        "blood_profile_records": blood_profile_records,
        "ct_scan_records": ct_scan_records,
        "treatment_records": treatment_records
    }

@api_router.get("/analytics/{patient_id}")
async def get_patient_analytics(patient_id: str):
    """Get analytics for a specific patient"""
    profile = await db.profiles.find_one({"patient_id": patient_id.upper()}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Gather all records
    mri = await db.mri_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    xray = await db.xray_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    ecg = await db.ecg_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    blood = await db.blood_profile_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    ct = await db.ct_scan_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    treatment = await db.treatment_records.find({"patient_id": patient_id}, {"_id": 0}).to_list(100)
    
    # Calculate analytics
    all_records = []
    for r in mri:
        all_records.append({"date": r["test_date"], "type": "MRI", "result": r["result"]})
    for r in xray:
        all_records.append({"date": r["test_date"], "type": "X-Ray", "result": r["result"]})
    for r in ecg:
        all_records.append({"date": r["test_date"], "type": "ECG", "result": r["result"]})
    for r in blood:
        all_records.append({"date": r["test_date"], "type": "Blood Profile", "result": r["result"]})
    for r in ct:
        all_records.append({"date": r["test_date"], "type": "CT Scan", "result": r["result"]})
    for r in treatment:
        all_records.append({"date": r["treatment_date"], "type": "Treatment", "result": r["result"]})
    
    # Sort by date
    all_records.sort(key=lambda x: x["date"], reverse=True)
    
    # Department counts
    dept_counts = Counter([r["type"] for r in all_records])
    
    # Treatment summary
    treatment_summary = {
        "total": len(treatment),
        "ongoing": len([t for t in treatment if t["result"] == "Ongoing"]),
        "completed": len([t for t in treatment if t["result"] == "Completed"])
    }
    
    # Determine health trend
    recent = all_records[:5] if all_records else []
    abnormal_count = sum(1 for r in recent if "abnormal" in r["result"].lower() or "detected" in r["result"].lower())
    if abnormal_count >= 3:
        health_trend = "Needs Attention"
    elif abnormal_count >= 1:
        health_trend = "Monitoring"
    else:
        health_trend = "Stable"
    
    return PatientAnalytics(
        total_visits=len(all_records),
        total_tests=len(mri) + len(xray) + len(ecg) + len(blood) + len(ct),
        departments_visited=dict(dept_counts),
        visit_timeline=all_records[:10],
        treatment_summary=treatment_summary,
        health_trend=health_trend,
        recent_results=recent
    )

@api_router.get("/department/{department_name}")
async def get_department_records(department_name: str):
    """Get all records for a specific department"""
    collection_map = {
        "mri": "mri_records",
        "xray": "xray_records",
        "ecg": "ecg_records",
        "blood": "blood_profile_records",
        "ct": "ct_scan_records",
        "treatment": "treatment_records"
    }
    
    collection_name = collection_map.get(department_name.lower())
    if not collection_name:
        raise HTTPException(status_code=404, detail="Department not found")
    
    collection = db[collection_name]
    records = await collection.find({}, {"_id": 0}).to_list(1000)
    
    # Add patient names to records
    for record in records:
        profile = await db.profiles.find_one({"patient_id": record["patient_id"]}, {"_id": 0, "name": 1})
        record["patient_name"] = profile["name"] if profile else "Unknown"
    
    return {"department": department_name, "records": records}

@api_router.get("/patients")
async def get_all_patients():
    """Get list of all patient IDs and names for reference"""
    profiles = await db.profiles.find({}, {"_id": 0, "patient_id": 1, "name": 1}).to_list(1000)
    return {"patients": profiles}

# ============================================================================
# DEEP QUERY - AI Clinical Assistant (OpenAI Direct)
# ============================================================================

@api_router.post("/deep-query", response_model=DeepQueryResponse)
async def deep_query(request: DeepQueryRequest):
    """AI-powered clinical assistant to analyze patient records and answer questions"""
    
    patient_id = request.patient_id
    question = request.question
    
    # Fetch all patient data
    query = {"patient_id": patient_id}
    
    profile = await db.profiles.find_one(query, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Fetch all records
    mri_records = await db.mri_records.find(query, {"_id": 0}).to_list(1000)
    xray_records = await db.xray_records.find(query, {"_id": 0}).to_list(1000)
    ecg_records = await db.ecg_records.find(query, {"_id": 0}).to_list(1000)
    treatment_records = await db.treatment_records.find(query, {"_id": 0}).to_list(1000)
    blood_profile_records = await db.blood_profile_records.find(query, {"_id": 0}).to_list(1000)
    ct_scan_records = await db.ct_scan_records.find(query, {"_id": 0}).to_list(1000)
    
    # Build context for LLM
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

MRI RECORDS ({len(mri_records)} records):
{json.dumps(mri_records, indent=2) if mri_records else 'No MRI records'}

X-RAY RECORDS ({len(xray_records)} records):
{json.dumps(xray_records, indent=2) if xray_records else 'No X-Ray records'}

ECG RECORDS ({len(ecg_records)} records):
{json.dumps(ecg_records, indent=2) if ecg_records else 'No ECG records'}

BLOOD PROFILE RECORDS ({len(blood_profile_records)} records):
{json.dumps(blood_profile_records, indent=2) if blood_profile_records else 'No blood profile records'}

CT SCAN RECORDS ({len(ct_scan_records)} records):
{json.dumps(ct_scan_records, indent=2) if ct_scan_records else 'No CT scan records'}

TREATMENT RECORDS ({len(treatment_records)} records):
{json.dumps(treatment_records, indent=2) if treatment_records else 'No treatment records'}
"""

    # Determine matched departments
    question_lower = question.lower()
    matched_departments = []
    if any(word in question_lower for word in ['mri', 'brain', 'spine', 'magnetic']):
        matched_departments.append('MRI')
    if any(word in question_lower for word in ['xray', 'x-ray', 'chest', 'bone', 'fracture']):
        matched_departments.append('X-Ray')
    if any(word in question_lower for word in ['ecg', 'heart', 'cardiac', 'rhythm']):
        matched_departments.append('ECG')
    if any(word in question_lower for word in ['blood', 'hemoglobin', 'platelet', 'wbc', 'rbc', 'lipid', 'liver', 'kidney', 'thyroid']):
        matched_departments.append('Blood Profile')
    if any(word in question_lower for word in ['ct', 'scan', 'computed tomography']):
        matched_departments.append('CT Scan')
    if any(word in question_lower for word in ['treatment', 'medicine', 'medication', 'prescription', 'therapy']):
        matched_departments.append('Treatment')
    
    if not matched_departments:
        if mri_records: matched_departments.append('MRI')
        if xray_records: matched_departments.append('X-Ray')
        if ecg_records: matched_departments.append('ECG')
        if blood_profile_records: matched_departments.append('Blood Profile')
        if ct_scan_records: matched_departments.append('CT Scan')
        if treatment_records: matched_departments.append('Treatment')
    
    # Collect evidence records
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
    
    # Try OpenAI API
    if openai_client:
        try:
            messages = [
                {"role": "system", "content": DOCASSIST_SYSTEM_PROMPT},
                {"role": "user", "content": f"Based on the following patient records, please answer this question: {question}\n\n{patient_context}"}
            ]
            
            response = await call_openai_chat(messages, model="gpt-4o")
            
            if response:
                return DeepQueryResponse(
                    answer=response,
                    evidence=evidence[:6],
                    matched_departments=matched_departments
                )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
    
    # Fallback: Rule-based summary
    logger.warning("Using fallback analyzer - OpenAI unavailable")
    records_dict = {
        'mri': mri_records,
        'xray': xray_records,
        'ecg': ecg_records,
        'blood': blood_profile_records,
        'ct': ct_scan_records,
        'treatment': treatment_records
    }
    fallback_answer = FallbackAnalyzer.summarize_patient(profile, records_dict)
    
    return DeepQueryResponse(
        answer=fallback_answer,
        evidence=evidence[:6],
        matched_departments=matched_departments
    )

# ============================================================================
# DOCUMENT ANALYSIS - PDF & Image Processing (OpenAI Vision)
# ============================================================================

@api_router.post("/analyze-document", response_model=FileAnalysisResponse)
async def analyze_document(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    question: str = Form(default="Analyze this medical document and provide a detailed summary.")
):
    """Analyze uploaded medical documents (images, PDFs) using OpenAI Vision"""
    
    # Validate file type
    allowed_types = {
        'image/png': 'image',
        'image/jpeg': 'image',
        'image/jpg': 'image',
        'image/webp': 'image',
        'application/pdf': 'pdf'
    }
    
    content_type = file.content_type
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {content_type}. Allowed: PNG, JPEG, WebP, PDF"
        )
    
    file_category = allowed_types[content_type]
    
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
        
        analysis = None
        file_type_label = "Unknown"
        
        if file_category == 'pdf':
            # Extract text from PDF
            file_type_label = "PDF Document"
            pdf_text = extract_text_from_pdf(temp_file_path)
            
            if openai_client and pdf_text and "[" not in pdf_text[:10]:
                # Use OpenAI to analyze extracted PDF text
                messages = [
                    {"role": "system", "content": DOCUMENT_ANALYSIS_PROMPT},
                    {"role": "user", "content": f"{patient_context}\n\nDoctor's Question: {question}\n\nExtracted PDF Content:\n{pdf_text[:8000]}"}
                ]
                analysis = await call_openai_chat(messages, model="gpt-4o")
            else:
                # Fallback for PDF
                analysis = f"""### Document Type: PDF Report

### Extracted Content:
{pdf_text[:2000]}...

### Note:
AI analysis unavailable. Please review the extracted text above manually.

### Recommendation:
Consult with appropriate specialist for interpretation."""
        
        else:
            # Image analysis using OpenAI Vision
            file_type_label = "Medical Image"
            
            if openai_client:
                image_base64 = encode_image_to_base64(temp_file_path)
                mime_type = get_image_mime_type(temp_file_path)
                
                analysis = await call_openai_vision(
                    image_base64=image_base64,
                    mime_type=mime_type,
                    prompt=f"{patient_context}\n\nDoctor's Question: {question}\n\nPlease analyze this medical image."
                )
            
            if not analysis:
                # Fallback for images
                analysis = """### Document Type: Medical Image

### Analysis:
AI image analysis is currently unavailable.

### Recommendation:
Please review the image manually or try again later when AI services are available.

### Note:
For urgent cases, please consult with a radiologist or appropriate specialist."""
        
        # Generate suggestions
        suggestions = [
            "Review findings with attending physician",
            "Compare with previous imaging if available",
            "Document observations in patient record"
        ]
        
        if "abnormal" in (analysis or "").lower():
            suggestions.insert(0, "⚠️ Abnormal findings detected - prioritize physician review")
        
        return FileAnalysisResponse(
            analysis=analysis or "Analysis could not be completed. Please try again.",
            file_type=file_type_label,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Document analysis error: {str(e)}")
        return FileAnalysisResponse(
            analysis=FallbackAnalyzer.get_error_message("generic"),
            file_type="Unknown",
            suggestions=["Please try again or review the document manually"]
        )
    
    finally:
        # Clean up temp file
        if temp_file_path.exists():
            temp_file_path.unlink()

# ============================================================================
# HEALTH CHECK AND STARTUP
# ============================================================================

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "database": "connected",
        "openai": "available" if openai_client else "not configured",
        "pdf_support": PDF_SUPPORT,
        "image_support": IMAGE_SUPPORT
    }
    return status

# Include the router
app.include_router(api_router)

# Startup logging
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
